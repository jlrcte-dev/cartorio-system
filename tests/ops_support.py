"""Apoio dos testes do verificador operacional (CARTORIO-OPS-1). Tudo sintético.

- relógio fixo (``NOW``) para os testes de idade;
- fábrica de publicações no formato da rotina de backup (``backup-<carimbo>.dump`` +
  manifesto ``arquivo/sha256/tamanho_bytes/gerado_em_utc/database``);
- systemd sintético: ``FakeSystemd`` responde como ``systemctl show``;
- API real efêmera (uvicorn) e SQLite migrado pelo Alembic, em diretório temporário.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from app.ops.systemd import SystemctlError

REPO_ROOT = Path(__file__).resolve().parent.parent
NOW = datetime(2026, 11, 7, 12, 0, 0, tzinfo=UTC)
CONTENT = b"PGDMP-artefato-sintetico-de-teste"
_REMOVE = object()


def fixed_clock(moment: datetime = NOW):
    return lambda: moment


def stamp_of(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def unix(moment: datetime) -> str:
    return f"@{int(moment.timestamp())}"


def write_publication(
    directory: Path,
    recovery_point: datetime,
    *,
    content: bytes = CONTENT,
    manifest: bool = True,
    overrides: dict | None = None,
    file_mtime: datetime | None = None,
) -> tuple[Path, Path]:
    """Publica como a rotina: dump primeiro, manifesto depois (se ``manifest``)."""
    directory.mkdir(parents=True, exist_ok=True)
    stamp = stamp_of(recovery_point)
    dump = directory / f"backup-{stamp}.dump"
    dump.write_bytes(content)
    data = {
        "arquivo": dump.name,
        "sha256": hashlib.sha256(content).hexdigest(),
        "tamanho_bytes": len(content),
        "gerado_em_utc": stamp,
        "database": "cartorio_lab",
    }
    for key, value in (overrides or {}).items():
        if value is _REMOVE:
            data.pop(key, None)
        else:
            data[key] = value
    manifest_path = directory / f"backup-{stamp}.json"
    if manifest:
        manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    if file_mtime is not None:
        ts = file_mtime.timestamp()
        os.utime(dump, (ts, ts))
        if manifest:
            os.utime(manifest_path, (ts, ts))
    return dump, manifest_path


REMOVE = _REMOVE


def service_props(active="active", sub="running", file_state="enabled", restarts="0") -> dict:
    return {
        "LoadState": "loaded",
        "ActiveState": active,
        "SubState": sub,
        "UnitFileState": file_state,
        "Result": "success",
        "ExecMainStatus": "0",
        "NRestarts": restarts,
    }


def oneshot_props(
    active="inactive", result="success", status="0", started: datetime | None = NOW
) -> dict:
    return {
        "LoadState": "loaded",
        "ActiveState": active,
        "SubState": "dead" if active != "failed" else "failed",
        "UnitFileState": "static",
        "Result": result,
        "ExecMainStatus": status,
        "ExecMainStartTimestamp": unix(started) if started else "",
        "ExecMainExitTimestamp": unix(started + timedelta(seconds=2)) if started else "",
    }


def timer_props(active="active", file_state="enabled") -> dict:
    return {
        "LoadState": "loaded",
        "ActiveState": active,
        "SubState": "waiting" if active == "active" else "dead",
        "UnitFileState": file_state,
        "LastTriggerUSec": unix(NOW - timedelta(hours=7)),
        "NextElapseUSecRealtime": unix(NOW + timedelta(hours=17)),
    }


class FakeSystemd:
    """Substitui ``run_systemctl_show``: devolve texto no formato do ``systemctl show``."""

    def __init__(self, units: dict[str, dict] | None = None, error: str | None = None) -> None:
        self.units = units or {}
        self.error = error
        self.calls: list[str] = []

    def __call__(self, systemctl: str, unit: str, timeout: float) -> str:
        self.calls.append(unit)
        if self.error:
            raise SystemctlError(self.error)
        props = self.units.get(unit, {"LoadState": "not-found", "ActiveState": "inactive"})
        return "\n".join(f"{k}={v}" for k, v in {"Id": unit, **props}.items()) + "\n"


def healthy_systemd() -> FakeSystemd:
    return FakeSystemd(
        {
            "cartorio-lab.service": service_props(),
            "postgresql@18-main.service": service_props(),
            "cartorio-lab-backup.service": oneshot_props(),
            "cartorio-lab-backup.timer": timer_props(),
        }
    )


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def clean_env(**extra: str) -> dict[str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("CARTORIO_OPS_") and k != "DATABASE_URL"
    }
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(extra)
    return env


def migrate_sqlite(db_path: Path, revision: str = "head") -> str:
    url = f"sqlite:///{db_path.as_posix()}"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", revision],
        cwd=REPO_ROOT,
        env=clean_env(DATABASE_URL=url),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return url


@contextmanager
def running_app(database_url: str, app_name: str, log_dir: Path) -> Iterator[str]:
    """API real (uvicorn) em porta livre de loopback; devolve a URL do /health."""
    port = free_port()
    log_path = log_dir / f"uvicorn-{port}.log"
    env = clean_env(DATABASE_URL=database_url, APP_NAME=app_name, DEBUG="false")
    with log_path.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=REPO_ROOT,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
    health_url = f"http://127.0.0.1:{port}/api/v1/health"
    try:
        with httpx.Client(trust_env=False, timeout=5) as client:
            for _ in range(100):
                if process.poll() is not None:
                    raise AssertionError(log_path.read_text(encoding="utf-8"))
                try:
                    if client.get(health_url).status_code == 200:
                        break
                except httpx.TransportError:
                    time.sleep(0.2)
            else:
                raise AssertionError("uvicorn não respondeu a tempo")
        yield health_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def run_cli(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "app.ops.cli", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
