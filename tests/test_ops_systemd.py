"""Leitura de unidades systemd com exemplos sintéticos de ``systemctl show``."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.ops.config import UnitSpec
from app.ops.systemd import (
    SystemctlError,
    evaluate_unit,
    parse_show,
    parse_unix_timestamp,
    probe_unit,
    run_systemctl_show,
)
from tests.ops_support import FakeSystemd, oneshot_props, service_props, timer_props


def test_parse_show_keeps_values_with_equals_sign() -> None:
    props = parse_show("Id=a.service\nActiveState=active\nEnvironment=A=1\n\n")
    assert props == {"Id": "a.service", "ActiveState": "active", "Environment": "A=1"}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("@1767225600", datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)),
        ("@1767225600.123456", datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)),
        ("", None),
        ("n/a", None),
        ("@0", None),
        ("Thu 2026-01-01 00:00:00 UTC", None),
    ],
)
def test_unix_timestamps(raw: str, expected: datetime | None) -> None:
    assert parse_unix_timestamp(raw) == expected


def test_persistent_service_running_and_enabled_is_ok() -> None:
    result = evaluate_unit("service", service_props())
    assert (result["status"], result["reason"]) == ("ok", "running")


@pytest.mark.parametrize(
    ("props", "reason"),
    [
        (service_props(active="inactive", sub="dead"), "unit_not_running"),
        (service_props(active="failed", sub="failed"), "unit_not_running"),
        (service_props(active="activating", sub="auto-restart"), "unit_not_running"),
        # guarda-chuva postgresql.service: active/exited mesmo com o cluster parado
        (service_props(active="active", sub="exited"), "unit_not_running"),
        (service_props(file_state="disabled"), "unit_not_enabled"),
        ({"LoadState": "not-found", "ActiveState": "inactive"}, "unit_not_found"),
        ({"LoadState": "masked", "ActiveState": "inactive"}, "unit_not_loaded"),
    ],
)
def test_persistent_service_failures(props: dict, reason: str) -> None:
    result = evaluate_unit("service", props)
    assert (result["status"], result["reason"]) == ("fail", reason)


def test_oneshot_inactive_after_success_is_the_expected_state() -> None:
    result = evaluate_unit("oneshot", oneshot_props())
    assert (result["status"], result["reason"]) == ("ok", "last_run_succeeded")
    assert result["started_utc"] == "2026-11-07T12:00:00Z"


def test_oneshot_without_run_since_boot_is_not_a_failure() -> None:
    result = evaluate_unit("oneshot", oneshot_props(started=None))
    assert (result["status"], result["reason"]) == ("ok", "no_run_since_boot")


def test_oneshot_running_now() -> None:
    result = evaluate_unit("oneshot", oneshot_props(active="activating"))
    assert (result["status"], result["reason"]) == ("ok", "running_now")


def test_oneshot_failed_reports_result_and_exit_status() -> None:
    result = evaluate_unit(
        "oneshot", oneshot_props(active="failed", result="exit-code", status="1")
    )
    assert (result["status"], result["reason"]) == ("fail", "last_run_failed")
    assert (result["result"], result["exit_status"]) == ("exit-code", 1)


def test_the_same_inactive_state_fails_a_persistent_service() -> None:
    props = oneshot_props()
    assert evaluate_unit("oneshot", props)["status"] == "ok"
    assert evaluate_unit("service", props)["status"] == "fail"


def test_timer_active_reports_last_and_next_trigger() -> None:
    result = evaluate_unit("timer", timer_props())
    assert (result["status"], result["reason"]) == ("ok", "timer_active")
    assert result["last_trigger_utc"] == "2026-11-07T05:00:00Z"
    assert result["next_elapse_utc"] == "2026-11-08T05:00:00Z"


@pytest.mark.parametrize(
    ("props", "reason"),
    [
        (timer_props(active="inactive"), "timer_inactive"),
        (timer_props(file_state="disabled"), "timer_not_enabled"),
    ],
)
def test_timer_failures(props: dict, reason: str) -> None:
    assert evaluate_unit("timer", props)["reason"] == reason


@pytest.mark.parametrize("error", ["systemd_unavailable", "systemctl_timeout", "systemctl_failed"])
def test_unreachable_systemd_is_inconclusive(error: str) -> None:
    result = probe_unit(
        UnitSpec("a.service", "service"),
        systemctl="systemctl",
        timeout=1,
        runner=FakeSystemd(error=error),
    )
    assert (result["status"], result["reason"]) == ("inconclusive", error)


def test_missing_systemctl_binary_is_systemd_unavailable(tmp_path) -> None:
    with pytest.raises(SystemctlError) as info:
        run_systemctl_show(str(tmp_path / "nao-existe-systemctl"), "a.service", 2)
    assert info.value.reason == "systemd_unavailable"
