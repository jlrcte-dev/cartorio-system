"""Atualização manual e consulta do retrato.

refresh: config do piloto (uma fonte explícita, sem pastas) → coleta pelo coletor
existente → vínculo com a geração capturada NESTA execução (run_id do estado e do
manifesto) → integridade sobre os mesmos bytes que serão lidos → retrato → validação →
troca atômica de ``latest.json`` (o ponto de publicação). Falha antes dela preserva o
último relatório válido e registra só ``last_attempt.json`` (sanitizado). O registro da
tentativa é gravado depois da troca: se ele falhar, o relatório novo já está publicado e
``show`` mostra a atualização como não confirmada, nunca como sucesso nem como preservação.

show: lê e valida ``latest.json`` e ``last_attempt.json``; sem autenticação nem rede, sem
recalcular nada (os indicadores de datas usam a referência gravada na captura).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from app.core.logging import get_logger
from app.modules.drive_capture.collector import Collector
from app.modules.drive_capture.config import CaptureConfig, FileSource
from app.modules.drive_capture.errors import Code, DriveCaptureError
from app.modules.drive_capture.store import CaptureStore, RunLock, atomic_write_json, utc_now
from app.modules.services_snapshot.report import (
    ReportRejected,
    attempt_relation,
    build_attempt,
    build_report,
    render_markdown,
    validate_attempt,
    validate_report,
)

logger = get_logger("services_snapshot")

SNAPSHOT_DIR = "services_snapshot"
LATEST = "latest.json"
ATTEMPT = "last_attempt.json"
_GEN_RE = re.compile(r"^gen-\d{8}T\d{6}Z-[0-9a-f]{8}$")

CollectorFactory = Callable[[CaptureConfig], tuple[Collector, str]]


class RefreshFailed(Exception):
    def __init__(self, stage: str, code: str) -> None:
        self.stage = stage
        self.code = code
        super().__init__(f"{stage}: {code}")


def snapshot_dir(config: CaptureConfig) -> Path:
    return config.data_dir / SNAPSHOT_DIR


def pilot_source(config: CaptureConfig) -> FileSource:
    if config.folders or len(config.files) != 1:
        raise RefreshFailed("configuracao", "fora_do_recorte_piloto")
    return config.files[0]


def default_collector(config: CaptureConfig) -> tuple[Collector, str]:
    # Import tardio: só o refresh carrega google-auth e lê a credencial.
    from app.modules.drive_capture.auth import build_transport
    from app.modules.drive_capture.drive_client import DriveClient

    transport, identity = build_transport(config)
    client = DriveClient(
        transport, shared_drive_id=config.shared_drive_id, max_retries=config.limits.max_retries
    )
    return Collector(config, client, CaptureStore(config.data_dir)), identity


def bind_generation(
    store: CaptureStore, key: str, run_id: str, file_id: str
) -> tuple[bytes, dict, dict]:
    """Bytes, ponteiro e manifesto da geração produzida por ``run_id``; nada de outra execução."""
    state = store.read_state(key) or {}
    attempt = state.get("last_attempt") or {}
    current = state.get("current") or {}
    if attempt.get("run_id") != run_id or attempt.get("result") != "captured" or not current:
        raise RefreshFailed("vinculo", "geracao_nao_vinculada")
    generation, content_file = current.get("generation", ""), current.get("content_file", "")
    if not _GEN_RE.match(generation) or content_file != "content.xlsx":
        raise RefreshFailed("vinculo", "formato_nao_suportado")
    gdir = store.sources_dir / key / generation
    try:
        manifest = json.loads((gdir / "manifest.json").read_text(encoding="utf-8"))
        content = (gdir / content_file).read_bytes()
    except (OSError, ValueError):
        raise RefreshFailed("vinculo", "geracao_indisponivel") from None
    if manifest.get("run_id") != run_id:
        raise RefreshFailed("vinculo", "geracao_nao_vinculada")
    if manifest.get("drive_file_id") != file_id or manifest.get("key") != key:
        raise RefreshFailed("integridade", "procedencia_divergente")
    digest = hashlib.sha256(content).hexdigest()
    if not (
        digest == current.get("sha256") == manifest.get("sha256")
        and len(content) == manifest.get("bytes")
    ):
        raise RefreshFailed("integridade", "integridade_divergente")
    return content, current, manifest


def snapshot_from_capture(
    source: FileSource, content: bytes, manifest: dict, generated_at: datetime
) -> dict:
    from app.modules.services_snapshot.dates import capture_reference
    from app.modules.services_snapshot.rules import classify_workbook
    from app.modules.services_snapshot.xlsx import XlsxError, parse_workbook

    reference = capture_reference(manifest.get("captured_at"))
    if reference is None:
        raise RefreshFailed("validacao", "relatorio_invalido")
    try:
        sheets = parse_workbook(content)
    except XlsxError:
        raise RefreshFailed("leitura", "xlsx_invalido") from None
    report = build_report(
        source_alias=source.alias,
        family=source.family,
        run_id=manifest["run_id"],
        captured_at=manifest.get("captured_at"),
        drive_modified_time=manifest.get("drive_modified_time"),
        drive_version=manifest.get("drive_version"),
        tabs=classify_workbook(sheets, reference),
        reference=reference,
        generated_at=generated_at,
    )
    try:
        validate_report(report)
    except ReportRejected:
        raise RefreshFailed("validacao", "relatorio_invalido") from None
    return report


def _record_attempt(out: Path, attempt: dict) -> bool:
    try:
        validate_attempt(attempt)
        atomic_write_json(out / ATTEMPT, attempt)
    except (ReportRejected, OSError, DriveCaptureError):
        logger.error("registro da tentativa não gravado")
        return False
    return True


def refresh(
    config: CaptureConfig,
    *,
    collector_factory: CollectorFactory = default_collector,
    clock: Callable[[], datetime] = utc_now,
) -> tuple[int, dict | None, dict | None]:
    """Devolve (código de saída, relatório publicado ou None, registro da tentativa ou None).

    Em sucesso, o registro volta None quando não pôde ser gravado: o relatório já foi
    publicado, mas a tentativa não está confirmada em disco."""
    out = snapshot_dir(config)
    attempted_at = clock()
    run_id: str | None = None
    try:
        source = pilot_source(config)
        with RunLock(out, "services-snapshot-refresh"):
            try:
                collector, identity = collector_factory(config)
                result = collector.run(identity)
            except DriveCaptureError as exc:
                raise RefreshFailed("coleta", str(exc.code)) from None
            run_id = result.run_id
            if result.global_code:
                raise RefreshFailed("coleta", result.global_code)
            outcome = next((s for s in result.sources if s.alias == source.alias), None)
            if outcome is None or outcome.result != "captured":
                raise RefreshFailed(
                    "coleta", (outcome.code if outcome else None) or "coleta_sem_captura"
                )
            content, _current, manifest = bind_generation(
                collector.store, outcome.key, run_id, source.file_id
            )
            report = snapshot_from_capture(source, content, manifest, clock())
            try:
                atomic_write_json(out / LATEST, report)
            except (OSError, DriveCaptureError):
                raise RefreshFailed("publicacao", "falha_ao_publicar") from None
    except DriveCaptureError as exc:
        if exc.code == Code.RUN_LOCKED:
            # Recusa antes de começar: não é tentativa e não sobrescreve o registro
            # da execução ativa.
            return 4, None, None
        attempt = build_attempt(attempted_at, False, "desconhecida", str(exc.code), run_id)
        _record_attempt(out, attempt)
        return 2, None, attempt
    except RefreshFailed as failed:
        attempt = build_attempt(attempted_at, False, failed.stage, failed.code, run_id)
        _record_attempt(out, attempt)
        logger.warning("atualização falhou: %s / %s", failed.stage, failed.code)
        return 2, None, attempt
    except Exception as exc:  # traceback pode carregar texto privado
        logger.error("atualização falhou: erro inesperado (%s)", type(exc).__name__)
        attempt = build_attempt(attempted_at, False, "desconhecida", "erro_inesperado", run_id)
        _record_attempt(out, attempt)
        return 2, None, attempt
    attempt = build_attempt(attempted_at, True, None, None, run_id)
    return 0, report, attempt if _record_attempt(out, attempt) else None


def _load(path: Path, validator: Callable[[object], None]) -> tuple[dict | None, bool]:
    """(objeto validado ou None, arquivo existia e era inválido)."""
    if not path.is_file():
        return None, False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        validator(data)
    except (OSError, ValueError, ReportRejected):
        return None, True
    return data, False


def show(config: CaptureConfig) -> tuple[int, str]:
    """Saída: 0 relatório válido, confirmado pelo registro da tentativa que o publicou ·
    1 relatório válido, mas a última tentativa falhou ou o registro não o confirma ·
    3 nenhum relatório válido ainda · 2 relatório ou registro local inválido."""
    out = snapshot_dir(config)
    report, bad_report = _load(out / LATEST, validate_report)
    attempt, bad_attempt = _load(out / ATTEMPT, validate_attempt)
    if bad_report or bad_attempt:
        return 2, "Relatório ou registro local inválido; nada exibido. Rode refresh para regenerar."
    text = render_markdown(report, attempt)
    if report is None:
        return 3, text
    return (0 if attempt_relation(report, attempt) == "confirmada" else 1), text
