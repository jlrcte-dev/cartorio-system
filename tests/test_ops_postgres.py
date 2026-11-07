"""Cenários do verificador contra PostgreSQL — parte do gate PostgreSQL de bancada.

- "API 200 com PostgreSQL indisponível" precisa só do driver (extra ``postgres``): roda
  sempre que ``psycopg`` estiver instalado.
- Os demais precisam de servidor real e reaproveitam, sem alterar, a fixture e as
  proteções da suíte do PR #5 (``tests/test_postgres_compat.py``): identidade exata da
  bancada, recusa de override na URL e em ``PG*``, schema exclusivo por sessão e
  descarte só do que a sessão criou.

No gate (``scripts/ops/pg_gate.py``) nenhum destes pode ser pulado.
"""

from __future__ import annotations

import json
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

from app.ops import cli
from app.ops.checks import ProbeError, read_only_connection
from app.ops.report import utc_now
from tests import test_postgres_compat as pr5
from tests.ops_support import (
    clean_env,
    free_port,
    healthy_systemd,
    run_cli,
    running_app,
    write_publication,
)

# Mesma fixture de sessão do PR #5 (schema exclusivo, migrado, sempre descartado).
postgres_db = pr5.postgres_db

APP_NAME = "Cartorio System - bancada ops PG"
REPO_ROOT = Path(__file__).resolve().parent.parent


def _driver_available() -> bool:
    try:
        import psycopg  # noqa: F401
    except ImportError:
        return False
    return True


_requires_driver = pytest.mark.skipif(
    not _driver_available(), reason="requer o driver PostgreSQL (extra postgres)"
)


@_requires_driver
def test_api_200_with_postgres_unavailable_fails_overall(tmp_path: Path) -> None:
    """HTTP real da aplicação: o /health responde 200 (não toca o banco), mas o
    PostgreSQL configurado está fora do ar — o verificador separa os dois fatos."""
    secret = f"senha-{uuid.uuid4().hex}"
    url = f"postgresql+psycopg://cartorio_app:{secret}@127.0.0.1:{free_port()}/cartorio_lab"
    with running_app(url, APP_NAME, tmp_path) as health_url:
        env = clean_env(
            CARTORIO_OPS_CHECKS="api,database",
            CARTORIO_OPS_HEALTH_URL=health_url,
            CARTORIO_OPS_EXPECTED_APP_NAME=APP_NAME,
            DATABASE_URL=url,
        )
        result = run_cli("check", env=env)
    report = json.loads(result.stdout)
    assert result.returncode == 1, result.stdout
    assert report["checks"]["api"]["status"] == "ok"
    assert report["checks"]["api"]["signals"]["health"]["status_code"] == 200
    database = report["checks"]["database"]
    # Linux recusa na hora (unavailable); no Windows o driver só desiste no prazo e a
    # mesma porta fechada aparece como timeout. Os dois são falha comprovada.
    assert database["status"] == "fail"
    assert database["reason"] in ("unavailable", "timeout")
    assert secret not in result.stdout + result.stderr


@pr5._requires_real_postgres
def test_database_check_is_a_real_read_only_query(postgres_db: str) -> None:
    env = {"CARTORIO_OPS_CHECKS": "database", "DATABASE_URL": postgres_db}
    report = _check(env)
    connection = report["checks"]["database"]["signals"]["connection"]
    assert (connection["status"], connection["read_only"]) == ("ok", True)
    assert isinstance(connection["server_major"], int)


@pr5._requires_real_postgres
def test_read_only_transaction_refuses_writes(postgres_db: str) -> None:
    with (
        pytest.raises(ProbeError) as info,
        read_only_connection(postgres_db, "postgresql", 5) as conn,
    ):
        conn.exec_driver_sql("CREATE TABLE ops_nao_pode_existir (id int)")
    assert info.value.facts.get("sqlstate") == "25006"  # read_only_sql_transaction


@pr5._requires_real_postgres
def test_wrong_password_is_a_failure_without_credentials_in_output(postgres_db: str) -> None:
    from sqlalchemy.engine import make_url

    secret = f"errada-{uuid.uuid4().hex}"
    wrong = make_url(postgres_db).set(password=secret).render_as_string(hide_password=False)
    result = run_cli("check", env=clean_env(CARTORIO_OPS_CHECKS="database", DATABASE_URL=wrong))
    report = json.loads(result.stdout)
    assert result.returncode == 1
    assert report["checks"]["database"]["reason"] in ("auth_failed", "unavailable")
    assert secret not in result.stdout + result.stderr


@pr5._requires_real_postgres
def test_healthy_and_complete_configuration_on_postgres_returns_zero(
    postgres_db: str, tmp_path: Path, capsys
) -> None:
    # O banco esperado vem da DSN da bancada: o manifesto precisa ser dele.
    database = make_url(postgres_db).database or ""
    write_publication(
        tmp_path / "b", utc_now() - timedelta(hours=2), overrides={"database": database}
    )
    with running_app(postgres_db, APP_NAME, tmp_path) as health_url:
        env = {
            "CARTORIO_OPS_CHECKS": "api,database,alembic,backup",
            "CARTORIO_OPS_HEALTH_URL": health_url,
            "CARTORIO_OPS_EXPECTED_APP_NAME": APP_NAME,
            "CARTORIO_OPS_UNITS": "cartorio-lab.service:service,postgresql@18-main.service:service",
            "DATABASE_URL": postgres_db,
            "CARTORIO_OPS_RELEASE_DIR": str(REPO_ROOT),
            "CARTORIO_OPS_BACKUP_DIR": str(tmp_path / "b"),
            "CARTORIO_OPS_BACKUP_MAX_AGE_HOURS": "26",
            "CARTORIO_OPS_BACKUP_SERVICE_UNIT": "cartorio-lab-backup.service",
            "CARTORIO_OPS_BACKUP_TIMER_UNIT": "cartorio-lab-backup.timer",
        }
        code = cli.main(["check"], environ=env, runner=healthy_systemd())
    report = json.loads(capsys.readouterr().out)
    assert code == 0, json.dumps(report, indent=2)
    assert {c["status"] for c in report["checks"].values()} == {"ok"}


@pr5._requires_real_postgres
def test_alembic_divergence_on_postgres_is_reported_without_migrating(postgres_db: str) -> None:
    import psycopg

    conninfo = pr5._psycopg_conninfo(postgres_db)
    with psycopg.connect(conninfo, autocommit=True) as conn:
        (original,) = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        conn.execute("UPDATE alembic_version SET version_num = 'e3f4a5b6c7d8'")
    try:
        report = _check(
            {
                "CARTORIO_OPS_CHECKS": "alembic",
                "DATABASE_URL": postgres_db,
                "CARTORIO_OPS_RELEASE_DIR": str(REPO_ROOT),
            }
        )
        revision = report["checks"]["alembic"]["signals"]["revision"]
        assert (revision["status"], revision["reason"]) == ("fail", "revision_behind")
        with psycopg.connect(conninfo, autocommit=True) as conn:
            rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
        assert rows == [("e3f4a5b6c7d8",)], "o verificador aplicou migration"
    finally:
        with psycopg.connect(conninfo, autocommit=True) as conn:
            conn.execute("UPDATE alembic_version SET version_num = %s", (original,))


def _check(env: dict[str, str]) -> dict:
    result = run_cli("check", env=clean_env(**env))
    return json.loads(result.stdout)
