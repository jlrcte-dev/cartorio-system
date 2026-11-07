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
import sys
import uuid
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

from app.ops import cli
from app.ops.backup import database_from_dsn
from app.ops.checks import ProbeError, read_only_connection, release_heads
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
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ops"))

import pg_gate  # noqa: E402


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


# ---------------------------------------------------------------------------
# Revisão final do PR #6: vínculo do backup ao banco que a conexão abriu, com dois
# bancos reais na mesma revisão Alembic (criados pelo gate: pg_gate.BINDING_DATABASES)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def binding_databases() -> Iterator[dict[str, str]]:
    """URL de cada banco do vínculo, com um schema exclusivo desta execução — o mesmo
    nome nos dois —, migrado até a head e sempre descartado. As travas do PR #5 valem
    antes de tudo: a URL base é a da bancada conhecida, e o ambiente não tem override."""
    base = pr5._require_postgres_url(pr5.POSTGRES_URL)
    pr5._require_clean_pg_env(base)
    schema = f"ops_vinculo_{uuid.uuid4().hex[:12]}"
    urls = {
        name: make_url(base).set(database=name).render_as_string(hide_password=False)
        for name in pg_gate.BINDING_DATABASES
    }
    created: list[str] = []
    try:
        for url in urls.values():
            pr5._create_schema(url, schema)
            created.append(url)
            pr5._run_alembic("upgrade", "head", database_url=pr5._scoped_url(url, schema))
        yield {name: pr5._scoped_url(url, schema) for name, url in urls.items()}
    finally:
        for url in created:
            pr5._drop_schema(url, schema)


def _opened(url: str) -> tuple[str, str]:
    """Banco e revisão Alembic vistos pela mesma conexão somente leitura do verificador."""
    with read_only_connection(url, "postgresql", 10) as conn:
        database = conn.exec_driver_sql("SELECT current_database()").scalar_one()
        revision = conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
    return str(database), str(revision)


def _override(url: str, database: str) -> str:
    """A mesma DSN, com o banco do caminho e ``dbname`` na querystring apontando outro."""
    return (
        make_url(url).update_query_dict({"dbname": database}).render_as_string(hide_password=False)
    )


def _binding_env(directory: Path, dsn: str, checks: str, **extra: str) -> dict[str, str]:
    return {
        "CARTORIO_OPS_CHECKS": checks,
        "DATABASE_URL": dsn,
        "CARTORIO_OPS_RELEASE_DIR": str(REPO_ROOT),
        "CARTORIO_OPS_BACKUP_DIR": str(directory),
        "CARTORIO_OPS_BACKUP_MAX_AGE_HOURS": "26",
        **extra,
    }


def _verify(env: dict[str, str]) -> tuple[int, dict, str]:
    result = run_cli("check", env=clean_env(**env))
    return result.returncode, json.loads(result.stdout), result.stdout + result.stderr


@pr5._requires_real_postgres
def test_override_dsn_opens_the_other_real_database_on_the_same_revision(
    binding_databases: dict[str, str],
) -> None:
    a, b = pg_gate.BINDING_DATABASES
    heads, _ = release_heads(REPO_ROOT)
    assert _opened(binding_databases[a]) == (a, heads[0])
    assert _opened(binding_databases[b]) == (b, heads[0])
    # O caminho diz A; a querystring diz B; quem responde é B.
    assert _opened(_override(binding_databases[a], b)) == (b, heads[0])


@pr5._requires_real_postgres
@pytest.mark.parametrize("variant", ["plain", "override", "blank_dbname", "no_path"])
def test_static_reading_of_the_dsn_matches_the_database_the_server_reports(
    binding_databases: dict[str, str], variant: str
) -> None:
    """Modo backup isolado não conecta: a leitura da DSN tem de dar o banco que a conexão
    real abre — conferido aqui contra ``current_database()`` do servidor."""
    a, b = pg_gate.BINDING_DATABASES
    url = make_url(binding_databases[a])
    dsn = {
        "plain": url.render_as_string(hide_password=False),
        "override": _override(binding_databases[a], b),
        "blank_dbname": url.render_as_string(hide_password=False) + "&dbname=",
        "no_path": _override(url.set(database=None).render_as_string(hide_password=False), b),
    }[variant]
    observed, _ = _opened(dsn)
    assert database_from_dsn(dsn) == (observed, None)


