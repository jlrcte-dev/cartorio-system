"""Armazenamento local privado das capturas, com publicação atômica por fonte.

Layout em ``data_dir``::

    registry.json                     ID do Drive → chave local estável
    run.lock                          exclusão mútua entre execuções
    sources/<chave>/state.json        ponto de commit: tentativa, sucesso, atual e anterior
    sources/<chave>/gen-<...>/        geração imutável: content.<ext> + manifest.json
    sources/<chave>/staging-<...>/    geração em montagem — nunca consumir

Quem consome lê ``state.json`` e abre só a geração que ele aponta. A geração é gravada
inteira em ``staging-*``, renomeada para ``gen-*`` e só então referenciada pela troca
atômica de ``state.json`` (``os.replace``). Falha antes disso deixa o estado anterior
intacto; diretório órfão é removido na próxima publicação da mesma fonte.

Caminhos usam apenas chaves locais (alias ou ``<alias_da_pasta>-NNNN``), nunca títulos
remotos.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.modules.drive_capture.errors import Code, DriveCaptureError

STATE_VERSION = 1
MANIFEST_VERSION = 1

_GEN_RE = re.compile(r"^gen-\d{8}T\d{6}Z-[0-9a-f]{8}$")
_STAGING_RE = re.compile(r"^staging-[0-9a-f]{16}$")
_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}(?:-\d{4})?$")
_POSIX = os.name == "posix"


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mkdir_private(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if _POSIX:
        path.chmod(0o700)


def _write_private(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())


def atomic_write_bytes(path: Path, data: bytes) -> None:
    _mkdir_private(path.parent)
    tmp = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    try:
        _write_private(tmp, data)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_bytes(path, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        raise DriveCaptureError(Code.STORE_ERROR, "estado local ilegível") from None
    return payload if isinstance(payload, dict) else None


@dataclass(frozen=True)
class Acquisition:
    content: bytes
    extension: str
    method: str
    source_mime: str
    exported_mime: str | None
    modified_time: str | None
    version: str | None
    drive_size: int | None
    drive_md5: str | None


class RunLock:
    def __init__(self, data_dir: Path, run_id: str) -> None:
        self._path = data_dir / "run.lock"
        self._run_id = run_id

    def __enter__(self) -> RunLock:
        _mkdir_private(self._path.parent)
        try:
            _write_private(self._path, json.dumps({"run_id": self._run_id}).encode())
        except FileExistsError:
            raise DriveCaptureError(Code.RUN_LOCKED) from None
        return self

    def __exit__(self, *exc: object) -> None:
        self._path.unlink(missing_ok=True)


class CaptureStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.sources_dir = data_dir / "sources"
        self._registry_path = data_dir / "registry.json"

    # -- registro ID → chave ------------------------------------------------------------

    def _registry(self) -> dict[str, Any]:
        registry = _read_json(self._registry_path)
        if registry is None:
            return {"version": STATE_VERSION, "next_seq": 1, "entries": {}}
        return registry

    def key_for(self, file_id: str, base_alias: str, *, folder_alias: str | None) -> str:
        """Chave local estável por ID do Drive: renomear o arquivo não cria outra fonte.

        ``folder_alias`` é ``None`` para fonte explícita por ID; para filho de pasta,
        registra a pasta de origem, usada para detectar quando ele sai do recorte.
        """
        registry = self._registry()
        entry = registry["entries"].get(file_id)
        if entry is not None:
            if entry.get("folder") != folder_alias:
                entry["folder"] = folder_alias
                atomic_write_json(self._registry_path, registry)
            return str(entry["key"])
        taken = {str(e["key"]) for e in registry["entries"].values()}
        if folder_alias is None and base_alias not in taken:
            key = base_alias
        else:
            seq = int(registry["next_seq"])
            registry["next_seq"] = seq + 1
            key = f"{base_alias}-{seq:04d}"
        registry["entries"][file_id] = {
            "key": key,
            "folder": folder_alias,
            "registered_at": iso(utc_now()),
        }
        atomic_write_json(self._registry_path, registry)
        return key

    def folder_members(self, folder_alias: str) -> dict[str, str]:
        """IDs registrados como filhos da pasta → chave local."""
        return {
            fid: str(e["key"])
            for fid, e in self._registry()["entries"].items()
            if e.get("folder") == folder_alias
        }

    # -- estado por fonte ------------------------------------------------------------------

    def _source_dir(self, key: str) -> Path:
        if not _KEY_RE.match(key):
            raise DriveCaptureError(Code.STORE_ERROR, "chave local inválida")
        return self.sources_dir / key

    def read_state(self, key: str) -> dict[str, Any] | None:
        return _read_json(self._source_dir(key) / "state.json")

    def _base_state(self, key: str, file_id: str) -> dict[str, Any]:
        return self.read_state(key) or {
            "version": STATE_VERSION,
            "key": key,
            "file_id": file_id,
            "eligibility": "eligible",
            "last_attempt": None,
            "last_success_at": None,
            "current": None,
            "previous": None,
        }

    def record_failure(
        self, key: str, file_id: str, code: Code, run_id: str, at: datetime
    ) -> dict[str, Any]:
        """Atualiza só a tentativa: falha nunca renova o último sucesso nem a captura."""
        state = self._base_state(key, file_id)
        state["last_attempt"] = {
            "at": iso(at),
            "run_id": run_id,
            "result": "failed",
            "code": str(code),
        }
        if code in (Code.OUT_OF_BOUNDARY, Code.TRASHED):
            state["eligibility"] = "suspended"
        atomic_write_json(self._source_dir(key) / "state.json", state)
        return state

    def publish(
        self,
        key: str,
        file_id: str,
        acquisition: Acquisition,
        *,
        alias: str,
        family: str,
        run_id: str,
        captured_at: datetime,
    ) -> dict[str, Any]:
        source_dir = self._source_dir(key)
        _mkdir_private(source_dir)
        sha256 = hashlib.sha256(acquisition.content).hexdigest()
        content_name = f"content.{acquisition.extension}"
        manifest = {
            "manifest_version": MANIFEST_VERSION,
            "key": key,
            "alias": alias,
            "family": family,
            "drive_file_id": file_id,
            "source_mime": acquisition.source_mime,
            "exported_mime": acquisition.exported_mime,
            "acquisition_method": acquisition.method,
            "drive_modified_time": acquisition.modified_time,
            "drive_version": acquisition.version,
            "drive_size": acquisition.drive_size,
            "drive_md5": acquisition.drive_md5,
            "captured_at": iso(captured_at),
            "run_id": run_id,
            "content_file": content_name,
            "bytes": len(acquisition.content),
            "sha256": sha256,
        }

        staging = source_dir / f"staging-{secrets.token_hex(8)}"
        generation = f"gen-{captured_at.strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(4)}"
        try:
            _mkdir_private(staging)
            _write_private(staging / content_name, acquisition.content)
            _write_private(
                staging / "manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
            )
            os.replace(staging, source_dir / generation)
        except OSError:
            shutil.rmtree(staging, ignore_errors=True)
            raise DriveCaptureError(Code.STORE_ERROR) from None

        state = self._base_state(key, file_id)
        state["previous"] = state.get("current")
        state["current"] = {
            "generation": generation,
            "captured_at": iso(captured_at),
            "content_file": content_name,
            "bytes": len(acquisition.content),
            "sha256": sha256,
            "drive_modified_time": acquisition.modified_time,
            "drive_version": acquisition.version,
            "acquisition_method": acquisition.method,
        }
        state["last_success_at"] = iso(captured_at)
        state["last_attempt"] = {
            "at": iso(captured_at),
            "run_id": run_id,
            "result": "captured",
            "code": None,
        }
        state["eligibility"] = "eligible"
        atomic_write_json(source_dir / "state.json", state)
        self._prune(source_dir, state)
        return state

    def _prune(self, source_dir: Path, state: dict[str, Any]) -> None:
        """Mantém só a geração atual e a anterior; só toca diretórios do próprio coletor."""
        keep = {ref["generation"] for ref in (state.get("current"), state.get("previous")) if ref}
        for child in source_dir.iterdir():
            if not child.is_dir() or child.is_symlink() or child.name in keep:
                continue
            if _GEN_RE.match(child.name) or _STAGING_RE.match(child.name):
                shutil.rmtree(child, ignore_errors=True)

    def current_content_path(self, key: str) -> Path | None:
        state = self.read_state(key)
        if not state or not state.get("current"):
            return None
        ref = state["current"]
        return self._source_dir(key) / ref["generation"] / ref["content_file"]
