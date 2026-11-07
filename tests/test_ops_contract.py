"""Contrato da saída do verificador: envelope versionado, precedência e códigos de saída."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.ops.config import CHECK_NAMES, load_config
from app.ops.report import (
    EXIT_CODES,
    SCHEMA,
    SCHEMA_VERSION,
    CheckResult,
    Status,
    build_report,
    internal_error_report,
    overall,
    signal,
    write_json_atomic,
)
from app.ops.verifier import run_checks
from tests.ops_support import NOW, fixed_clock


def _check(name: str, status: Status, reason: str = "r") -> CheckResult:
    return CheckResult(name, status, reason)


def test_exit_codes_are_distinct_and_documented() -> None:
    assert EXIT_CODES == {Status.OK: 0, Status.FAIL: 1, Status.INCONCLUSIVE: 2}


@pytest.mark.parametrize(
    ("statuses", "expected", "reason"),
    [
        ([Status.OK, Status.OK], Status.OK, "all_checks_ok"),
        ([Status.OK, Status.INCONCLUSIVE], Status.INCONCLUSIVE, "check_inconclusive"),
        ([Status.INCONCLUSIVE, Status.FAIL, Status.OK], Status.FAIL, "check_failed"),
        ([Status.FAIL, Status.SKIPPED], Status.FAIL, "check_failed"),
        ([Status.OK, Status.SKIPPED], Status.OK, "all_checks_ok"),
    ],
)
def test_overall_precedence_fail_beats_inconclusive(statuses, expected, reason) -> None:
    checks = [_check(f"c{i}", s) for i, s in enumerate(statuses)]
    assert overall(checks) == (expected, reason)


def test_nothing_executed_is_never_healthy() -> None:
    checks = [_check(name, Status.SKIPPED, "not_selected") for name in CHECK_NAMES]
    assert overall(checks) == (Status.INCONCLUSIVE, "no_checks_executed")
    assert build_report(checks, NOW)["exit_code"] == 2


def test_reason_is_from_first_signal_with_worst_status() -> None:
    result = CheckResult.from_signals(
        "backup",
        {
            "a": signal(Status.OK, "fine"),
            "b": signal(Status.INCONCLUSIVE, "unknown"),
            "c": signal(Status.FAIL, "first_failure"),
            "d": signal(Status.FAIL, "second_failure"),
            "e": signal(Status.NOT_CONFIGURED, "not_configured"),
        },
        empty_reason="no_signal",
    )
    assert (result.status, result.reason) == (Status.FAIL, "first_failure")


def test_signals_that_do_not_count_cannot_make_a_check_healthy() -> None:
    result = CheckResult.from_signals(
        "api",
        {"units": signal(Status.NOT_CONFIGURED, "not_configured")},
        empty_reason="no_signal",
    )
    assert (result.status, result.reason) == (Status.INCONCLUSIVE, "no_signal")


def test_envelope_has_versioned_schema_and_utc_instant() -> None:
    local = datetime(2026, 11, 7, 9, 0, 0, tzinfo=timezone(timedelta(hours=-3)))
    report = build_report([_check("api", Status.OK, "ok")], local, release={"id": "abc1234"})
    assert report["schema"] == SCHEMA == "cartorio_system.ops.check"
    assert report["schema_version"] == SCHEMA_VERSION == "1.0"
    assert report["generated_at"] == "2026-11-07T12:00:00Z"
    assert report["overall"] == "ok" and report["exit_code"] == 0
    assert set(report) == {
        "schema",
        "schema_version",
        "generated_at",
        "invocation_id",
        "overall",
        "reason",
        "exit_code",
        "release",
        "config_errors",
        "checks",
    }
    check = report["checks"]["api"]
    assert set(check) == {"status", "required", "reason", "duration_ms", "signals"}
    json.dumps(report)  # serializável sem conversor


def test_internal_error_is_inconclusive_and_hides_the_message() -> None:
    report = internal_error_report(NOW, RuntimeError("postgresql://u:segredo@10.0.0.9/db"))
    assert (report["overall"], report["exit_code"]) == ("inconclusive", 2)
    assert report["reason"] == "verifier_internal_error"
    assert "segredo" not in json.dumps(report)
    assert report["error_class"] == "RuntimeError"


def test_atomic_write_leaves_only_the_final_file(tmp_path: Path) -> None:
    target = tmp_path / "sub" / "last-check.json"
    write_json_atomic(target, {"a": 1})
    write_json_atomic(target, {"a": 2})
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 2}
    assert [p.name for p in target.parent.iterdir()] == ["last-check.json"]


# ---------------------------------------------------------------------------
# Configuração explícita por ambiente
# ---------------------------------------------------------------------------


def test_defaults_select_all_checks_and_no_acceptance_threshold() -> None:
    cfg = load_config({})
    assert cfg.checks == CHECK_NAMES
    assert cfg.timeout_seconds == 5.0
    assert cfg.expected_dialect == "postgresql"
    assert cfg.backup_max_age_hours is None  # limiar de aceite nunca é presumido
    assert cfg.problems == {}


@pytest.mark.parametrize("value", ["abc", "0", "-1", "inf", "nan", "61"])
def test_invalid_timeout_makes_every_check_inconclusive(value: str) -> None:
    cfg = load_config({"CARTORIO_OPS_TIMEOUT_SECONDS": value})
    report = run_checks(cfg, clock=fixed_clock())
    assert report["overall"] == "inconclusive"
    assert report["config_errors"] == ["CARTORIO_OPS_TIMEOUT_SECONDS"]
    assert {c["reason"] for c in report["checks"].values()} == {"config_invalid"}


def test_unknown_check_name_is_rejected() -> None:
    cfg = load_config({"CARTORIO_OPS_CHECKS": "api,banco"})
    assert cfg.problems == {"global": ["CARTORIO_OPS_CHECKS"]}


def test_check_selection_skips_the_rest() -> None:
    cfg = load_config({"CARTORIO_OPS_CHECKS": "database"})
    report = run_checks(cfg, clock=fixed_clock())
    statuses = {name: c["status"] for name, c in report["checks"].items()}
    assert statuses == {
        "api": "skipped",
        "database": "inconclusive",
        "alembic": "skipped",
        "backup": "skipped",
    }
    assert report["checks"]["api"]["required"] is False


@pytest.mark.parametrize(
    ("var", "value", "check"),
    [
        ("CARTORIO_OPS_HEALTH_URL", "file:///etc/passwd", "api"),
        ("CARTORIO_OPS_HEALTH_URL", "http://user:senha@127.0.0.1:8000/x", "api"),
        ("CARTORIO_OPS_UNITS", "cartorio.service:timer", "api"),
        ("CARTORIO_OPS_UNITS", "cartorio.service", "api"),
        ("CARTORIO_OPS_BACKUP_DIR", "relativo/backups", "backup"),
        ("CARTORIO_OPS_BACKUP_MAX_AGE_HOURS", "inf", "backup"),
        ("CARTORIO_OPS_BACKUP_TIMER_UNIT", "backup.service", "backup"),
        ("CARTORIO_OPS_RELEASE_DIR", "current", "alembic"),
        ("CARTORIO_OPS_EXPECTED_DIALECT", "mysql", "database"),
    ],
)
def test_invalid_values_are_reported_by_variable_name_only(var, value, check) -> None:
    cfg = load_config({var: value})
    assert var in cfg.problems_for(check)
    report = run_checks(cfg, clock=fixed_clock())
    assert report["checks"][check]["reason"] == "config_invalid"
    assert value not in json.dumps(report)


def test_units_are_parsed_with_their_kind() -> None:
    cfg = load_config(
        {"CARTORIO_OPS_UNITS": "app.service:service, job.service:oneshot,job.timer:timer"}
    )
    assert [(u.name, u.kind) for u in cfg.units] == [
        ("app.service", "service"),
        ("job.service", "oneshot"),
        ("job.timer", "timer"),
    ]


def test_an_exception_inside_one_check_does_not_stop_the_others(monkeypatch) -> None:
    import app.ops.verifier as verifier

    def boom(*args, **kwargs):
        raise RuntimeError("falha interna com segredo")

    monkeypatch.setattr(verifier, "check_database", boom)
    cfg = load_config({"DATABASE_URL": "sqlite:////nao/existe.db"})
    report = run_checks(cfg, clock=fixed_clock())
    database = report["checks"]["database"]
    assert (database["status"], database["reason"]) == ("inconclusive", "unexpected_error")
    assert report["checks"]["alembic"]["reason"] == "config_missing"  # seguiu adiante
    assert "segredo" not in json.dumps(report)


def test_release_id_comes_from_sha_named_release_dir(tmp_path: Path) -> None:
    sha = "c49c6579cf97614323cd228f4b0c25825b40c2fe"
    (tmp_path / "releases" / sha).mkdir(parents=True)
    cfg = load_config({"CARTORIO_OPS_RELEASE_DIR": str(tmp_path / "releases" / sha)})
    assert run_checks(cfg, clock=fixed_clock())["release"]["id"] == sha


def test_generated_at_uses_the_injected_clock() -> None:
    report = run_checks(load_config({}), clock=fixed_clock(NOW))
    assert report["generated_at"] == NOW.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
