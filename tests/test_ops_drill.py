"""Ensaio de restauração: recusa de alvos indevidos e contrato do relatório.

Tudo aqui é puro (sem servidor): a execução completa do ensaio é do gate PostgreSQL
(``scripts/ops/pg_gate.py``), que a reprova se não passar.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from app.ops import drill, pgcluster
from app.ops.pgcluster import (
    WORK_MARKER,
    DrillRefused,
    ansi_safe,
    create_work_dir,
    remove_work_dir,
    require_clean_libpq_env,
    require_loopback,
    subprocess_env,
    verify_identity,
    verify_restore_target,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ops"))

import pg_gate  # noqa: E402

EXPECTED = {"cluster_name": "cartorio_ops_destino_x", "token": "t0k3n", "port": 15432}


@pytest.fixture
def any_work_root(monkeypatch):
    """O tmp_path desta máquina pode ser não-ASCII; a recusa disso é testada à parte."""
    monkeypatch.setattr(pgcluster, "ansi_safe", lambda path: True)


def _observed(**overrides) -> dict:
    return {
        "cluster_name": "cartorio_ops_destino_x",
        "token": "t0k3n",
        "port": "15432",
        "listen_addresses": "127.0.0.1",
        **overrides,
    }


@pytest.mark.parametrize("variable", ["PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS"])
def test_connection_override_variables_are_refused(variable: str) -> None:
    with pytest.raises(DrillRefused) as info:
        require_clean_libpq_env({variable: "qualquer"})
    assert info.value.reason == "libpq_env_override"
    assert info.value.facts["variables"] == [variable]


def test_inert_variables_do_not_block_because_every_parameter_is_explicit() -> None:
    require_clean_libpq_env({"PGHOST": "10.0.0.1", "PGPORT": "6543", "PGUSER": "x"})


def test_subprocesses_never_inherit_pg_variables_or_database_url() -> None:
    env = subprocess_env(
        {"PATH": "/bin", "PGHOST": "x", "pgpassword": "y", "DATABASE_URL": "z"}, A="1"
    )
    assert env == {"PATH": "/bin", "A": "1"}


@pytest.mark.parametrize("host", ["10.0.0.5", "localhost", "::1", "db.example", ""])
def test_external_targets_are_refused(host: str) -> None:
    with pytest.raises(DrillRefused) as info:
        require_loopback(host)
    assert info.value.reason == "target_not_local"


@pytest.mark.parametrize("host", ["10.0.0.5", "localhost"])
def test_cluster_never_connects_outside_loopback(tmp_path: Path, host: str) -> None:
    cluster = pgcluster.Cluster(
        label="destino", run_id="r1", pg_bin=tmp_path, root=tmp_path, port=5432, host=host
    )
    with pytest.raises(DrillRefused) as info:
        cluster.connect()  # recusado antes de importar o driver ou abrir socket
    assert info.value.reason == "target_not_local"
    with pytest.raises(DrillRefused):
        drill._db_url(cluster, "cartorio_drill_destino", "x")


def test_identity_proven_by_token_name_port_and_isolation() -> None:
    verify_identity(observed=_observed(), **EXPECTED)


@pytest.mark.parametrize(
    ("override", "reason"),
    [
        ({"token": "outro"}, "target_identity_unproven"),
        ({"cluster_name": "producao"}, "target_identity_unproven"),
        ({"port": "5432"}, "target_identity_unproven"),
        ({"token": None}, "target_identity_unproven"),
        ({"listen_addresses": "*"}, "target_not_isolated"),
        ({"listen_addresses": "0.0.0.0"}, "target_not_isolated"),
    ],
)
def test_unproven_or_exposed_targets_are_refused(override: dict, reason: str) -> None:
    with pytest.raises(DrillRefused) as info:
        verify_identity(observed=_observed(**override), **EXPECTED)
    assert info.value.reason == reason


@pytest.mark.parametrize(
    ("observed", "reason"),
    [
        # banco reaproveitado: marcador de outra execução
        (
            {"comment": "cartorio-ops-drill:outra:destino", "owner": "app", "user_relations": 0},
            "target_not_created_by_this_run",
        ),
        # banco externo: sem marcador nenhum
        ({"comment": None, "owner": "app", "user_relations": 0}, "target_not_created_by_this_run"),
        (
            {"comment": "cartorio-ops-drill:r1:destino", "owner": "postgres", "user_relations": 0},
            "target_not_created_by_this_run",
        ),
        # vazio é exigido, mas nunca suficiente: aqui o marcador confere e há tabelas
        (
            {"comment": "cartorio-ops-drill:r1:destino", "owner": "app", "user_relations": 3},
            "target_not_empty",
        ),
    ],
)
def test_restore_target_must_be_created_by_this_run_and_empty(observed: dict, reason: str) -> None:
    with pytest.raises(DrillRefused) as info:
        verify_restore_target(
            expected_marker="cartorio-ops-drill:r1:destino", expected_owner="app", observed=observed
        )
    assert info.value.reason == reason


def test_restore_target_accepted_only_with_marker_owner_and_empty() -> None:
    verify_restore_target(
        expected_marker="cartorio-ops-drill:r1:destino",
        expected_owner="app",
        observed={"comment": "cartorio-ops-drill:r1:destino", "owner": "app", "user_relations": 0},
    )


def test_non_ascii_work_root_is_refused_only_on_windows() -> None:
    assert ansi_safe(Path("C:/Usuários/Ação/Temp"), platform="win32") is False
    assert ansi_safe(Path("C:/bancada/Temp"), platform="win32") is True
    assert ansi_safe(Path("/srv/ação/tmp"), platform="linux") is True


def test_reused_work_directory_is_refused(tmp_path: Path, any_work_root) -> None:
    create_work_dir(tmp_path, "r1")
    with pytest.raises(DrillRefused) as info:
        create_work_dir(tmp_path, "r1")
    assert info.value.reason == "work_dir_reused"


def test_cleanup_removes_only_what_carries_this_run_marker(tmp_path: Path, any_work_root) -> None:
    mine = create_work_dir(tmp_path, "r1")
    (mine / "data").mkdir()
    foreign = tmp_path / "cartorio-ops-drill-r2"
    foreign.mkdir()
    (foreign / "importante.txt").write_text("não apagar", encoding="utf-8")
    other_run = create_work_dir(tmp_path, "r3")

    assert remove_work_dir(foreign, "r2") is False  # sem marcador
    assert remove_work_dir(other_run, "r1") is False  # marcador de outra execução
    assert remove_work_dir(mine, "r1") is True
    assert not mine.exists()
    assert (foreign / "importante.txt").exists() and (other_run / WORK_MARKER).exists()


def _drill_args(tmp_path: Path, *extra: str) -> list[str]:
    (tmp_path / "work").mkdir(exist_ok=True)
    return [
        "--pg-bin",
        str(tmp_path / "sem-binarios"),
        "--work-root",
        str(tmp_path / "work"),
        "--report",
        str(tmp_path / "drill.json"),
        *extra,
    ]


def test_drill_refuses_override_env_before_creating_anything(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("PGSERVICE", "perfil-de-producao")
    assert drill.main(_drill_args(tmp_path)) == 2
    report = json.loads((tmp_path / "drill.json").read_text(encoding="utf-8"))
    assert (report["verdict"], report["reason"]) == ("refused", "libpq_env_override")
    assert report["cleanup"] == {"work_dir_created": False}
    assert list((tmp_path / "work").iterdir()) == []
    capsys.readouterr()


def test_drill_without_postgres_binaries_refuses_and_cleans_up(
    tmp_path, monkeypatch, capsys, any_work_root
) -> None:
    for name in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS"):
        monkeypatch.delenv(name, raising=False)
    assert drill.main(_drill_args(tmp_path)) == 2
    report = json.loads((tmp_path / "drill.json").read_text(encoding="utf-8"))
    assert (report["verdict"], report["reason"]) == ("refused", "pg_binary_missing")
    assert report["cleanup"]["work_dir_removed"] is True
    assert list((tmp_path / "work").iterdir()) == []
    for key in (
        "schema",
        "schema_version",
        "run_id",
        "mode",
        "classification",
        "started_at",
        "finished_at",
        "release",
    ):
        assert key in report
    assert report["schema"] == "cartorio_system.ops.restore_drill"
    assert report["classification"] == "bench_measurement"
    assert report["release"]["alembic_heads"] == ["f4a5b6c7d8e9"]
    capsys.readouterr()


def test_copy_mode_requires_the_expected_record(tmp_path) -> None:
    with pytest.raises(SystemExit) as info:
        drill.main(_drill_args(tmp_path, "--from-manifest", str(tmp_path / "backup-x.json")))
    assert info.value.code == 2


# ---------------------------------------------------------------------------
# Gate PostgreSQL: prova obrigatória pulada reprova
# ---------------------------------------------------------------------------


def _junit(tmp_path: Path, **counts: int) -> Path:
    attrs = " ".join(f'{k}="{v}"' for k, v in counts.items())
    path = tmp_path / "junit.xml"
    path.write_text(f'<testsuites><testsuite name="pytest" {attrs}/></testsuites>', "utf-8")
    return path


def test_gate_fails_when_a_mandatory_proof_is_skipped(tmp_path: Path) -> None:
    totals = pg_gate.junit_totals(_junit(tmp_path, tests=20, failures=0, errors=0, skipped=5))
    assert pg_gate.gate_verdict(0, totals) == ["mandatory_proof_skipped"]


def test_gate_passes_only_with_everything_executed(tmp_path: Path) -> None:
    totals = pg_gate.junit_totals(_junit(tmp_path, tests=20, failures=0, errors=0, skipped=0))
    assert pg_gate.gate_verdict(0, totals) == []


def test_gate_fails_on_empty_collection_and_on_failures(tmp_path: Path) -> None:
    empty = pg_gate.junit_totals(_junit(tmp_path, tests=0, failures=0, errors=0, skipped=0))
    assert "no_tests_collected" in pg_gate.gate_verdict(5, empty)
    failed = {"tests": 3, "failures": 1, "errors": 0, "skipped": 0}
    assert pg_gate.gate_verdict(1, failed) == ["pytest_exit_nonzero", "tests_failed"]


# ---------------------------------------------------------------------------
# Partes do ensaio que não dependem de servidor PostgreSQL
# ---------------------------------------------------------------------------

_TOC_SAMPLE = """\
$ pg_restore --list /bancada/artefato/backup-20260101T000000Z.dump
;
; Archive created at 2026-01-01 00:00:00 UTC
;     dbname: cartorio_drill_origem
;     TOC Entries: 42
;     Compression: gzip
;     Format: CUSTOM
;     Dumped from database version: 18.0
;     Dumped by pg_dump version: 18.0
;
; Selected TOC Entries:
;
3445; 0 0 ENCODING - ENCODING
218; 1259 16390 TABLE public alembic_version cartorio_drill_app
"""


def test_toc_listing_prefers_the_header_count() -> None:
    assert drill.parse_toc_listing(_TOC_SAMPLE) == (42, "2026-01-01 00:00:00 UTC")


def test_toc_listing_without_header_counts_entries() -> None:
    body = "\n".join(line for line in _TOC_SAMPLE.splitlines() if "TOC Entries" not in line)
    assert drill.parse_toc_listing(body)[0] == 2


def test_revisions_ignore_the_logged_command_line() -> None:
    output = "$ python -m alembic current --hint aaaaaaaaaaaa\nf4a5b6c7d8e9 (head)\n"
    assert drill._revisions(output) == ["f4a5b6c7d8e9"]


def test_scrub_hides_generated_secrets_and_dsn_passwords() -> None:
    text = "falhou: postgresql+psycopg://app:abc123@127.0.0.1:5/db senha=XyZ-gerada"
    scrubbed = drill._scrub(text, ["XyZ-gerada"])
    assert "abc123" not in scrubbed and "XyZ-gerada" not in scrubbed


def test_drill_api_process_round_trips_a_record_on_the_real_app(
    tmp_path: Path, any_work_root
) -> None:
    """Mesmo caminho HTTP que o ensaio usa no destino (POST, GET, prova de instância),
    aqui contra a API real com SQLite."""
    from tests.ops_support import migrate_sqlite

    url = migrate_sqlite(tmp_path / "api.db")
    work = create_work_dir(tmp_path, "api-check")
    ctx = drill.Ctx(
        run_id="api-check",
        pg_bin=tmp_path,
        work=work,
        clock=lambda: None,
        base_env=pgcluster.subprocess_env(__import__("os").environ),
    )
    with drill.ApiProcess(ctx, url, "Cartorio System - ensaio api", "x") as api:
        created = api.request(
            "POST",
            "/audit/findings",
            {
                "finding_code": "DRILL-API-CHECK",
                "title": "Registro sintético",
                "description": "Teste do cliente HTTP do ensaio.",
                "category": "SYSTEM",
                "origin": "MANUAL",
                "severity": "LOW",
                "probability": "LOW",
                "impact": "LOW",
                "priority": "BACKLOG",
                "evidence_summary": "sintético",
                "recommended_action": "nenhuma",
            },
        )
        fetched = api.request("GET", f"/audit/findings/{created['id']}")
        process = api.process
    assert fetched["finding_code"] == "DRILL-API-CHECK"
    assert process is not None and process.poll() is not None  # encerrado no __exit__


# ---------------------------------------------------------------------------
# Achado 2 do PR #6: cópia de origem divergente não é restaurada
# ---------------------------------------------------------------------------


def _copy_source(tmp_path: Path, database: str) -> Path:
    from datetime import UTC, datetime, timedelta

    from tests.ops_support import write_publication

    _, manifest = write_publication(
        tmp_path / "copia",
        datetime.now(UTC) - timedelta(hours=1),
        overrides={"database": database},
    )
    return manifest


def _ctx(tmp_path: Path, run_id: str) -> drill.Ctx:
    import os
    from datetime import UTC, datetime

    return drill.Ctx(
        run_id=run_id,
        pg_bin=tmp_path / "sem-binarios",
        work=create_work_dir(tmp_path, run_id),
        clock=lambda: datetime.now(UTC),
        base_env=pgcluster.subprocess_env(os.environ),
    )


def test_copy_of_another_database_is_refused_before_restoring(
    tmp_path: Path, any_work_root
) -> None:
    manifest = _copy_source(tmp_path, "outro_banco_ficticio")
    ctx = _ctx(tmp_path, "r-copia")
    source = drill._copy_phase(ctx, manifest, 1, "COD-SINTETICO", "cartorio_lab")
    with pytest.raises(DrillRefused) as info:
        drill._verify_artifact(ctx, source)
    # Recusado na validação do manifesto: nem chegou ao pg_restore (sem binários aqui).
    assert info.value.reason == "database_mismatch"
    assert "artifact" not in ctx.report


def test_copy_of_the_expected_database_passes_the_manifest_check(
    tmp_path: Path, any_work_root
) -> None:
    manifest = _copy_source(tmp_path, "cartorio_lab")
    ctx = _ctx(tmp_path, "r-copia-ok")
    source = drill._copy_phase(ctx, manifest, 1, "COD-SINTETICO", "cartorio_lab")
    with pytest.raises(DrillRefused) as info:
        drill._verify_artifact(ctx, source)
    # Passou pelo manifesto e pelo banco; parou só por falta do pg_restore desta bancada.
    assert info.value.reason == "pg_binary_missing"


@pytest.mark.parametrize(
    ("extra", "message"),
    [
        (["--expect-finding-id", "1", "--expect-finding-code", "C"], "expect-database"),
        (
            ["--expect-finding-id", "1", "--expect-finding-code", "C", "--expect-database", "a b"],
            "expect-database",
        ),
        (
            [
                "--expect-finding-id",
                "1",
                "--expect-finding-code",
                "C",
                "--expect-database",
                "cartorio_lab",
                "--export-artifact",
                "x",
            ],
            "export-artifact",
        ),
    ],
)
def test_copy_mode_arguments_are_validated(tmp_path, capsys, extra, message) -> None:
    with pytest.raises(SystemExit) as info:
        drill.main(_drill_args(tmp_path, "--from-manifest", str(tmp_path / "b.json"), *extra))
    assert info.value.code == 2
    assert message in capsys.readouterr().err


def test_expect_database_is_only_for_copy_mode(tmp_path, capsys) -> None:
    with pytest.raises(SystemExit) as info:
        drill.main(_drill_args(tmp_path, "--expect-database", "cartorio_lab"))
    assert info.value.code == 2
