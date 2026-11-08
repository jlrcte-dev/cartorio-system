"""Leitura do estado de unidades systemd via ``systemctl show`` (somente leitura).

Três tipos, três semânticas:

- ``service`` (persistente): saudável só ``active``/``running``. ``postgresql.service``
  do Debian/Ubuntu é guarda-chuva — reporta ``active``/``exited`` mesmo com o cluster
  parado —, por isso ``exited`` não passa: configure a instância
  ``postgresql@<versão>-<cluster>.service``.
- ``oneshot`` (job): inativo depois de uma execução bem-sucedida é o esperado. O estado
  do systemd vale por boot: sem execução desde o boot, a última tentativa é desconhecida
  (informação, não falha — a idade do backup cobre o atraso).
- ``timer``: precisa estar ``active`` e habilitado para sobreviver ao boot.

Exige systemd ≥ 251 (``--timestamp=unix``).
"""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.ops.config import UnitSpec
from app.ops.report import Status, signal, utc_iso

SHOW_PROPERTIES = (
    "Id",
    "LoadState",
    "ActiveState",
    "SubState",
    "UnitFileState",
    "Result",
    "ExecMainStatus",
    "ExecMainStartTimestamp",
    "ExecMainExitTimestamp",
    "NRestarts",
    "LastTriggerUSec",
    "NextElapseUSecRealtime",
)

# Estados de arquivo que impedem a unidade de voltar sozinha depois do boot.
_NOT_ENABLED = {"disabled", "masked", "masked-runtime", "bad"}

_UNIX_TS = re.compile(r"^@(\d+)(?:\.\d+)?$")


class SystemctlError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


ShowRunner = Callable[[str, str, float], str]


def run_systemctl_show(systemctl: str, unit: str, timeout: float) -> str:
    cmd = [
        systemctl,
        "show",
        "--no-pager",
        "--timestamp=unix",
        "--property=" + ",".join(SHOW_PROPERTIES),
        "--",
        unit,
    ]
    env = dict(os.environ, SYSTEMD_PAGER="cat", SYSTEMD_COLORS="0", LC_ALL="C")
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            stdin=subprocess.DEVNULL,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SystemctlError("systemd_unavailable") from exc
    except subprocess.TimeoutExpired as exc:
        raise SystemctlError("systemctl_timeout") from exc
    except OSError as exc:
        raise SystemctlError("systemctl_failed") from exc
    if proc.returncode != 0:
        # Ex.: "System has not been booted with systemd as init system".
        raise SystemctlError("systemctl_failed")
    return proc.stdout


def parse_show(text: str) -> dict[str, str]:
    props: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            props[key.strip()] = value.strip()
    return props


def parse_unix_timestamp(value: str | None) -> datetime | None:
    match = _UNIX_TS.match(value or "")
    if not match or int(match.group(1)) == 0:
        return None
    return datetime.fromtimestamp(int(match.group(1)), tz=UTC)


def _iso(value: str | None) -> str | None:
    moment = parse_unix_timestamp(value)
    return utc_iso(moment) if moment else None


def evaluate_unit(kind: str, props: dict[str, str]) -> dict[str, Any]:
    load = props.get("LoadState", "")
    active = props.get("ActiveState", "")
    sub = props.get("SubState", "")
    file_state = props.get("UnitFileState", "")
    facts: dict[str, Any] = {
        "kind": kind,
        "active_state": active,
        "sub_state": sub,
        "unit_file_state": file_state,
    }
    if load == "not-found":
        return signal(Status.FAIL, "unit_not_found", **facts)
    if load != "loaded":
        return signal(Status.FAIL, "unit_not_loaded", load_state=load, **facts)

    if kind == "timer":
        facts["last_trigger_utc"] = _iso(props.get("LastTriggerUSec"))
        facts["next_elapse_utc"] = _iso(props.get("NextElapseUSecRealtime"))
        if active != "active":
            return signal(Status.FAIL, "timer_inactive", **facts)
        if file_state in _NOT_ENABLED:
            return signal(Status.FAIL, "timer_not_enabled", **facts)
        return signal(Status.OK, "timer_active", **facts)

    result = props.get("Result", "")
    facts["result"] = result
    facts["exit_status"] = _int_or_none(props.get("ExecMainStatus"))
    facts["started_utc"] = _iso(props.get("ExecMainStartTimestamp"))
    facts["finished_utc"] = _iso(props.get("ExecMainExitTimestamp"))

    if kind == "oneshot":
        if active == "activating":
            return signal(Status.OK, "running_now", **facts)
        if active == "failed" or result not in ("", "success"):
            return signal(Status.FAIL, "last_run_failed", **facts)
        if active in ("inactive", "active"):
            if facts["started_utc"] is None:
                return signal(Status.OK, "no_run_since_boot", **facts)
            return signal(Status.OK, "last_run_succeeded", **facts)
        return signal(Status.FAIL, "unexpected_state", **facts)

    facts["n_restarts"] = _int_or_none(props.get("NRestarts"))
    if active != "active" or sub != "running":
        return signal(Status.FAIL, "unit_not_running", **facts)
    if file_state in _NOT_ENABLED:
        return signal(Status.FAIL, "unit_not_enabled", **facts)
    return signal(Status.OK, "running", **facts)


def _int_or_none(value: str | None) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except ValueError:
        return None


def probe_unit(
    spec: UnitSpec, *, systemctl: str, timeout: float, runner: ShowRunner = run_systemctl_show
) -> dict[str, Any]:
    try:
        output = runner(systemctl, spec.name, timeout)
    except SystemctlError as exc:
        return signal(Status.INCONCLUSIVE, exc.reason, kind=spec.kind)
    return evaluate_unit(spec.kind, parse_show(output))
