"""Orquestra uma coleta manual: fronteira → aquisição → consistência → publicação.

Cada fonte é isolada: falha numa não interrompe as demais. Nada aqui interpreta conteúdo;
os sinais de alteração são técnicos (versão, modifiedTime, hash da exportação) e não
dizem que um serviço avançou.
"""

from __future__ import annotations

import fnmatch
import hashlib
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from app.core.logging import get_logger
from app.modules.drive_capture.config import (
    GOOGLE_EXPORTS,
    GOOGLE_FOLDER,
    GOOGLE_SHORTCUT,
    STORED_EXTENSIONS,
    CaptureConfig,
    FolderSource,
)
from app.modules.drive_capture.drive_client import DriveClient, FileMeta
from app.modules.drive_capture.errors import Code, DriveCaptureError
from app.modules.drive_capture.store import Acquisition, CaptureStore, RunLock, iso, utc_now

logger = get_logger("drive_capture.collector")

_ZIP_MAGIC = b"PK\x03\x04"


@dataclass(frozen=True)
class Candidate:
    file_id: str
    alias: str
    family: str
    origin: str  # "file" | "folder"
    folder: FolderSource | None = None


@dataclass
class SourceOutcome:
    key: str
    alias: str
    family: str
    origin: str
    folder_alias: str | None
    result: str  # "captured" | "failed" | "skipped"
    code: str | None
    attempt_at: str
    last_success_at: str | None = None
    drive_modified_time: str | None = None
    drive_version: str | None = None
    bytes: int | None = None
    method: str | None = None
    consistency_retry: bool = False
    signals: dict[str, bool | None] = field(default_factory=dict)


@dataclass
class FolderOutcome:
    alias: str
    family: str
    listing: str  # "complete" | "partial" | "failed"
    code: str | None = None
    children_seen: int = 0
    eligible: int = 0
    ignored_subfolders: int = 0
    ignored_shortcuts: int = 0
    ignored_mime: int = 0
    not_matching_pattern: int = 0
    already_covered: int = 0
    departed: int = 0


@dataclass
class RunResult:
    run_id: str
    started_at: datetime
    finished_at: datetime | None = None
    identity_verified: bool = False
    global_code: str | None = None
    sources: list[SourceOutcome] = field(default_factory=list)
    folders: list[FolderOutcome] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.global_code:
            return "failed"
        captured = sum(1 for s in self.sources if s.result == "captured")
        problems = any(s.result != "captured" for s in self.sources) or any(
            f.listing != "complete" for f in self.folders
        )
        if self.sources and captured == 0:
            return "failed"
        if problems:
            return "partial"
        return "complete"


def new_run_id(now: datetime) -> str:
    return f"{now.strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(3)}"


