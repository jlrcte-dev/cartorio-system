"""Observador fora do host — piloto da CARTORIO-OPS-2.

Roda numa máquina separada da VM e nunca acessa banco: lê o último relatório do
verificador (``cartorio_system.ops.check`` 1.0, trazido até aqui por um transporte que é
decisão de implantação) e as gerações da cópia externa (:mod:`app.ops.offsite`). Três
avaliações separadas, que não se substituem:

- ``application_signal`` — há relatório válido e recente? Sem sinal fresco é falha: é o
  caso em que a VM ou o host caíram e nenhum ``OnFailure=`` dentro deles disparou;
- ``last_check`` — o que o último relatório válido disse, mesmo vencido;
- ``offsite_copy`` — a geração mais nova é íntegra e do banco esperado, e o ponto de
  recuperação da última válida (do manifesto, nunca do mtime) está dentro do limite.

``last_valid_copy`` sai sempre à parte: é a evidência de que há de onde restaurar,
independente do sinal da aplicação. A saída não traz caminho, nome de banco nem texto
livre do relatório — só estados e motivos estáveis.
"""

from __future__ import annotations

import argparse
import json
import math
import stat
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.ops.backup import FUTURE_TOLERANCE
from app.ops.config import CHECK_NAMES, DATABASE_NAME
from app.ops.offsite import read_copies
from app.ops.report import (
    EXIT_CODES,
    Clock,
    Status,
    signal,
    utc_iso,
    utc_now,
    worst,
)
from app.ops.report import SCHEMA as CHECK_SCHEMA

OBSERVATION_SCHEMA = "cartorio_system.ops.offsite_observation"
SCHEMA_VERSION = "1.0"
MAX_SIGNAL_BYTES = 1024 * 1024
# Limiares de LABORATÓRIO: o verificador de laboratório roda a cada 30 min e a rotina de
# backup é diária. Os reais são decisão de implantação.
LAB_SIGNAL_MAX_AGE_MINUTES = 45.0
LAB_COPY_MAX_AGE_HOURS = 26.0
_PROBLEMS_LIMIT = 10
_UNRECOGNIZED = "unrecognized"
# Vocabulário do contrato ``cartorio_system.ops.check`` 1.0, como o verificador o emite
# (app.ops.report, checks, backup, systemd, verifier). O formato de código sozinho não
# basta: um valor qualquer em minúsculas e dígitos — um segredo, um hash — passaria nele.
_CHECK_NAMES = frozenset(CHECK_NAMES)
_CHECK_STATUSES = frozenset(
    s.value for s in (Status.OK, Status.FAIL, Status.INCONCLUSIVE, Status.SKIPPED)
)
_REPORT_REASONS = frozenset(
    {
        "all_checks_ok",
        "check_failed",
        "check_inconclusive",
        "no_checks_executed",
        "output_not_published",
        "verifier_internal_error",
    }
)
_CHECK_REASONS = frozenset(
    {
        # comuns e do verificador
        "config_invalid",
        "config_missing",
        "no_signal",
        "not_configured",
        "not_selected",
        "unexpected_error",
        # api
        "app_mismatch",
        "healthy",
        "http_status",
        "timeout",
        "unexpected_body",
        "unexpected_response",
        "unreachable",
        # unidades systemd (api e backup)
        "last_attempt_failed",
        "last_run_failed",
        "last_run_succeeded",
        "no_run_since_boot",
        "running",
        "running_now",
        "systemctl_failed",
        "systemctl_timeout",
        "systemd_unavailable",
        "timer_active",
        "timer_inactive",
        "timer_not_enabled",
        "unexpected_state",
        "unit_not_enabled",
        "unit_not_found",
        "unit_not_loaded",
        "unit_not_running",
        # database e alembic
        "auth_failed",
        "database_missing",
        "database_unavailable",
        "dialect_mismatch",
        "ok",
        "query_failed",
        "release_unreadable",
        "revision_behind",
        "revision_match",
        "revision_unknown",
        "unavailable",
        "version_table_missing",
        "version_table_unreadable",
        # backup: identidade, diretório, publicações, idade e restauração
        "expected_database_ambiguous",
        "expected_database_conflict",
        "expected_database_explicit",
        "expected_database_from_connection",
        "expected_database_from_dsn",
        "expected_database_missing",
        "expected_database_unproven",
        "expected_database_unresolved",
        "backup_dir_unavailable",
        "backup_dir_unreadable",
        "artifact_missing",
        "artifact_not_regular",
        "artifact_unreadable",
        "available",
        "backup_missing",
        "backup_stale",
        "complete",
        "database_mismatch",
        "digest_mismatch",
        "digest_verified",
        "manifest_incomplete",
        "manifest_inconsistent",
        "manifest_invalid",
        "manifest_missing",
        "manifest_not_usable",
        "manifest_unparseable",
        "manifest_unreadable",
        "no_copy",
        "no_unverifiable_copy",
        "no_valid_copy",
        "no_verifiable_copy",
        "recovery_point_in_future",
        "recovery_point_unreadable",
        "reference_outside_dir",
        "restore_evidence_invalid",
        "restore_evidence_missing",
        "restore_evidence_unreadable",
        "restore_test_failed",
        "restore_test_stale",
        "restore_verified",
        "size_mismatch",
        "unverifiable_copy",
        "within_max_age",
    }
)
_CHECK_RESULTS = {
    "ok": (Status.OK, "check_ok"),
    "fail": (Status.FAIL, "check_failed"),
    "inconclusive": (Status.INCONCLUSIVE, "check_inconclusive"),
}


