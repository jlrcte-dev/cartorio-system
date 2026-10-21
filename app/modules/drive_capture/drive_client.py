"""Cliente somente leitura da Drive API v3.

Duas travas independentes contra escrita: o transporte só expõe GET (``session.get``)
e só aceita caminhos de leitura (``about``, ``files``, ``files/{id}``,
``files/{id}/export``). Escopo OAuth de leitura não basta sozinho para restringir a
fronteira — quem restringe é a permissão da identidade mais a allowlist da config.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from app.modules.drive_capture.errors import (
    RETRYABLE,
    Code,
    DriveCaptureError,
    classify_exception,
    map_http_error,
)

API_BASE = "https://www.googleapis.com/drive/v3/"
ALLOWED_PATH_RE = re.compile(r"^(?:about|files|files/[A-Za-z0-9_-]+(?:/export)?)$")

_JSON_MAX_BYTES = 4 * 1024 * 1024
_ERROR_BODY_MAX_BYTES = 16 * 1024
_CHUNK = 64 * 1024

# ``name`` só é pedido quando a pasta tem name_pattern; fica em memória para o casamento
# e nunca é gravado em manifesto, estado, log ou relatório.
_META_FIELDS = (
    "id,mimeType,parents,trashed,modifiedTime,version,size,md5Checksum,"
    "capabilities(canDownload),shortcutDetails(targetId)"
)


class ReadOnlyTransport(Protocol):
    def get_json(self, path: str, params: Mapping[str, str]) -> dict[str, Any]: ...

    def get_bytes(self, path: str, params: Mapping[str, str], max_bytes: int) -> bytes: ...


def check_path(path: str) -> None:
    if not ALLOWED_PATH_RE.match(path):
        raise DriveCaptureError(Code.UNEXPECTED_ERROR, "caminho fora da allowlist de leitura")


class RequestsTransport:
    """Transporte real sobre uma sessão autorizada (``google.auth...AuthorizedSession``).

    Recebe a sessão pronta; não importa ``requests`` nem ``google-auth``. Exceções são
    reemitidas com ``from None`` porque as originais carregam URL com ID de arquivo.
    """

    def __init__(self, session: object, timeout_seconds: float) -> None:
        self._session = session
        self._timeout = timeout_seconds

    def get_json(self, path: str, params: Mapping[str, str]) -> dict[str, Any]:
        body = self._get(path, params, _JSON_MAX_BYTES)
        try:
            payload = json.loads(body)
        except ValueError:
            raise DriveCaptureError(Code.UNEXPECTED_RESPONSE) from None
        if not isinstance(payload, dict):
            raise DriveCaptureError(Code.UNEXPECTED_RESPONSE)
        return payload

    def get_bytes(self, path: str, params: Mapping[str, str], max_bytes: int) -> bytes:
        return self._get(path, params, max_bytes)

    def _get(self, path: str, params: Mapping[str, str], max_bytes: int) -> bytes:
        check_path(path)
        get = self._session.get  # type: ignore[attr-defined]
        try:
            response = get(API_BASE + path, params=dict(params), timeout=self._timeout, stream=True)
        except Exception as exc:  # qualquer falha vira código controlado
            raise DriveCaptureError(classify_exception(exc)) from None
        try:
            if response.status_code >= 400:
                raise DriveCaptureError(
                    map_http_error(
                        response.status_code, _read_capped(response, _ERROR_BODY_MAX_BYTES)
                    )
                )
            body = _read_capped(response, max_bytes)
            if body is None:
                raise DriveCaptureError(Code.SIZE_LIMIT)
            return body
        except DriveCaptureError:
            raise
        except Exception as exc:
            raise DriveCaptureError(classify_exception(exc)) from None
        finally:
            response.close()


def _read_capped(response: Any, max_bytes: int) -> bytes | None:  # noqa: ANN401
    """Lê até ``max_bytes``; devolve ``None`` se o corpo for maior (nunca trunca)."""
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(_CHUNK):
        total += len(chunk)
        if total > max_bytes:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


@dataclass(frozen=True)
class FileMeta:
    file_id: str
    mime_type: str
    parents: tuple[str, ...]
    trashed: bool
    modified_time: str | None
    version: str | None
    size: int | None
    md5: str | None
    can_download: bool | None
    name: str | None = None

    def consistency_key(self) -> tuple[object, ...]:
        return (self.version, self.modified_time, self.md5, self.size, self.mime_type)


def _parse_meta(raw: Mapping[str, Any]) -> FileMeta:
    try:
        file_id = raw["id"]
        mime_type = raw["mimeType"]
    except KeyError:
        raise DriveCaptureError(Code.UNEXPECTED_RESPONSE) from None
    size = raw.get("size")
    capabilities = raw.get("capabilities") or {}
    can_download = capabilities.get("canDownload") if isinstance(capabilities, dict) else None
    return FileMeta(
        file_id=str(file_id),
        mime_type=str(mime_type),
        parents=tuple(str(p) for p in raw.get("parents") or ()),
        trashed=bool(raw.get("trashed", False)),
        modified_time=raw.get("modifiedTime"),
        version=None if raw.get("version") is None else str(raw["version"]),
        size=int(size) if size is not None else None,
        md5=raw.get("md5Checksum"),
        can_download=can_download if isinstance(can_download, bool) else None,
        name=raw.get("name"),
    )


@dataclass(frozen=True)
class Listing:
    files: tuple[FileMeta, ...]
    complete: bool
    incomplete_reason: str | None = None


class DriveClient:
    def __init__(
        self,
        transport: ReadOnlyTransport,
        *,
        shared_drive_id: str | None = None,
        max_retries: int = 2,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._transport = transport
        self._shared_drive_id = shared_drive_id
        self._max_retries = max_retries
        self._sleep = sleep

    def _drive_params(self) -> dict[str, str]:
        # Opções de Shared Drive só quando esse ambiente foi declarado na config.
        return {"supportsAllDrives": "true"} if self._shared_drive_id else {}

    def _with_retry(self, call: Callable[[], Any]) -> Any:  # noqa: ANN401
        attempt = 0
        while True:
            try:
                return call()
            except DriveCaptureError as exc:
                if exc.code not in RETRYABLE or attempt >= self._max_retries:
                    raise
                attempt += 1
                self._sleep(2.0**attempt)

    def authenticated_identity(self) -> str | None:
        payload = self._with_retry(
            lambda: self._transport.get_json("about", {"fields": "user(emailAddress)"})
        )
        user = payload.get("user")
        email = user.get("emailAddress") if isinstance(user, dict) else None
        return email if isinstance(email, str) else None

    def get_metadata(self, file_id: str, *, with_name: bool = False) -> FileMeta:
        fields = _META_FIELDS + (",name" if with_name else "")
        params = {"fields": fields, **self._drive_params()}
        raw = self._with_retry(lambda: self._transport.get_json(f"files/{file_id}", params))
        meta = _parse_meta(raw)
        if meta.file_id != file_id:
            raise DriveCaptureError(Code.UNEXPECTED_RESPONSE)
        return meta

    def list_children(
        self, folder_id: str, *, page_size: int, max_pages: int, with_name: bool = False
    ) -> Listing:
        fields = _META_FIELDS + (",name" if with_name else "")
        params: dict[str, str] = {
            # Consulta restrita à pasta autorizada — nunca listagem global filtrada depois.
            "q": f"'{folder_id}' in parents and trashed = false",
            "fields": f"nextPageToken,incompleteSearch,files({fields})",
            "pageSize": str(page_size),
            # Sob teto de páginas/fontes, a seleção é por metadado do Drive, nunca por título.
            "orderBy": "modifiedTime desc",
        }
        if self._shared_drive_id:
            params.update(
                {
                    "corpora": "drive",
                    "driveId": self._shared_drive_id,
                    "includeItemsFromAllDrives": "true",
                    "supportsAllDrives": "true",
                }
            )
        files: list[FileMeta] = []
        token: str | None = None
        for _ in range(max_pages):
            page_params = dict(params, **({"pageToken": token} if token else {}))
            payload = self._with_retry(lambda p=page_params: self._transport.get_json("files", p))
            raw_files = payload.get("files")
            if not isinstance(raw_files, list):
                raise DriveCaptureError(Code.UNEXPECTED_RESPONSE)
            files.extend(_parse_meta(item) for item in raw_files)
            if payload.get("incompleteSearch"):
                return Listing(tuple(files), complete=False, incomplete_reason="incomplete_search")
            token = payload.get("nextPageToken")
            if not token:
                return Listing(tuple(files), complete=True)
        return Listing(tuple(files), complete=False, incomplete_reason="listing_page_limit")

    def export(self, file_id: str, export_mime: str, max_bytes: int) -> bytes:
        params = {"mimeType": export_mime}
        return self._with_retry(
            lambda: self._transport.get_bytes(f"files/{file_id}/export", params, max_bytes)
        )

    def download(self, file_id: str, max_bytes: int) -> bytes:
        params = {"alt": "media", **self._drive_params()}
        return self._with_retry(
            lambda: self._transport.get_bytes(f"files/{file_id}", params, max_bytes)
        )
