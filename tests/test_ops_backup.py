"""Evidência de backup com relógio controlado e cópias sintéticas no formato da rotina.

Cobre os cenários de aceite: cópia vencida com artefato presente; cópia ausente,
incompleta, corrompida ou sem evidência verificável; última tentativa falhou com a
cópia anterior válida; referências fora do diretório; publicação parcial.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import timedelta
from pathlib import Path

import pytest

from app.ops.backup import PARTIAL_GRACE, check_backup, evaluate_publication
from app.ops.config import load_config
from tests.ops_support import (
    NOW,
    REMOVE,
    FakeSystemd,
    oneshot_props,
    stamp_of,
    timer_props,
    write_publication,
)

MAX_AGE = 26


def _cfg(directory: Path, **extra: str):
    env = {
        "CARTORIO_OPS_BACKUP_DIR": str(directory),
        "CARTORIO_OPS_BACKUP_MAX_AGE_HOURS": str(MAX_AGE),
        "CARTORIO_OPS_BACKUP_EXPECTED_DATABASE": "cartorio_lab",
        **extra,
    }
    return load_config(env)


def _run(directory: Path, runner: FakeSystemd | None = None, **extra: str):
    return check_backup(_cfg(directory, **extra), now=NOW, runner=runner or FakeSystemd())


def _sig(result, name: str) -> tuple[str, str]:
    return result.signals[name]["status"], result.signals[name]["reason"]


def test_recent_complete_and_intact_copy_is_ok(tmp_path: Path) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=7))
    result = _run(tmp_path)
    assert (result.status.value, result.reason) == ("ok", "complete")
    assert _sig(result, "integrity") == ("ok", "digest_verified")
    assert _sig(result, "age") == ("ok", "within_max_age")
    assert result.signals["age"]["age_hours"] == 7.0
    assert result.signals["last_copy"]["recovery_point_utc"] == "2026-11-07T05:00:00Z"
    assert _sig(result, "last_attempt") == ("not_configured", "not_configured")


def test_stale_copy_with_artifact_present_reports_delay(tmp_path: Path) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=30))
    result = _run(tmp_path)
    assert (result.status.value, result.reason) == ("fail", "backup_stale")
    assert result.signals["age"]["age_hours"] == 30.0
    assert result.signals["age"]["max_age_hours"] == MAX_AGE
    assert _sig(result, "integrity") == ("ok", "digest_verified")  # íntegra, só velha


def test_age_exactly_at_the_limit_is_still_fresh(tmp_path: Path) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=MAX_AGE))
    assert _run(tmp_path).status.value == "ok"


def test_age_uses_the_recovery_point_never_the_file_mtime(tmp_path: Path) -> None:
    # Arquivo "tocado" agora, mas o ponto de recuperação é antigo: continua vencido.
    write_publication(tmp_path, NOW - timedelta(hours=40), file_mtime=NOW)
    assert _run(tmp_path).reason == "backup_stale"


def test_empty_directory_is_missing_copy(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert (result.status.value, result.reason) == ("fail", "backup_missing")


def test_missing_directory_is_inconclusive(tmp_path: Path) -> None:
    result = _run(tmp_path / "nao-existe")
    assert (result.status.value, result.reason) == ("inconclusive", "backup_dir_unavailable")


def test_incomplete_copy_size_mismatch(tmp_path: Path) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=1), overrides={"tamanho_bytes": 999_999})
    result = _run(tmp_path)
    assert (result.status.value, result.reason) == ("fail", "size_mismatch")
    assert _sig(result, "last_valid_copy") == ("fail", "no_valid_copy")


def test_corrupted_copy_digest_mismatch_and_older_valid_copy_still_visible(
    tmp_path: Path,
) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=25))
    dump, _ = write_publication(tmp_path, NOW - timedelta(hours=1))
    dump.write_bytes(dump.read_bytes()[:-1] + b"X")  # mesmo tamanho, outro conteúdo
    result = _run(tmp_path)
    assert (result.status.value, result.reason) == ("fail", "digest_mismatch")
    assert _sig(result, "last_valid_copy") == ("ok", "available")
    assert result.signals["last_valid_copy"]["age_hours"] == 25.0
    assert _sig(result, "age") == ("ok", "within_max_age")


def test_manifest_without_digest_has_no_verifiable_evidence(tmp_path: Path) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=1), overrides={"sha256": REMOVE})
    result = _run(tmp_path)
    assert (result.status.value, result.reason) == ("fail", "manifest_incomplete")


def test_dump_without_manifest_after_grace_is_not_verifiable(tmp_path: Path) -> None:
    write_publication(
        tmp_path, NOW - timedelta(hours=2), manifest=False, file_mtime=NOW - timedelta(hours=2)
    )
    result = _run(tmp_path)
    assert (result.status.value, result.reason) == ("fail", "no_verifiable_copy")
    partial = result.signals["publications"]["partial"]
    assert partial == [
        {
            "file": f"backup-{stamp_of(NOW - timedelta(hours=2))}.dump",
            "reason": "manifest_missing",
            "pending": False,
        }
    ]


def test_publication_in_progress_is_unavailable_not_a_failure(tmp_path: Path) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=20))
    # Dump já renomeado, manifesto ainda não escrito, dentro da carência.
    write_publication(tmp_path, NOW - timedelta(minutes=3), manifest=False, file_mtime=NOW)
    result = _run(tmp_path)
    assert result.status.value == "ok"
    assert result.signals["last_copy"]["recovery_point_utc"] == "2026-11-06T16:00:00Z"
    assert result.signals["publications"]["partial"][0]["pending"] is True


def test_stale_partial_newer_than_last_copy_fails_even_with_fresh_previous(
    tmp_path: Path,
) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=20))
    late = NOW - PARTIAL_GRACE - timedelta(minutes=1)
    write_publication(tmp_path, NOW - timedelta(hours=1), manifest=False, file_mtime=late)
    result = _run(tmp_path)
    assert (result.status.value, result.reason) == ("fail", "unverifiable_copy")
    assert _sig(result, "last_copy") == ("ok", "complete")
    assert _sig(result, "age") == ("ok", "within_max_age")


def test_truncated_manifest_is_partial_and_previous_copy_is_used(tmp_path: Path) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=10))
    _, manifest = write_publication(tmp_path, NOW - timedelta(minutes=1))
    manifest.write_text('{"arquivo": "backup-', encoding="utf-8")  # escrita interrompida
    os.utime(manifest, (NOW.timestamp(), NOW.timestamp()))
    result = _run(tmp_path)
    assert result.status.value == "ok"
    assert result.signals["publications"]["partial"][0]["reason"] == "manifest_unparseable"


@pytest.mark.parametrize(
    "reference",
    ["../fora.dump", "/etc/fora.dump", "sub/backup.dump", "..\\fora.dump", ".."],
)
def test_reference_outside_configured_directory_is_rejected(tmp_path: Path, reference: str) -> None:
    backups = tmp_path / "recorrentes"
    write_publication(backups, NOW - timedelta(hours=1), overrides={"arquivo": reference})
    (tmp_path / "fora.dump").write_bytes(b"fora")
    result = _run(backups)
    assert (result.status.value, result.reason) == ("fail", "reference_outside_dir")


@pytest.mark.skipif(sys.platform == "win32", reason="link simbólico exige privilégio no Windows")
def test_symlinked_artifact_is_rejected(tmp_path: Path) -> None:
    backups = tmp_path / "recorrentes"
    dump, _ = write_publication(backups, NOW - timedelta(hours=1))
    outside = tmp_path / "fora.dump"
    outside.write_bytes(dump.read_bytes())
    dump.unlink()
    dump.symlink_to(outside)
    assert _run(backups).reason == "reference_outside_dir"


def test_future_recovery_point_is_invalid_evidence(tmp_path: Path) -> None:
    write_publication(tmp_path, NOW + timedelta(hours=2))
    result = _run(tmp_path)
    assert (result.status.value, result.reason) == ("fail", "recovery_point_in_future")


def test_small_clock_skew_is_tolerated(tmp_path: Path) -> None:
    write_publication(tmp_path, NOW + timedelta(minutes=2))
    assert _run(tmp_path).status.value == "ok"


def test_unreadable_recovery_point_is_invalid_evidence(tmp_path: Path) -> None:
    stamp = "20261399T999999Z"  # casa com o padrão, mas não é data
    (tmp_path / f"backup-{stamp}.dump").write_bytes(b"x")
    (tmp_path / f"backup-{stamp}.json").write_text(
        json.dumps(
            {
                "arquivo": f"backup-{stamp}.dump",
                "sha256": "0" * 64,
                "tamanho_bytes": 1,
                "gerado_em_utc": stamp,
                "database": "cartorio_lab",
            }
        ),
        encoding="utf-8",
    )
    assert _run(tmp_path).reason == "recovery_point_unreadable"


def test_manifest_pointing_to_another_copy_is_inconsistent(tmp_path: Path) -> None:
    older, _ = write_publication(tmp_path / "x", NOW - timedelta(hours=5))
    write_publication(tmp_path, NOW - timedelta(hours=1), overrides={"arquivo": older.name})
    (tmp_path / older.name).write_bytes(older.read_bytes())
    assert _run(tmp_path).reason == "manifest_inconsistent"


def test_failed_attempt_and_previous_valid_copy_appear_together(tmp_path: Path) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=7))
    runner = FakeSystemd(
        {
            "lab-backup.service": oneshot_props(active="failed", result="exit-code", status="1"),
            "lab-backup.timer": timer_props(),
        }
    )
    result = _run(
        tmp_path,
        runner,
        CARTORIO_OPS_BACKUP_SERVICE_UNIT="lab-backup.service",
        CARTORIO_OPS_BACKUP_TIMER_UNIT="lab-backup.timer",
    )
    assert (result.status.value, result.reason) == ("fail", "last_attempt_failed")
    assert _sig(result, "last_copy") == ("ok", "complete")
    assert _sig(result, "integrity") == ("ok", "digest_verified")
    assert _sig(result, "age") == ("ok", "within_max_age")
    assert result.signals["last_attempt"]["exit_status"] == 1
    assert _sig(result, "timer") == ("ok", "timer_active")


def test_inactive_backup_timer_fails(tmp_path: Path) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=7))
    runner = FakeSystemd({"lab-backup.timer": timer_props(active="inactive")})
    result = _run(tmp_path, runner, CARTORIO_OPS_BACKUP_TIMER_UNIT="lab-backup.timer")
    assert (result.status.value, result.reason) == ("fail", "timer_inactive")


def test_no_attempt_since_boot_is_informative_only(tmp_path: Path) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=7))
    runner = FakeSystemd({"lab-backup.service": oneshot_props(started=None)})
    result = _run(tmp_path, runner, CARTORIO_OPS_BACKUP_SERVICE_UNIT="lab-backup.service")
    assert result.status.value == "ok"
    assert _sig(result, "last_attempt") == ("ok", "no_run_since_boot")


def test_unreachable_systemd_with_good_copy_is_inconclusive(tmp_path: Path) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=7))
    result = _run(
        tmp_path,
        FakeSystemd(error="systemd_unavailable"),
        CARTORIO_OPS_BACKUP_TIMER_UNIT="lab-backup.timer",
    )
    assert (result.status.value, result.reason) == ("inconclusive", "systemd_unavailable")


def test_staging_leftovers_are_counted(tmp_path: Path) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=1))
    (tmp_path / ".tmp").mkdir()
    (tmp_path / ".tmp" / "staging-x.dump").write_bytes(b"x")
    assert _run(tmp_path).signals["publications"]["staging_files"] == 1


def _drill_evidence(path: Path, *, verdict: str, finished: str, sha: str | None) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema": "cartorio_system.ops.restore_drill",
                "verdict": verdict,
                "finished_at": finished,
                "mode": "synthetic",
                "classification": "bench_measurement",
                "artifact": {"sha256": sha},
            }
        ),
        encoding="utf-8",
    )
    return path


def test_restore_test_is_a_separate_signal(tmp_path: Path) -> None:
    dump, _ = write_publication(tmp_path / "b", NOW - timedelta(hours=1))
    import hashlib

    sha = hashlib.sha256(dump.read_bytes()).hexdigest()
    evidence = _drill_evidence(
        tmp_path / "drill.json", verdict="passed", finished="2026-11-01T12:00:00Z", sha=sha
    )
    result = _run(tmp_path / "b", CARTORIO_OPS_RESTORE_EVIDENCE=str(evidence))
    assert _sig(result, "restore_test") == ("ok", "restore_verified")
    assert result.signals["restore_test"]["age_days"] == 6.0
    assert result.signals["restore_test"]["same_artifact_as_last_copy"] is True


@pytest.mark.parametrize(
    ("verdict", "finished", "max_days", "expected"),
    [
        ("failed", "2026-11-06T12:00:00Z", None, ("fail", "restore_test_failed")),
        ("passed", "2026-08-01T12:00:00Z", "35", ("fail", "restore_test_stale")),
        ("passed", "2027-01-01T00:00:00Z", None, ("inconclusive", "restore_evidence_invalid")),
    ],
)
def test_restore_test_failures(tmp_path: Path, verdict, finished, max_days, expected) -> None:
    write_publication(tmp_path / "b", NOW - timedelta(hours=1))
    evidence = _drill_evidence(tmp_path / "d.json", verdict=verdict, finished=finished, sha=None)
    extra = {"CARTORIO_OPS_RESTORE_EVIDENCE": str(evidence)}
    if max_days:
        extra["CARTORIO_OPS_RESTORE_MAX_AGE_DAYS"] = max_days
    assert _sig(_run(tmp_path / "b", **extra), "restore_test") == expected


def test_missing_restore_evidence_is_inconclusive(tmp_path: Path) -> None:
    write_publication(tmp_path / "b", NOW - timedelta(hours=1))
    result = _run(tmp_path / "b", CARTORIO_OPS_RESTORE_EVIDENCE=str(tmp_path / "nada.json"))
    assert _sig(result, "restore_test") == ("inconclusive", "restore_evidence_missing")


def test_missing_threshold_is_config_missing_not_a_default(tmp_path: Path) -> None:
    cfg = load_config({"CARTORIO_OPS_BACKUP_DIR": str(tmp_path)})
    result = check_backup(cfg, now=NOW, runner=FakeSystemd())
    assert (result.status.value, result.reason) == ("inconclusive", "config_missing")


def test_evaluate_publication_reads_the_real_routine_format(tmp_path: Path) -> None:
    # Mesmo formato publicado pela rotina de homologação (valores sintéticos).
    write_publication(tmp_path, NOW - timedelta(hours=1))
    evaluation = evaluate_publication(
        tmp_path, stamp_of(NOW - timedelta(hours=1)), NOW, "cartorio_lab"
    )
    assert (evaluation.state, evaluation.reason) == ("valid", "digest_verified")


# ---------------------------------------------------------------------------
# Achado 2 do PR #6: o manifesto precisa ser do banco esperado
# ---------------------------------------------------------------------------

FOREIGN = "outro_banco_ficticio"
LAB_DSN = "postgresql+psycopg://lab:senha@127.0.0.1:5432/cartorio_lab"


def _check_with(directory: Path, env: dict[str, str]):
    base = {
        "CARTORIO_OPS_BACKUP_DIR": str(directory),
        "CARTORIO_OPS_BACKUP_MAX_AGE_HOURS": str(MAX_AGE),
    }
    return check_backup(load_config({**base, **env}), now=NOW, runner=FakeSystemd())


def test_fresh_intact_copy_of_another_database_is_rejected_without_names(
    tmp_path: Path,
) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=1), overrides={"database": FOREIGN})
    result = _run(tmp_path)
    assert (result.status.value, result.reason) == ("fail", "database_mismatch")
    assert _sig(result, "last_valid_copy") == ("fail", "no_valid_copy")
    serialized = json.dumps(result.as_dict())
    assert FOREIGN not in serialized and "cartorio_lab" not in serialized


def test_older_correct_copy_stays_the_last_valid_point(tmp_path: Path) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=5))
    write_publication(tmp_path, NOW - timedelta(hours=1), overrides={"database": FOREIGN})
    result = _run(tmp_path)
    assert (result.status.value, result.reason) == ("fail", "database_mismatch")
    assert _sig(result, "last_copy") == ("fail", "database_mismatch")
    assert _sig(result, "last_valid_copy") == ("ok", "available")
    assert result.signals["last_valid_copy"]["age_hours"] == 5.0
    assert _sig(result, "age") == ("ok", "within_max_age")


def test_expected_database_comes_from_an_unambiguous_dsn(tmp_path: Path) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=1))
    assert _check_with(tmp_path, {"DATABASE_URL": LAB_DSN}).status.value == "ok"


@pytest.mark.parametrize(
    "dsn",
    [
        LAB_DSN + "?dbname=outro",
        LAB_DSN + "?service=perfil",
        LAB_DSN + "?dbname=",
        "postgresql+psycopg://lab:senha@127.0.0.1:5432/",
        "sqlite:////srv/bancada.db",
    ],
)
def test_ambiguous_dsn_without_explicit_name_is_inconclusive(tmp_path: Path, dsn: str) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=1))
    result = _check_with(tmp_path, {"DATABASE_URL": dsn})
    assert (result.status.value, result.reason) == ("inconclusive", "expected_database_ambiguous")


def test_explicit_name_decides_when_the_dsn_is_ambiguous(tmp_path: Path) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=1))
    env = {
        "DATABASE_URL": LAB_DSN + "?dbname=outro",
        "CARTORIO_OPS_BACKUP_EXPECTED_DATABASE": "cartorio_lab",
    }
    assert _check_with(tmp_path, env).status.value == "ok"


def test_explicit_name_and_dsn_must_agree(tmp_path: Path) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=1))
    env = {"DATABASE_URL": LAB_DSN, "CARTORIO_OPS_BACKUP_EXPECTED_DATABASE": FOREIGN}
    result = _check_with(tmp_path, env)
    assert (result.status.value, result.reason) == ("inconclusive", "expected_database_conflict")
    assert FOREIGN not in json.dumps(result.as_dict())


def test_missing_expected_database_is_inconclusive(tmp_path: Path) -> None:
    write_publication(tmp_path, NOW - timedelta(hours=1))
    result = _check_with(tmp_path, {})
    assert (result.status.value, result.reason) == ("inconclusive", "expected_database_missing")


@pytest.mark.parametrize("value", ["com espaco", "x" * 64])
def test_invalid_expected_database_is_config_invalid(tmp_path: Path, value: str) -> None:
    result = _check_with(tmp_path, {"CARTORIO_OPS_BACKUP_EXPECTED_DATABASE": value})
    assert (result.status.value, result.reason) == ("inconclusive", "config_invalid")
