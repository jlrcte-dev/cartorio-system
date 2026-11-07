"""Alerta a partir do relatório do verificador — destino local de teste (spool).

Ponto de integração: ``build_alert`` produz o payload, ``write_alert`` o entrega ao
spool. Um canal futuro (mensageria, e-mail) consome o mesmo payload, lendo o spool ou
substituindo ``write_alert``; o verificador não muda. Sem deduplicação nem retenção:
cada execução com problema gera um arquivo, e política de repetição é decisão do canal.

Também alerta quando NÃO há relatório utilizável — ausente, ilegível ou velho demais —,
porque é exatamente o caso em que o verificador quebrou antes de escrever.

Acionado pelo ``OnFailure=`` (``--expect-failure``), nunca responde "sem alerta": se a
execução que falhou não escreveu relatório, o que está em disco é o da execução
anterior — possivelmente saudável — e não pode silenciar a falha. O systemd (≥ 251)
entrega ``MONITOR_*`` à unidade acionada; o ``MONITOR_INVOCATION_ID`` é comparado com
o ``invocation_id`` que o ``check`` grava no relatório.
"""

from __future__ import annotations

import json
import secrets
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.ops.report import SCHEMA as REPORT_SCHEMA
from app.ops.report import Status, utc_iso, write_json_atomic

ALERT_SCHEMA = "cartorio_system.ops.alert"
ALERT_SCHEMA_VERSION = "1.0"
_MAX_REPORT_BYTES = 1024 * 1024
_PROBLEM_STATUSES = (Status.FAIL.value, Status.INCONCLUSIVE.value)
_MONITOR_VARIABLES = {
    "MONITOR_UNIT": "unit",
    "MONITOR_INVOCATION_ID": "invocation_id",
    "MONITOR_SERVICE_RESULT": "service_result",
    "MONITOR_EXIT_CODE": "exit_code",
    "MONITOR_EXIT_STATUS": "exit_status",
}


def load_report(
    path: Path, now: datetime, max_age: timedelta
) -> tuple[dict[str, Any] | None, str | None]:
    """(relatório, problema). Problema: report_missing | report_unreadable |
    report_invalid | report_stale."""
    try:
        if path.stat().st_size > _MAX_REPORT_BYTES:
            return None, "report_invalid"
        report = json.loads(path.read_bytes())
    except FileNotFoundError:
        return None, "report_missing"
    except (OSError, UnicodeDecodeError, ValueError):
        return None, "report_unreadable"
    if not isinstance(report, dict) or report.get("schema") != REPORT_SCHEMA:
        return None, "report_invalid"
    try:
        generated = datetime.strptime(str(report.get("generated_at")), "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None, "report_invalid"
    if now - generated.replace(tzinfo=UTC) > max_age:
        return report, "report_stale"
    return report, None


def monitor_facts(environ: Mapping[str, str]) -> dict[str, str]:
    """O que o systemd informa sobre a execução que acionou o ``OnFailure=``."""
    return {
        name: environ[variable][:64]
        for variable, name in _MONITOR_VARIABLES.items()
        if environ.get(variable)
    }


def failure_problem(report: dict[str, Any], monitor: Mapping[str, str]) -> str | None:
    """Com o alerta acionado por falha: o relatório em disco descreve ESSA falha?"""
    expected = monitor.get("invocation_id")
    if expected and report.get("invocation_id") != expected:
        return "report_not_from_failed_run"
    if report.get("overall") == Status.OK.value:
        return "run_failed_but_report_healthy"
    return None


def problems_of(report: dict[str, Any]) -> list[dict[str, str]]:
    checks = report.get("checks")
    if not isinstance(checks, dict):
        return []
    return [
        {"check": name, "status": str(check["status"]), "reason": str(check.get("reason"))}
        for name, check in checks.items()
        if isinstance(check, dict) and check.get("status") in _PROBLEM_STATUSES
    ]


def build_alert(
    report: dict[str, Any] | None,
    problem: str | None,
    now: datetime,
    *,
    monitor: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    report = report or {}
    if problem is None and not report:
        problem = "report_missing"
    # Só um relatório que descreve esta execução tem problemas "atuais" a listar.
    current = problem is None
    if current:
        level, reason = str(report.get("overall")), str(report.get("reason"))
    else:
        level, reason = Status.INCONCLUSIVE.value, problem
    problems = problems_of(report) if current else []
    return {
        "schema": ALERT_SCHEMA,
        "schema_version": ALERT_SCHEMA_VERSION,
        "emitted_at": utc_iso(now),
        "level": level,
        "reason": reason,
        "report_generated_at": report.get("generated_at"),
        "report_overall": report.get("overall"),
        "report_exit_code": report.get("exit_code"),
        "failed_run": dict(monitor) if monitor else None,
        "problems": problems,
        "summary": "; ".join(f"{p['check']}: {p['reason']}" for p in problems) or reason,
    }


def write_alert(spool: Path, alert: dict[str, Any], now: datetime) -> Path:
    name = f"alert-{now.strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(3)}.json"
    target = spool / name
    write_json_atomic(target, alert)
    return target