def _parse_utc(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None


def _known(value: object, vocabulary: frozenset[str]) -> str:
    """Texto vindo de outra máquina: só código do contrato passa; o resto vira marcador."""
    return value if isinstance(value, str) and value in vocabulary else _UNRECOGNIZED


def _minutes(delta: timedelta) -> float:
    return round(delta.total_seconds() / 60, 1)


def _hours(delta: timedelta) -> float:
    return round(delta.total_seconds() / 3600, 1)


def _invalid(detail: str) -> tuple[dict[str, Any], None]:
    return signal(Status.FAIL, "signal_invalid", detail=detail), None


def application_signal(
    path: Path, now: datetime, max_age: timedelta
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Sinal da aplicação e, quando o relatório é válido, o próprio relatório."""
    try:
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            return _invalid("not_a_file")
        if info.st_size > MAX_SIGNAL_BYTES:
            return _invalid("too_large")
        raw = path.read_bytes()
    except FileNotFoundError:
        return signal(Status.FAIL, "signal_missing"), None
    except PermissionError:
        return signal(Status.INCONCLUSIVE, "signal_unreadable"), None
    try:
        report = json.loads(raw)
    except (UnicodeDecodeError, ValueError):
        return _invalid("unparseable")
    if not isinstance(report, dict) or report.get("schema") != CHECK_SCHEMA:
        return _invalid("schema")
    version = report.get("schema_version")
    if not isinstance(version, str) or version.split(".")[0] != "1":
        return _invalid("schema_version")
    generated = _parse_utc(report.get("generated_at"))
    if generated is None:
        return _invalid("generated_at")
    overall = report.get("overall")
    if not isinstance(overall, str) or overall not in _CHECK_RESULTS:  # lista/objeto: TypeError
        return _invalid("overall")
    report = {**report, "generated_at": utc_iso(generated)}  # normalizado, já validado
    facts = {
        "generated_at": utc_iso(generated),
        "age_minutes": _minutes(now - generated),
        "max_age_minutes": _minutes(max_age),
    }
    if generated > now + FUTURE_TOLERANCE:
        return signal(Status.FAIL, "signal_from_future", **facts), report
    if now - generated > max_age:
        return signal(Status.FAIL, "signal_stale", **facts), report
    return signal(Status.OK, "signal_fresh", **facts), report


def last_check(report: dict[str, Any] | None) -> dict[str, Any]:
    """O que o último relatório válido disse, com as checagens que não passaram."""
    if report is None:
        return signal(Status.NOT_EVALUATED, "check_unknown")
    status, reason = _CHECK_RESULTS[report["overall"]]
    problems: list[dict[str, str]] = []
    checks = report.get("checks")
    if isinstance(checks, dict):
        for name, check in sorted(checks.items())[:_PROBLEMS_LIMIT]:
            if isinstance(check, dict) and check.get("status") not in ("ok", "skipped"):
                problems.append(
                    {
                        "check": _known(name, _CHECK_NAMES),
                        "status": _known(check.get("status"), _CHECK_STATUSES),
                        "reason": _known(check.get("reason"), _CHECK_REASONS),
                    }
                )
    return signal(
        status,
        reason,
        generated_at=report["generated_at"],
        reported_reason=_known(report.get("reason"), _REPORT_REASONS),
        problems=problems,
    )


def offsite_copy(
    copies: Path, expected_database: str, now: datetime, max_age: timedelta
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Estado da cópia externa e, à parte, a última cópia válida."""
    if not DATABASE_NAME.match(expected_database):
        return signal(Status.INCONCLUSIVE, "expected_database_invalid"), None
    limit = _hours(max_age)
    try:
        state = read_copies(copies, expected_database, now)
    except FileNotFoundError:
        return signal(Status.FAIL, "copy_missing", generations=0, max_age_hours=limit), None
    except NotADirectoryError:
        return signal(Status.FAIL, "copies_layout_invalid", max_age_hours=limit), None
    except PermissionError:
        return signal(Status.INCONCLUSIVE, "copies_unreadable", max_age_hours=limit), None
    facts: dict[str, Any] = {
        "generations": len(state.generations.stamps),
        "ignored_entries": state.generations.ignored,
        "invalid_newer": state.invalid_newer,
        "max_age_hours": limit,
    }
    if state.latest is not None:
        latest = state.latest
        facts["latest"] = {"stamp": latest.stamp, "state": latest.state, "reason": latest.reason}
    valid = state.last_valid
    if valid is None or valid.recovery_point is None:
        reason = "copy_no_valid" if state.generations.stamps else "copy_missing"
        return signal(Status.FAIL, reason, **facts), None
    age = now - valid.recovery_point
    evidence = {
        "stamp": valid.stamp,
        "recovery_point_utc": utc_iso(valid.recovery_point),
        "age_hours": _hours(age),
        "size_bytes": valid.facts.get("size_bytes"),
        "sha256": valid.facts.get("sha256"),
    }
    if state.latest is not valid:
        return signal(Status.FAIL, "copy_latest_invalid", **facts), evidence
    if age > max_age:
        return signal(Status.FAIL, "copy_stale", **facts), evidence
    return signal(Status.OK, "copy_fresh", **facts), evidence


def observe(
    signal_path: Path,
    copies: Path,
    expected_database: str,
    *,
    now: datetime,
    signal_max_age: timedelta,
    copy_max_age: timedelta,
) -> dict[str, Any]:
    """Relatório ``cartorio_system.ops.offsite_observation`` 1.0. Estado geral = o mais
    grave dos três (falha > inconclusivo > ok); motivo = o do primeiro com esse estado,
    na ordem sinal, último check, cópia."""
    app_signal, report = application_signal(signal_path, now, signal_max_age)
    copy_signal, last_valid = offsite_copy(copies, expected_database, now, copy_max_age)
    signals = {
        "application_signal": app_signal,
        "last_check": last_check(report),
        "offsite_copy": copy_signal,
    }
    status = worst(Status(item["status"]) for item in signals.values()) or Status.INCONCLUSIVE
    if status is Status.OK:
        reason = "all_ok"
    else:
        reason = next(
            (item["reason"] for item in signals.values() if item["status"] == status.value),
            "nothing_evaluated",
        )
    return {
        "schema": OBSERVATION_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_iso(now),
        "overall": status.value,
        "reason": reason,
        "exit_code": EXIT_CODES[status],
        "signals": signals,
        "last_valid_copy": last_valid,
    }


def _threshold(unit: str) -> Callable[[str], float]:
    """Limiar positivo e finito que caiba num ``timedelta``: ``nan``, ``inf`` e valores
    enormes passavam no ``> 0`` e só quebravam depois, na conversão."""

    def parse(text: str) -> float:
        value = float(text)
        if not math.isfinite(value) or value <= 0:
            raise argparse.ArgumentTypeError("precisa ser um número finito maior que zero")
        try:
            timedelta(**{unit: value})
        except OverflowError:
            raise argparse.ArgumentTypeError("grande demais para um limite de idade") from None
        return value

    parse.__name__ = "limiar"  # é o nome que o argparse mostra em "invalid ... value"
    return parse


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.ops.observer",
        description=(
            "Observa, de fora da VM, o sinal da aplicação e a cópia externa. Nunca acessa "
            "banco. Saída: 0 ok, 1 falha, 2 inconclusivo."
        ),
    )
    parser.add_argument(
        "--signal",
        type=Path,
        required=True,
        help="último relatório do verificador (cartorio_system.ops.check 1.0)",
    )
    parser.add_argument(
        "--copies", type=Path, required=True, help="raiz das cópias (a de app.ops.offsite)"
    )
    parser.add_argument(
        "--expected-database", required=True, help="banco de que a cópia precisa ser"
    )
    parser.add_argument(
        "--signal-max-age-minutes",
        type=_threshold("minutes"),
        default=LAB_SIGNAL_MAX_AGE_MINUTES,
        help=f"limite de idade do sinal (laboratório: {LAB_SIGNAL_MAX_AGE_MINUTES:g})",
    )
    parser.add_argument(
        "--copy-max-age-hours",
        type=_threshold("hours"),
        default=LAB_COPY_MAX_AGE_HOURS,
        help=f"limite de idade da cópia (laboratório: {LAB_COPY_MAX_AGE_HOURS:g})",
    )
    return parser


def main(argv: Sequence[str] | None = None, *, clock: Clock = utc_now) -> int:
    args = _parser().parse_args(argv)
    result = observe(
        args.signal,
        args.copies,
        args.expected_database,
        now=clock(),
        signal_max_age=timedelta(minutes=args.signal_max_age_minutes),
        copy_max_age=timedelta(hours=args.copy_max_age_hours),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
