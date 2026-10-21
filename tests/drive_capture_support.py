"""Drive sintético em memória para os testes do coletor somente leitura.

Implementa o mesmo protocolo do transporte real (``get_json``/``get_bytes``), aplica a
mesma allowlist de caminhos e registra cada chamada. Todos os IDs, nomes e conteúdos
são fictícios.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.modules.drive_capture.config import (
    DOCX,
    GOOGLE_DOC,
    GOOGLE_FOLDER,
    GOOGLE_SHEET,
    GOOGLE_SHORTCUT,
    XLSX,
    CaptureConfig,
    parse_config,
)
from app.modules.drive_capture.drive_client import DriveClient, check_path
from app.modules.drive_capture.errors import Code, DriveCaptureError

IDENTITY = "leitor-cartorio@projeto-ficticio.iam.gserviceaccount.com"
FOLDER_A = "FOLDERaaaaaaaaaaaaaa01"
FOLDER_B = "FOLDERbbbbbbbbbbbbbb02"
SUBFOLDER = "FOLDERsubsubsubsubsu03"
SHEET_1 = "SHEETfinanceiro000001"
DOC_1 = "DOCrelatorio00000000001"

_Q_RE = re.compile(r"^'([A-Za-z0-9_-]+)' in parents and trashed = false$")


def xlsx_bytes(marker: str) -> bytes:
    return b"PK\x03\x04" + marker.encode("utf-8")


class FakeDrive:
    def __init__(self) -> None:
        self.files: dict[str, dict[str, Any]] = {}
        self.calls: list[tuple[str, str, dict[str, str]]] = []
        self.failures: dict[tuple[str, str], list[Code]] = {}
        self.after_content: dict[str, Callable[[], None]] = {}
        self.identity = IDENTITY

    # -- montagem ------------------------------------------------------------------------

    def add(
        self,
        file_id: str,
        mime: str,
        *,
        parents: tuple[str, ...] = (),
        content: bytes | None = None,
        name: str = "Planilha fictícia",
        trashed: bool = False,
        can_download: bool = True,
        stored: bool = False,
    ) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "id": file_id,
            "mimeType": mime,
            "parents": list(parents),
            "name": name,
            "trashed": trashed,
            "version": 1,
            "modifiedTime": "2026-10-19T11:00:00.000Z",
            "canDownload": can_download,
            "stored": stored,
            "content": content if content is not None else xlsx_bytes(f"conteudo-{file_id}"),
        }
        self.files[file_id] = entry
        return entry

    def touch(self, file_id: str, content: bytes | None = None) -> None:
        entry = self.files[file_id]
        entry["version"] += 1
        stamp = datetime(2026, 10, 19, 11, tzinfo=UTC) + timedelta(minutes=entry["version"])
        entry["modifiedTime"] = stamp.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        if content is not None:
            entry["content"] = content

    def fail(self, op: str, file_id: str, *codes: Code) -> None:
        self.failures[(op, file_id)] = list(codes)

    def _maybe_fail(self, op: str, file_id: str) -> None:
        queue = self.failures.get((op, file_id))
        if queue:
            raise DriveCaptureError(queue.pop(0))

    def _meta(self, entry: dict[str, Any], fields: str) -> dict[str, Any]:
        meta = {
            "id": entry["id"],
            "mimeType": entry["mimeType"],
            "parents": list(entry["parents"]),
            "trashed": entry["trashed"],
            "modifiedTime": entry["modifiedTime"],
            "version": str(entry["version"]),
            "capabilities": {"canDownload": entry["canDownload"]},
        }
        if entry["stored"]:
            meta["size"] = str(len(entry["content"]))
            meta["md5Checksum"] = hashlib.md5(entry["content"]).hexdigest()
        if fields.endswith(",name") or ",name)" in fields:
            meta["name"] = entry["name"]
        return meta

    # -- protocolo do transporte -----------------------------------------------------------

    def get_json(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        check_path(path)
        self.calls.append(("GET", path, dict(params)))
        if path == "about":
            self._maybe_fail("about", "-")
            return {"user": {"emailAddress": self.identity}}
        if path == "files":
            match = _Q_RE.match(params["q"])
            assert match, "listagem sem restrição de pasta"
            folder_id = match.group(1)
            self._maybe_fail("list", folder_id)
            children = [
                e for e in self.files.values() if folder_id in e["parents"] and not e["trashed"]
            ]
            start = int(params.get("pageToken", "0"))
            size = int(params["pageSize"])
            page = children[start : start + size]
            payload: dict[str, Any] = {"files": [self._meta(e, params["fields"]) for e in page]}
            if start + size < len(children):
                payload["nextPageToken"] = str(start + size)
            return payload
        file_id = path.removeprefix("files/")
        self._maybe_fail("meta", file_id)
        if file_id not in self.files:
            raise DriveCaptureError(Code.NOT_FOUND)
        return self._meta(self.files[file_id], params["fields"])

    def get_bytes(self, path: str, params: dict[str, str], max_bytes: int) -> bytes:
        check_path(path)
        self.calls.append(("GET", path, dict(params)))
        if path.endswith("/export"):
            file_id = path.removeprefix("files/").removesuffix("/export")
            op = "export"
            entry = self.files[file_id]
            expected = {GOOGLE_SHEET: XLSX, GOOGLE_DOC: DOCX}[entry["mimeType"]]
            assert params["mimeType"] == expected
        else:
            file_id = path.removeprefix("files/")
            op = "download"
            assert params.get("alt") == "media"
            entry = self.files[file_id]
        self._maybe_fail(op, file_id)
        content = entry["content"]
        hook = self.after_content.pop(file_id, None)
        if hook:
            hook()
        if len(content) > max_bytes:
            raise DriveCaptureError(Code.SIZE_LIMIT)
        return content

    # -- consultas dos testes --------------------------------------------------------------

    def paths(self) -> list[str]:
        return [path for _, path, _ in self.calls]

    def content_calls(self) -> list[str]:
        return [
            path
            for _, path, params in self.calls
            if path.endswith("/export") or params.get("alt") == "media"
        ]


def make_config(tmp_path: Path, **overrides: Any) -> CaptureConfig:
    data: dict[str, Any] = {
        "version": 1,
        "credentials_file": str(tmp_path / "credencial-ficticia.json"),
        "data_dir": str(tmp_path / "dados"),
        "expected_identity": IDENTITY,
        "files": [],
        "folders": [],
    }
    data.update(overrides)
    return parse_config(data, tmp_path)


def make_client(
    drive: FakeDrive, config: CaptureConfig, sleeps: list[float] | None = None
) -> DriveClient:
    record = sleeps if sleeps is not None else []
    return DriveClient(
        drive,
        shared_drive_id=config.shared_drive_id,
        max_retries=config.limits.max_retries,
        sleep=record.append,
    )


FOLDER_RULE = {"mime_types": [GOOGLE_SHEET]}
SHORTCUT = GOOGLE_SHORTCUT
FOLDER = GOOGLE_FOLDER
