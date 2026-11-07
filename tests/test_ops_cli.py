"""CLI do verificador e cenários de aceite com a API real (uvicorn) em bancada SQLite.

A variante PostgreSQL dos mesmos cenários está em ``test_ops_postgres.py`` (gate PG).
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import timedelta
from pathlib import Path

import pytest

from app.ops import cli
from app.ops.report import utc_now
from tests.ops_support import (
    FakeSystemd,
    clean_env,
    free_port,
    healthy_systemd,
    migrate_sqlite,
    oneshot_props,
    run_cli,
    running_app,
    timer_props,
    write_publication,
)

APP_NAME = "Cartorio System - bancada ops"
HEAD = "f4a5b6c7d8e9"
OLDER = "e3f4a5b6c7d8"
REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def bench(tmp_path_factory: pytest.TempPathFactory):
    """SQLite migrado até a head + API real apontada para ele."""
    root = tmp_path_factory.mktemp("ops_bench")
    url = migrate_sqlite(root / "bench.db")
    with running_app(url, APP_NAME, root) as health_url:
        yield {"root": root, "db": root / "bench.db", "url": url, "health": health_url}


def _full_env(bench: dict, backup_dir: Path, **extra: str) -> dict[str, str]:
    env = {
        "CARTORIO_OPS_CHECKS": "api,database,alembic,backup",
        "CARTORIO_OPS_HEALTH_URL": bench["health"],
        "CARTORIO_OPS_EXPECTED_APP_NAME": APP_NAME,
        "CARTORIO_OPS_UNITS": "cartorio-lab.service:service,postgresql@18-main.service:service",
        "DATABASE_URL": bench["url"],
        "CARTORIO_OPS_EXPECTED_DIALECT": "sqlite",
        "CARTORIO_OPS_RELEASE_DIR": str(REPO_ROOT),
        "CARTORIO_OPS_BACKUP_DIR": str(backup_dir),
        "CARTORIO_OPS_BACKUP_MAX_AGE_HOURS": "26",
        "CARTORIO_OPS_BACKUP_SERVICE_UNIT": "cartorio-lab-backup.service",
        "CARTORIO_OPS_BACKUP_TIMER_UNIT": "cartorio-lab-backup.timer",
    }
    env.update(extra)
    return env


def _main(capsys, env: dict[str, str], runner=None, *args: str) -> tuple[int, dict]:
    code = cli.main(["check", *args], environ=env, runner=runner or healthy_systemd())
    return code, json.loads(capsys.readouterr().out)


# ---------------------------------------------------------------------------
# Cenários de aceite (bancada SQLite, HTTP real)
# ---------------------------------------------------------------------------


def test_healthy_and_complete_configuration_returns_zero(bench, tmp_path, capsys) -> None:
    write_publication(tmp_path / "b", utc_now() - timedelta(hours=2))
    code, report = _main(capsys, _full_env(bench, tmp_path / "b"))
    assert code == 0, json.dumps(report, indent=2)
    assert report["overall"] == "ok" and report["exit_code"] == 0
    assert {c["status"] for c in report["checks"].values()} == {"ok"}
    health = report["checks"]["api"]["signals"]["health"]
    assert (health["status_code"], health["reason"]) == (200, "healthy")
    assert report["checks"]["alembic"]["signals"]["revision"]["db_revisions"] == [HEAD]


def test_api_healthy_but_database_failing_exits_nonzero(bench, tmp_path, capsys) -> None:
    missing_db = tmp_path / "nao-existe.db"
    env = _full_env(
        bench,
        tmp_path,
        CARTORIO_OPS_CHECKS="api,database",
        DATABASE_URL=f"sqlite:///{missing_db.as_posix()}",
    )
    code, report = _main(capsys, env)
    assert code == 1
    assert report["checks"]["api"]["status"] == "ok"
    database = report["checks"]["database"]
    assert (database["status"], database["reason"]) == ("fail", "database_missing")
    assert not missing_db.exists(), "verificador somente leitura criou o arquivo do banco"


def test_alembic_divergence_is_reported_without_applying_migrations(
    bench, tmp_path, capsys
) -> None:
    copy = tmp_path / "divergente.db"
    shutil.copyfile(bench["db"], copy)
    with sqlite3.connect(copy) as conn:
        conn.execute("UPDATE alembic_version SET version_num = ?", (OLDER,))
    env = _full_env(
        bench, tmp_path, CARTORIO_OPS_CHECKS="alembic", DATABASE_URL=f"sqlite:///{copy.as_posix()}"
    )
    code, report = _main(capsys, env)
    revision = report["checks"]["alembic"]["signals"]["revision"]
    assert code == 1
    assert (revision["status"], revision["reason"]) == ("fail", "revision_behind")
    assert (revision["db_revisions"], revision["expected_heads"]) == ([OLDER], [HEAD])
    with sqlite3.connect(copy) as conn:
        assert conn.execute("SELECT version_num FROM alembic_version").fetchall() == [(OLDER,)]


def test_unknown_revision_means_database_ahead_of_release(bench, tmp_path, capsys) -> None:
    copy = tmp_path / "adiante.db"
    shutil.copyfile(bench["db"], copy)
    with sqlite3.connect(copy) as conn:
        conn.execute("UPDATE alembic_version SET version_num = 'aaaaaaaaaaaa'")
    env = _full_env(
        bench, tmp_path, CARTORIO_OPS_CHECKS="alembic", DATABASE_URL=f"sqlite:///{copy.as_posix()}"
    )
    _, report = _main(capsys, env)
    assert report["checks"]["alembic"]["reason"] == "revision_unknown"


def test_database_without_version_table_is_lack_of_evidence(bench, tmp_path, capsys) -> None:
    empty = tmp_path / "vazio.db"
    sqlite3.connect(empty).close()
    env = _full_env(
        bench, tmp_path, CARTORIO_OPS_CHECKS="alembic", DATABASE_URL=f"sqlite:///{empty.as_posix()}"
    )
    code, report = _main(capsys, env)
    assert code == 2
    assert report["checks"]["alembic"]["reason"] == "version_table_missing"


def test_wrong_instance_answering_health_is_detected(bench, tmp_path, capsys) -> None:
    env = _full_env(
        bench, tmp_path, CARTORIO_OPS_CHECKS="api", CARTORIO_OPS_EXPECTED_APP_NAME="Outra"
    )
    _, report = _main(capsys, env)
    assert report["checks"]["api"]["reason"] == "app_mismatch"


def test_api_down_is_unreachable(bench, tmp_path, capsys) -> None:
    env = _full_env(
        bench,
        tmp_path,
        CARTORIO_OPS_CHECKS="api",
        CARTORIO_OPS_HEALTH_URL=f"http://127.0.0.1:{free_port()}/api/v1/health",
    )
    code, report = _main(capsys, env)
    assert code == 1
    assert report["checks"]["api"]["reason"] == "unreachable"


def test_dialect_mismatch_is_a_failure(bench, tmp_path, capsys) -> None:
    env = _full_env(
        bench, tmp_path, CARTORIO_OPS_CHECKS="database", CARTORIO_OPS_EXPECTED_DIALECT="postgresql"
    )
    code, report = _main(capsys, env)
    signal = report["checks"]["database"]["signals"]["connection"]
    assert code == 1
    assert (signal["reason"], signal["observed"]) == ("dialect_mismatch", "sqlite")


def test_failure_and_inconclusive_in_the_same_run_exit_as_failure(bench, tmp_path, capsys) -> None:
    env = _full_env(bench, tmp_path / "vazio", CARTORIO_OPS_CHECKS="api,backup")
    (tmp_path / "vazio").mkdir()
    runner = FakeSystemd(error="systemd_unavailable")  # api: inconclusivo
    code, report = _main(capsys, env, runner)
    assert report["checks"]["api"]["status"] == "inconclusive"
    assert report["checks"]["backup"]["reason"] == "backup_missing"
    assert (code, report["overall"]) == (1, "fail")


def test_stale_backup_triggers_the_local_test_alert(bench, tmp_path, capsys) -> None:
    write_publication(tmp_path / "b", utc_now() - timedelta(hours=40))
    env = _full_env(bench, tmp_path / "b", CARTORIO_OPS_CHECKS="backup")
    output = tmp_path / "state" / "last-check.json"
    code, report = _main(capsys, env, None, "--output", str(output))
    assert code == 1 and report["checks"]["backup"]["reason"] == "backup_stale"
    assert json.loads(output.read_text(encoding="utf-8")) == report

    spool = tmp_path / "state" / "alerts"
    assert cli.main(["alert", "--report", str(output), "--spool", str(spool)]) == 0
    capsys.readouterr()
    [alert_file] = list(spool.glob("alert-*.json"))
    alert = json.loads(alert_file.read_text(encoding="utf-8"))
    assert alert["schema"] == "cartorio_system.ops.alert"
    assert (alert["level"], alert["reason"]) == ("fail", "check_failed")
    assert alert["problems"] == [{"check": "backup", "status": "fail", "reason": "backup_stale"}]
    assert alert["summary"] == "backup: backup_stale"


def test_failed_backup_attempt_keeps_previous_copy_visible(bench, tmp_path, capsys) -> None:
    write_publication(tmp_path / "b", utc_now() - timedelta(hours=3))
    runner = FakeSystemd(
        {
            "cartorio-lab-backup.service": oneshot_props(
                active="failed", result="exit-code", status="1"
            ),
            "cartorio-lab-backup.timer": timer_props(),
        }
    )
    env = _full_env(bench, tmp_path / "b", CARTORIO_OPS_CHECKS="backup")
    code, report = _main(capsys, env, runner)
    signals = report["checks"]["backup"]["signals"]
    assert code == 1
    assert report["checks"]["backup"]["reason"] == "last_attempt_failed"
    assert signals["last_valid_copy"]["status"] == "ok"
    assert signals["integrity"]["reason"] == "digest_verified"


# ---------------------------------------------------------------------------
# Processo real: códigos de saída, JSON em stdout, sem vazamento
# ---------------------------------------------------------------------------


def test_subprocess_without_configuration_is_inconclusive() -> None:
    result = run_cli("check", "--compact", env=clean_env())
    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert report["schema_version"] == "1.0"
    assert {c["reason"] for c in report["checks"].values()} == {"config_missing"}


def test_subprocess_never_prints_the_dsn(tmp_path) -> None:
    secret = "SenhaQueNaoPodeVazar"
    env = clean_env(
        CARTORIO_OPS_CHECKS="database",
        DATABASE_URL=f"postgresql+nao_existe://u:{secret}@10.255.255.1:5432/db",
    )
    result = run_cli("check", env=env)
    assert result.returncode == 2
    assert secret not in result.stdout + result.stderr
    assert "10.255.255.1" not in result.stdout + result.stderr
    connection = json.loads(result.stdout)["checks"]["database"]["signals"]["connection"]
    assert (connection["reason"], connection["detail"]) == ("config_invalid", "driver_unavailable")


def test_usage_error_is_inconclusive_exit_code() -> None:
    assert run_cli("check", "--nao-existe", env=clean_env()).returncode == 2


# ---------------------------------------------------------------------------
# Alerta
# ---------------------------------------------------------------------------


def test_alert_without_report_still_alerts(tmp_path, capsys) -> None:
    spool = tmp_path / "alerts"
    assert cli.main(["alert", "--report", str(tmp_path / "x.json"), "--spool", str(spool)]) == 0
    capsys.readouterr()
    [alert_file] = list(spool.iterdir())
    alert = json.loads(alert_file.read_text(encoding="utf-8"))
    assert (alert["level"], alert["reason"]) == ("inconclusive", "report_missing")


def test_alert_on_stale_report_says_so(tmp_path, capsys) -> None:
    report = tmp_path / "last.json"
    report.write_text(
        json.dumps(
            {
                "schema": "cartorio_system.ops.check",
                "generated_at": "2026-01-01T00:00:00Z",
                "overall": "ok",
                "checks": {},
            }
        ),
        encoding="utf-8",
    )
    assert cli.main(["alert", "--report", str(report), "--spool", str(tmp_path / "a")]) == 0
    capsys.readouterr()
    [alert_file] = list((tmp_path / "a").iterdir())
    assert json.loads(alert_file.read_text(encoding="utf-8"))["reason"] == "report_stale"


def test_healthy_report_produces_no_alert(bench, tmp_path, capsys) -> None:
    write_publication(tmp_path / "b", utc_now() - timedelta(hours=2))
    output = tmp_path / "last.json"
    code, _ = _main(capsys, _full_env(bench, tmp_path / "b"), None, "--output", str(output))
    assert code == 0
    assert cli.main(["alert", "--report", str(output), "--spool", str(tmp_path / "a")]) == 0
    assert not (tmp_path / "a").exists()


# ---------------------------------------------------------------------------
# Falha com relatório saudável anterior: o alerta acionado por OnFailure= não silencia
# ---------------------------------------------------------------------------

PREVIOUS_RUN = "a" * 32
FAILED_RUN = "b" * 32


def _healthy_report_from_previous_run(bench, tmp_path, capsys) -> Path:
    write_publication(tmp_path / "b", utc_now() - timedelta(hours=2))
    output = tmp_path / "state" / "last-check.json"
    env = _full_env(bench, tmp_path / "b", INVOCATION_ID=PREVIOUS_RUN)
    code, report = _main(capsys, env, None, "--output", str(output))
    assert (code, report["overall"], report["invocation_id"]) == (0, "ok", PREVIOUS_RUN)
    return output


def _alert_after_failure(report: Path, spool: Path, environ: dict, capsys) -> dict:
    args = ["alert", "--expect-failure", "--report", str(report), "--spool", str(spool)]
    assert cli.main(args, environ=environ) == 0
    capsys.readouterr()
    [alert_file] = list(spool.glob("alert-*.json"))
    return json.loads(alert_file.read_text(encoding="utf-8"))


def test_failure_with_previous_healthy_report_still_alerts(bench, tmp_path, capsys) -> None:
    """A execução que falhou não escreveu relatório (venv quebrado, disco cheio, timeout):
    em disco ficou o relatório SAUDÁVEL da anterior. Sem ``MONITOR_*`` (systemd < 251)."""
    report = _healthy_report_from_previous_run(bench, tmp_path, capsys)
    alert = _alert_after_failure(report, tmp_path / "alerts", {}, capsys)
    assert (alert["level"], alert["reason"]) == ("inconclusive", "run_failed_but_report_healthy")
    assert alert["report_overall"] == "ok"
    assert alert["problems"] == []  # nada do relatório antigo vira problema "atual"


def test_failure_report_from_another_run_is_identified(bench, tmp_path, capsys) -> None:
    report = _healthy_report_from_previous_run(bench, tmp_path, capsys)
    monitor = {
        "MONITOR_UNIT": "cartorio-lab-ops-check.service",
        "MONITOR_INVOCATION_ID": FAILED_RUN,
        "MONITOR_SERVICE_RESULT": "exit-code",
        "MONITOR_EXIT_CODE": "exited",
        "MONITOR_EXIT_STATUS": "1",
    }
    alert = _alert_after_failure(report, tmp_path / "alerts", monitor, capsys)
    assert (alert["level"], alert["reason"]) == ("inconclusive", "report_not_from_failed_run")
    assert alert["failed_run"] == {
        "unit": "cartorio-lab-ops-check.service",
        "invocation_id": FAILED_RUN,
        "service_result": "exit-code",
        "exit_code": "exited",
        "exit_status": "1",
    }


def test_failure_report_from_the_failed_run_lists_its_problems(bench, tmp_path, capsys) -> None:
    write_publication(tmp_path / "b", utc_now() - timedelta(hours=40))
    output = tmp_path / "state" / "last-check.json"
    env = _full_env(bench, tmp_path / "b", CARTORIO_OPS_CHECKS="backup", INVOCATION_ID=FAILED_RUN)
    code, _ = _main(capsys, env, None, "--output", str(output))
    assert code == 1
    alert = _alert_after_failure(
        output, tmp_path / "alerts", {"MONITOR_INVOCATION_ID": FAILED_RUN}, capsys
    )
    assert (alert["level"], alert["reason"]) == ("fail", "check_failed")
    assert alert["problems"] == [{"check": "backup", "status": "fail", "reason": "backup_stale"}]


def test_invocation_id_is_recorded_only_when_well_formed(bench, tmp_path, capsys) -> None:
    env = _full_env(bench, tmp_path, CARTORIO_OPS_CHECKS="api", INVOCATION_ID="nao-e-hex")
    _, report = _main(capsys, env)
    assert report["invocation_id"] is None


# ---------------------------------------------------------------------------
# Achado 4 do PR #6: o JSON de stdout concorda com o código real do processo
# ---------------------------------------------------------------------------


def _backup_only_env(tmp_path: Path, scenario: str) -> dict[str, str]:
    """Só a checagem de backup: saudável, falha (cópia vencida) ou inconclusiva."""
    backups = tmp_path / "b"
    if scenario == "healthy":
        write_publication(backups, utc_now() - timedelta(hours=1))
    elif scenario == "failing":
        write_publication(backups, utc_now() - timedelta(hours=40))
    env = {
        "CARTORIO_OPS_CHECKS": "backup",
        "CARTORIO_OPS_BACKUP_MAX_AGE_HOURS": "26",
        "CARTORIO_OPS_BACKUP_EXPECTED_DATABASE": "cartorio_lab",
    }
    if scenario != "inconclusive":
        env["CARTORIO_OPS_BACKUP_DIR"] = str(backups)
    return clean_env(**env)


@pytest.mark.parametrize(
    ("scenario", "exit_code", "overall", "reason"),
    [
        ("healthy", 2, "inconclusive", "output_not_published"),
        ("failing", 1, "fail", "check_failed"),
        ("inconclusive", 2, "inconclusive", "check_inconclusive"),
    ],
)
def test_unpublished_output_keeps_stdout_and_exit_code_in_agreement(
    tmp_path: Path, scenario: str, exit_code: int, overall: str, reason: str
) -> None:
    blocker = tmp_path / "arquivo-no-lugar-do-diretorio"
    blocker.write_text("x", encoding="utf-8")
    result = run_cli(
        "check",
        "--compact",
        "--output",
        str(blocker / "last-check.json"),
        env=_backup_only_env(tmp_path, scenario),
    )
    report = json.loads(result.stdout)
    assert result.returncode == exit_code == report["exit_code"]
    assert (report["overall"], report["reason"]) == (overall, reason)
    assert report["output"]["published"] is False
    assert report["output"]["reason"] == "output_not_published"
    assert str(tmp_path) not in result.stdout  # caminho do arquivo não vaza no JSON


@pytest.mark.parametrize(
    ("scenario", "exit_code"), [("healthy", 0), ("failing", 1), ("inconclusive", 2)]
)
def test_published_output_equals_stdout_and_exit_code(
    tmp_path: Path, scenario: str, exit_code: int
) -> None:
    output = tmp_path / "estado" / "last-check.json"
    result = run_cli(
        "check", "--compact", "--output", str(output), env=_backup_only_env(tmp_path, scenario)
    )
    report = json.loads(result.stdout)
    assert json.loads(output.read_text(encoding="utf-8")) == report
    assert result.returncode == exit_code == report["exit_code"]
    assert report["output"] == {"requested": True, "published": True}


def test_without_output_the_envelope_says_so(tmp_path: Path) -> None:
    result = run_cli("check", "--compact", env=_backup_only_env(tmp_path, "healthy"))
    report = json.loads(result.stdout)
    assert (result.returncode, report["exit_code"]) == (0, 0)
    assert report["output"] == {"requested": False}