@pr5._requires_real_postgres
def test_manifest_of_the_database_the_override_did_not_open_is_refused(
    binding_databases: dict[str, str], tmp_path: Path
) -> None:
    """A configuração da revisão, com servidor real: manifesto (e nome explícito) do banco
    A; DSN que nomeia A no caminho e abre B pelo override; A e B na mesma revisão."""
    a, b = pg_gate.BINDING_DATABASES
    write_publication(tmp_path, utc_now() - timedelta(hours=2), overrides={"database": a})
    override = _override(binding_databases[a], b)
    explicit = {"CARTORIO_OPS_BACKUP_EXPECTED_DATABASE": a}

    code, report, output = _verify(
        _binding_env(tmp_path, override, "database,alembic,backup", **explicit)
    )
    checks = report["checks"]
    assert code == 2, json.dumps(report, indent=2)
    assert checks["database"]["status"] == "ok"
    assert checks["database"]["signals"]["connection"]["identity_observed"] is True
    assert checks["alembic"]["reason"] == "revision_match"  # B também está na head
    assert (checks["backup"]["status"], checks["backup"]["reason"]) == (
        "inconclusive",
        "expected_database_conflict",
    )
    for hidden in (a, b, str(make_url(override).password)):
        assert hidden not in output

    # Sem o nome explícito, o banco esperado é o que a conexão abriu, e a cópia de A cai.
    code, report, _ = _verify(_binding_env(tmp_path, override, "database,alembic,backup"))
    assert (code, report["checks"]["backup"]["reason"]) == (1, "database_mismatch")


@pr5._requires_real_postgres
def test_identity_and_manifest_coherent_on_the_real_server_return_zero(
    binding_databases: dict[str, str], tmp_path: Path
) -> None:
    a, b = pg_gate.BINDING_DATABASES
    write_publication(tmp_path / "a", utc_now() - timedelta(hours=2), overrides={"database": a})
    env = _binding_env(
        tmp_path / "a",
        binding_databases[a],
        "database,alembic,backup",
        CARTORIO_OPS_BACKUP_EXPECTED_DATABASE=a,
    )
    code, report, _ = _verify(env)
    assert code == 0, json.dumps(report, indent=2)
    identity = report["checks"]["backup"]["signals"]["expected_database"]
    assert identity["reason"] == "expected_database_from_connection"

    # A DSN com override, lida como a conexão a abre: a cópia de B é a esperada.
    write_publication(tmp_path / "b", utc_now() - timedelta(hours=2), overrides={"database": b})
    override = _override(binding_databases[a], b)
    code, report, _ = _verify(_binding_env(tmp_path / "b", override, "database,alembic,backup"))
    assert code == 0, json.dumps(report, indent=2)


@pr5._requires_real_postgres
def test_isolated_backup_mode_reads_the_dsn_like_the_real_connection(
    binding_databases: dict[str, str], tmp_path: Path
) -> None:
    a, b = pg_gate.BINDING_DATABASES
    override = _override(binding_databases[a], b)
    assert _opened(override)[0] == b

    write_publication(tmp_path / "a", utc_now() - timedelta(hours=2), overrides={"database": a})
    explicit = {"CARTORIO_OPS_BACKUP_EXPECTED_DATABASE": a}
    code, report, _ = _verify(_binding_env(tmp_path / "a", override, "backup", **explicit))
    assert (code, report["checks"]["backup"]["reason"]) == (2, "expected_database_conflict")

    write_publication(tmp_path / "b", utc_now() - timedelta(hours=2), overrides={"database": b})
    code, report, _ = _verify(_binding_env(tmp_path / "b", override, "backup"))
    identity = report["checks"]["backup"]["signals"]["expected_database"]
    assert (code, identity["reason"]) == (0, "expected_database_from_dsn")