class Collector:
    def __init__(
        self,
        config: CaptureConfig,
        client: DriveClient,
        store: CaptureStore,
        *,
        clock: Callable[[], datetime] = utc_now,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config
        self.client = client
        self.store = store
        self._clock = clock
        self._monotonic = monotonic

    # -- entrada ---------------------------------------------------------------------------

    def run(self, identity: str | None = None) -> RunResult:
        started = self._clock()
        result = RunResult(run_id=new_run_id(started), started_at=started)
        try:
            with RunLock(self.config.data_dir, result.run_id):
                self._run_locked(result, identity)
        except DriveCaptureError as exc:
            result.global_code = str(exc.code)
            logger.error("coleta abortada: %s", exc.code)
        except Exception as exc:  # traceback poderia carregar ID ou caminho privado
            result.global_code = str(Code.UNEXPECTED_ERROR)
            logger.error("coleta abortada: erro inesperado (%s)", type(exc).__name__)
        result.finished_at = self._clock()
        return result

    def verify_identity(self, identity: str | None) -> None:
        """A credencial local e a identidade que o Drive reconhece precisam ser a declarada."""
        expected = self.config.expected_identity.lower()
        if identity is not None and identity.lower() != expected:
            raise DriveCaptureError(Code.IDENTITY_MISMATCH)
        observed = self.client.authenticated_identity()
        if observed is None or observed.lower() != expected:
            raise DriveCaptureError(Code.IDENTITY_MISMATCH)

    def _run_locked(self, result: RunResult, identity: str | None) -> None:
        self.verify_identity(identity)
        result.identity_verified = True

        candidates, departed = self._resolve_boundary(result)
        limits = self.config.limits
        deadline = self._monotonic() + limits.max_run_seconds
        budget = limits.max_run_bytes

        for file_id, key, alias, family, folder_alias in departed:
            at = self._clock()
            state = self.store.record_failure(key, file_id, Code.OUT_OF_BOUNDARY, result.run_id, at)
            result.sources.append(
                self._failed(
                    key, alias, family, "folder", folder_alias, Code.OUT_OF_BOUNDARY, at, state
                )
            )

        for index, candidate in enumerate(candidates):
            folder_alias = candidate.folder.alias if candidate.folder else None
            key = self.store.key_for(candidate.file_id, candidate.alias, folder_alias=folder_alias)
            alias = key if folder_alias else candidate.alias
            at = self._clock()
            if index >= limits.max_sources:
                result.sources.append(
                    self._skipped(key, alias, candidate, folder_alias, Code.SOURCE_CAP, at)
                )
                continue
            if self._monotonic() >= deadline or budget <= 0:
                result.sources.append(
                    self._skipped(
                        key, alias, candidate, folder_alias, Code.RUN_BUDGET_EXHAUSTED, at
                    )
                )
                continue
            outcome = self._capture_one(candidate, key, alias, folder_alias, result.run_id, budget)
            if outcome.bytes:
                budget -= outcome.bytes
            result.sources.append(outcome)

    def preflight(self, identity: str | None = None) -> RunResult:
        """Valida identidade, fronteira e acesso a metadados sem baixar nada nem gravar."""
        started = self._clock()
        result = RunResult(run_id=new_run_id(started), started_at=started)
        try:
            self.verify_identity(identity)
            result.identity_verified = True
            candidates, _ = self._resolve_boundary(result)
        except DriveCaptureError as exc:
            result.global_code = str(exc.code)
            result.finished_at = self._clock()
            return result
        per_folder: dict[str, int] = {}
        for index, candidate in enumerate(candidates):
            if candidate.folder is None:
                alias = candidate.alias
            else:
                per_folder[candidate.alias] = per_folder.get(candidate.alias, 0) + 1
                alias = f"{candidate.alias}#{per_folder[candidate.alias]}"
            outcome = SourceOutcome(
                key="",
                alias=alias,
                family=candidate.family,
                origin=candidate.origin,
                folder_alias=candidate.folder.alias if candidate.folder else None,
                result="eligible",
                code=None,
                attempt_at=iso(self._clock()),
            )
            try:
                if index >= self.config.limits.max_sources:
                    raise DriveCaptureError(Code.SOURCE_CAP)
                meta = self.client.get_metadata(candidate.file_id)
                self._check_eligible(meta, candidate)
                if meta.can_download is False:
                    raise DriveCaptureError(Code.DOWNLOAD_RESTRICTED)
                outcome.drive_modified_time = meta.modified_time
                outcome.drive_version = meta.version
                outcome.method = (
                    GOOGLE_EXPORTS[meta.mime_type][2]
                    if meta.mime_type in GOOGLE_EXPORTS
                    else "download"
                )
            except DriveCaptureError as exc:
                outcome.result = "failed"
                outcome.code = str(exc.code)
            result.sources.append(outcome)
        result.finished_at = self._clock()
        return result

    # -- fronteira -------------------------------------------------------------------------

    def _resolve_boundary(
        self, result: RunResult
    ) -> tuple[list[Candidate], list[tuple[str, str, str, str, str]]]:
        candidates = [Candidate(f.file_id, f.alias, f.family, "file") for f in self.config.files]
        claimed = {c.file_id for c in candidates}
        complete_listings: list[tuple[FolderSource, FolderOutcome]] = []

        for folder in self.config.folders:
            outcome = FolderOutcome(alias=folder.alias, family=folder.family, listing="failed")
            result.folders.append(outcome)
            try:
                meta = self.client.get_metadata(folder.folder_id)
                if meta.mime_type != GOOGLE_FOLDER:
                    raise DriveCaptureError(Code.NOT_A_FOLDER)
                if meta.trashed:
                    raise DriveCaptureError(Code.TRASHED)
                listing = self.client.list_children(
                    folder.folder_id,
                    page_size=self.config.limits.page_size,
                    max_pages=self.config.limits.max_listing_pages,
                    with_name=folder.name_pattern is not None,
                )
            except DriveCaptureError as exc:
                outcome.code = str(exc.code)
                continue

            outcome.listing = "complete" if listing.complete else "partial"
            outcome.code = listing.incomplete_reason
            for child in listing.files:
                outcome.children_seen += 1
                # Defesa redundante: a consulta já é restrita à pasta.
                if folder.folder_id not in child.parents or child.trashed:
                    continue
                if child.mime_type == GOOGLE_FOLDER:
                    outcome.ignored_subfolders += 1
                    continue
                if child.mime_type == GOOGLE_SHORTCUT:
                    outcome.ignored_shortcuts += 1
                    continue
                if child.mime_type not in folder.mime_types:
                    outcome.ignored_mime += 1
                    continue
                if folder.name_pattern and not fnmatch.fnmatch(
                    (child.name or "").lower(), folder.name_pattern.lower()
                ):
                    outcome.not_matching_pattern += 1
                    continue
                if child.file_id in claimed:
                    outcome.already_covered += 1
                    continue
                claimed.add(child.file_id)
                outcome.eligible += 1
                candidates.append(
                    Candidate(child.file_id, folder.alias, folder.family, "folder", folder)
                )

            if listing.complete:
                complete_listings.append((folder, outcome))

        # Calculado depois de todas as pastas: um arquivo que passou de uma pasta autorizada
        # para outra continua no recorte. Só listagem completa autoriza concluir que um filho
        # conhecido saiu, e o arquivo ausente não é consultado — ler fora do recorte seria
        # ampliar o acesso.
        departed: list[tuple[str, str, str, str, str]] = []
        for folder, outcome in complete_listings:
            for file_id, key in self.store.folder_members(folder.alias).items():
                if file_id not in claimed:
                    outcome.departed += 1
                    departed.append((file_id, key, key, folder.family, folder.alias))
        return candidates, departed

    def _check_eligible(self, meta: FileMeta, candidate: Candidate) -> None:
        if meta.trashed:
            raise DriveCaptureError(Code.TRASHED)
        if candidate.folder is not None and candidate.folder.folder_id not in meta.parents:
            raise DriveCaptureError(Code.OUT_OF_BOUNDARY)
        if meta.mime_type == GOOGLE_SHORTCUT:
            raise DriveCaptureError(Code.SHORTCUT_NOT_FOLLOWED)
        if meta.mime_type == GOOGLE_FOLDER:
            raise DriveCaptureError(Code.IS_FOLDER)
        if not self.config.is_capturable_mime(meta.mime_type):
            raise DriveCaptureError(Code.UNSUPPORTED_MIME)
        if candidate.folder is not None and meta.mime_type not in candidate.folder.mime_types:
            raise DriveCaptureError(Code.UNSUPPORTED_MIME)

    # -- aquisição -------------------------------------------------------------------------

    def _acquire(self, meta: FileMeta, max_bytes: int, budget_bound: bool) -> Acquisition:
        if meta.can_download is False:
            raise DriveCaptureError(Code.DOWNLOAD_RESTRICTED)
        if meta.size is not None and meta.size > max_bytes:
            raise DriveCaptureError(Code.RUN_BUDGET_EXHAUSTED if budget_bound else Code.SIZE_LIMIT)
        try:
            if meta.mime_type in GOOGLE_EXPORTS:
                export_mime, extension, method = GOOGLE_EXPORTS[meta.mime_type]
                content = self.client.export(meta.file_id, export_mime, max_bytes)
                if not content.startswith(_ZIP_MAGIC):
                    raise DriveCaptureError(Code.UNEXPECTED_RESPONSE)
            else:
                export_mime, extension, method = None, STORED_EXTENSIONS[meta.mime_type], "download"
                content = self.client.download(meta.file_id, max_bytes)
        except DriveCaptureError as exc:
            if exc.code == Code.SIZE_LIMIT and budget_bound:
                raise DriveCaptureError(Code.RUN_BUDGET_EXHAUSTED) from None
            raise
        if meta.md5 is not None and hashlib.md5(content).hexdigest() != meta.md5:
            raise DriveCaptureError(Code.INTEGRITY_MISMATCH)
        return Acquisition(
            content=content,
            extension=extension,
            method=method,
            source_mime=meta.mime_type,
            exported_mime=export_mime,
            modified_time=meta.modified_time,
            version=meta.version,
            drive_size=meta.size,
            drive_md5=meta.md5,
        )

    def _capture_one(
        self,
        candidate: Candidate,
        key: str,
        alias: str,
        folder_alias: str | None,
        run_id: str,
        budget: int,
    ) -> SourceOutcome:
        at = self._clock()
        max_file = self.config.limits.max_file_bytes
        max_bytes = min(max_file, budget)
        budget_bound = budget < max_file
        retried = False
        try:
            before = self.client.get_metadata(candidate.file_id)
            self._check_eligible(before, candidate)
            for attempt in range(2):
                acquisition = self._acquire(before, max_bytes, budget_bound)
                after = self.client.get_metadata(candidate.file_id)
                # Revalida pertencimento antes de promover: a fonte pode ter saído do recorte.
                self._check_eligible(after, candidate)
                if after.consistency_key() == before.consistency_key():
                    break
                if attempt == 1:
                    raise DriveCaptureError(Code.SOURCE_CHANGED)
                retried = True
                before = after
            previous = (self.store.read_state(key) or {}).get("current")
            state = self.store.publish(
                key,
                candidate.file_id,
                acquisition,
                alias=alias,
                family=candidate.family,
                run_id=run_id,
                captured_at=self._clock(),
            )
        except DriveCaptureError as exc:
            state = self.store.record_failure(key, candidate.file_id, exc.code, run_id, at)
            logger.warning("fonte %s: %s", alias, exc.code)
            outcome = self._failed(
                key, alias, candidate.family, candidate.origin, folder_alias, exc.code, at, state
            )
            outcome.consistency_retry = retried
            return outcome
        except Exception as exc:  # a coleta das demais fontes continua
            logger.error("fonte %s: erro inesperado (%s)", alias, type(exc).__name__)
            state = self.store.record_failure(
                key, candidate.file_id, Code.UNEXPECTED_ERROR, run_id, at
            )
            return self._failed(
                key,
                alias,
                candidate.family,
                candidate.origin,
                folder_alias,
                Code.UNEXPECTED_ERROR,
                at,
                state,
            )

        current = state["current"]
        logger.info("fonte %s: capturada (%s bytes)", alias, current["bytes"])
        return SourceOutcome(
            key=key,
            alias=alias,
            family=candidate.family,
            origin=candidate.origin,
            folder_alias=folder_alias,
            result="captured",
            code=None,
            attempt_at=iso(at),
            last_success_at=state["last_success_at"],
            drive_modified_time=current["drive_modified_time"],
            drive_version=current["drive_version"],
            bytes=current["bytes"],
            method=current["acquisition_method"],
            consistency_retry=retried,
            signals=_change_signals(previous, current),
        )

    # -- resultados ------------------------------------------------------------------------

    @staticmethod
    def _failed(
        key: str,
        alias: str,
        family: str,
        origin: str,
        folder_alias: str | None,
        code: Code,
        at: datetime,
        state: dict,
    ) -> SourceOutcome:
        # Sem modifiedTime/versão: numa falha nada foi observado agora, e repetir o valor da
        # última captura válida pareceria observação atual. Ela fica em last_success_at.
        return SourceOutcome(
            key=key,
            alias=alias,
            family=family,
            origin=origin,
            folder_alias=folder_alias,
            result="failed",
            code=str(code),
            attempt_at=iso(at),
            last_success_at=state.get("last_success_at"),
        )

    def _skipped(
        self,
        key: str,
        alias: str,
        candidate: Candidate,
        folder_alias: str | None,
        code: Code,
        at: datetime,
    ) -> SourceOutcome:
        state = self.store.read_state(key) or {}
        return SourceOutcome(
            key=key,
            alias=alias,
            family=candidate.family,
            origin=candidate.origin,
            folder_alias=folder_alias,
            result="skipped",
            code=str(code),
            attempt_at=iso(at),
            last_success_at=state.get("last_success_at"),
        )


def _change_signals(previous: dict | None, current: dict) -> dict[str, bool | None]:
    if not previous:
        return {
            "version_changed": None,
            "modified_time_changed": None,
            "content_hash_changed": None,
        }
    return {
        "version_changed": previous.get("drive_version") != current.get("drive_version"),
        "modified_time_changed": previous.get("drive_modified_time")
        != current.get("drive_modified_time"),
        "content_hash_changed": previous.get("sha256") != current.get("sha256"),
    }
