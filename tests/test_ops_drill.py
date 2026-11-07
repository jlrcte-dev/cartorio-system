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
    DrillFailed,
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
    assert report["cleanup"] == {"confirmed": True, "work_dir_created": False}
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


# ---------------------------------------------------------------------------
# Achado 3 do PR #6: parada confirmada antes da limpeza (falhas induzidas)
# ---------------------------------------------------------------------------


class FakeTools:
    """Substitui ``pgcluster.run_tool``: simula initdb e pg_ctl e registra as chamadas.

    ``status`` dá o código do ``pg_ctl status`` por rótulo do cluster (0 rodando,
    3 parado); ``stop`` dá o retorno do ``pg_ctl stop`` ou uma exceção a lançar.
    """

    def __init__(self, *, start="ok", stop=None, status=None) -> None:
        self.start = start
        self.stop = stop or {}
        self.status = status or {}
        self.calls: list[tuple[str, str]] = []

    def __call__(self, cmd, *, env, log, timeout=120):
        import subprocess

        tool = Path(cmd[0]).name
        action = cmd[1] if tool == "pg_ctl" else tool
        data = Path(cmd[cmd.index("-D") + 1])
        label = data.parent.name
        self.calls.append((action, label))
        if action == "initdb":
            data.mkdir(parents=True)
            (data / "postgresql.conf").write_text("", encoding="utf-8")
            (data / "pg_hba.conf").write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0)
        if action == "start":
            if self.start == "timeout":
                raise subprocess.TimeoutExpired(cmd, timeout)
            return subprocess.CompletedProcess(cmd, 0 if self.start == "ok" else 1)
        if action == "stop":
            outcome = self.stop.get(label, 0)
            if isinstance(outcome, BaseException):
                raise outcome
            return subprocess.CompletedProcess(cmd, outcome)
        if action == "status":
            return subprocess.CompletedProcess(cmd, self.status.get(label, 3))
        raise AssertionError(f"ação inesperada: {cmd}")


@pytest.fixture
def fake_pg(monkeypatch):
    def install(tools: FakeTools) -> FakeTools:
        monkeypatch.setattr(pgcluster, "run_tool", tools)
        monkeypatch.setattr(pgcluster, "pg_binary", lambda pg_bin, name: Path(name))
        return tools

    return install


def _running_cluster(work: Path, label: str) -> pgcluster.Cluster:
    cluster = pgcluster.Cluster(label=label, run_id="r1", pg_bin=work, root=work / label)
    cluster.state = "running"
    return cluster


def test_start_timeout_leaves_the_cluster_uncertain_and_the_area_preserved(
    tmp_path: Path, any_work_root, fake_pg
) -> None:
    tools = fake_pg(FakeTools(start="timeout", stop={"destino": 1}, status={"destino": 0}))
    ctx = _ctx(tmp_path, "r-timeout")
    cluster = pgcluster.Cluster(
        label="destino", run_id="r-timeout", pg_bin=tmp_path, root=ctx.work / "destino"
    )
    ctx.clusters.append(cluster)
    cluster.initialize({})
    with pytest.raises(DrillFailed) as info:
        cluster.start({})
    assert info.value.reason == "cluster_start_timeout"
    assert cluster.state == "start_attempted"  # o postmaster pode seguir subindo

    cleanup = drill._cleanup(ctx, keep=False)
    assert cleanup["clusters"] == {"destino": "uncertain"}
    assert (cleanup["confirmed"], cleanup["work_dir_removed"]) == (False, False)
    assert ctx.work.exists() and (ctx.work / WORK_MARKER).exists()
    assert ("status", "destino") in tools.calls
    assert drill.final_verdict("passed", "ok", cleanup) == ("failed", "cleanup_unconfirmed")


def test_every_cluster_gets_the_stop_order_even_when_one_raises(
    tmp_path: Path, any_work_root, fake_pg
) -> None:
    tools = fake_pg(
        FakeTools(stop={"origem": RuntimeError("pg_ctl quebrou"), "destino": 1}, status={})
    )
    ctx = _ctx(tmp_path, "r-varios")
    ctx.clusters.extend(
        _running_cluster(ctx.work, label) for label in ("origem", "destino", "gate")
    )
    cleanup = drill._cleanup(ctx, keep=False)
    assert [label for action, label in tools.calls if action == "stop"] == [
        "origem",
        "destino",
        "gate",
    ]
    # destino: o stop falhou, mas o status confirmou a parada (saída 3).
    assert cleanup["clusters"] == {"origem": "uncertain", "destino": "stopped", "gate": "stopped"}
    assert cleanup["confirmed"] is False and ctx.work.exists()


def test_failed_stop_return_is_settled_by_the_status_check(
    tmp_path: Path, any_work_root, fake_pg
) -> None:
    fake_pg(FakeTools(stop={"destino": 1}, status={"destino": 3}))
    ctx = _ctx(tmp_path, "r-confirma")
    ctx.clusters.append(_running_cluster(ctx.work, "destino"))
    cleanup = drill._cleanup(ctx, keep=False)
    assert (cleanup["confirmed"], cleanup["work_dir_removed"]) == (True, True)
    assert not ctx.work.exists()


def test_cluster_never_started_needs_no_stop(tmp_path: Path, any_work_root, fake_pg) -> None:
    tools = fake_pg(FakeTools())
    ctx = _ctx(tmp_path, "r-nunca")
    ctx.clusters.append(
        pgcluster.Cluster(label="destino", run_id="r-nunca", pg_bin=tmp_path, root=ctx.work / "d")
    )
    cleanup = drill._cleanup(ctx, keep=False)
    assert cleanup["clusters"] == {"destino": "not_started"} and cleanup["confirmed"] is True
    assert tools.calls == []


def test_removal_failure_fails_an_otherwise_passed_drill(
    tmp_path: Path, any_work_root, fake_pg, monkeypatch
) -> None:
    fake_pg(FakeTools())
    monkeypatch.setattr(drill, "remove_work_dir", lambda path, run_id: False)
    ctx = _ctx(tmp_path, "r-remocao")
    ctx.clusters.append(_running_cluster(ctx.work, "destino"))
    cleanup = drill._cleanup(ctx, keep=False)
    assert (cleanup["clusters_stopped"], cleanup["confirmed"]) == (True, False)
    assert drill.final_verdict("passed", "ok", cleanup) == ("failed", "cleanup_unconfirmed")


def test_original_failure_is_preserved_and_cleanup_recorded_apart() -> None:
    cleanup = {"confirmed": False}
    assert drill.final_verdict("failed", "pg_restore_failed", cleanup) == (
        "failed",
        "pg_restore_failed",
    )
    assert drill.final_verdict("refused", "database_mismatch", cleanup) == (
        "refused",
        "database_mismatch",
    )


def test_drill_with_a_possibly_active_cluster_is_never_passed(
    tmp_path: Path, any_work_root, fake_pg, monkeypatch, capsys
) -> None:
    """Caminho completo do ensaio: partida estoura o prazo, o servidor continua de pé
    (status 0) mesmo depois do stop — diretório preservado, veredito reprovado, saída 1."""
    fake_pg(FakeTools(start="timeout", stop={"origem": 1}, status={"origem": 0}))
    monkeypatch.setattr(drill, "pg_binary", lambda pg_bin, name: Path(name))
    monkeypatch.setattr(drill, "tool_version", lambda binary: ("18.0", 18))
    for name in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS"):
        monkeypatch.delenv(name, raising=False)
    assert drill.main(_drill_args(tmp_path)) == 1
    capsys.readouterr()
    report = json.loads((tmp_path / "drill.json").read_text(encoding="utf-8"))
    assert (report["verdict"], report["reason"]) == ("failed", "cluster_start_timeout")
    cleanup = report["cleanup"]
    assert cleanup["clusters"] == {"origem": "uncertain"}
    assert (cleanup["confirmed"], cleanup["work_dir_removed"]) == (False, False)
    assert cleanup["kept"] == "cluster_stop_unconfirmed"
    [kept] = list((tmp_path / "work").iterdir())
    assert (kept / WORK_MARKER).exists()


def _gate_args(tmp_path: Path) -> list[str]:
    (tmp_path / "work").mkdir(exist_ok=True)
    return [
        "--pg-bin",
        str(tmp_path / "bin"),
        "--work-root",
        str(tmp_path / "work"),
        "--report",
        str(tmp_path / "gate.json"),
    ]


@pytest.fixture
def fake_gate(monkeypatch, fake_pg):
    """Gate com ferramentas falsas: suíte "aprovada" e prova de restauração espiã."""
    drill_runs: list[str] = []

    def install(tools: FakeTools) -> list[str]:
        fake_pg(tools)
        monkeypatch.setattr(pg_gate, "pg_binary", lambda pg_bin, name: Path(name))
        monkeypatch.setattr(pg_gate, "tool_version", lambda binary: ("18.0", 18))

        def prove(self) -> None:
            self.server_version, self.server_major = "18.0", 18

        monkeypatch.setattr(pgcluster.Cluster, "prove_identity", prove)
        monkeypatch.setattr(pg_gate, "_run_suite", lambda *args: [])

        def fake_drills(args, run_id):
            drill_runs.append("synthetic")
            return {"synthetic": {"verdict": "passed"}}, []

        monkeypatch.setattr(pg_gate, "_run_drills", fake_drills)
        for name in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS"):
            monkeypatch.delenv(name, raising=False)
        return drill_runs

    return install


def test_gate_starts_no_restore_proof_while_the_test_cluster_may_be_active(
    tmp_path: Path, any_work_root, fake_gate, capsys
) -> None:
    drill_runs = fake_gate(FakeTools(stop={"gate": 1}, status={"gate": 0}))
    assert pg_gate.main(_gate_args(tmp_path)) == 1
    capsys.readouterr()
    report = json.loads((tmp_path / "gate.json").read_text(encoding="utf-8"))
    assert report["gate_cleanup"] == {
        "cluster": "uncertain",
        "work_dir_removed": False,
        "confirmed": False,
    }
    assert "gate_cleanup_unconfirmed" in report["reasons"]
    assert drill_runs == []  # a prova de restauração nem começou
    assert len(list((tmp_path / "work").iterdir())) == 1  # área preservada


def test_gate_runs_the_restore_proof_only_after_confirmed_cleanup(
    tmp_path: Path, any_work_root, fake_gate, capsys
) -> None:
    drill_runs = fake_gate(FakeTools(status={"gate": 3}))
    assert pg_gate.main(_gate_args(tmp_path)) == 0
    capsys.readouterr()
    report = json.loads((tmp_path / "gate.json").read_text(encoding="utf-8"))
    assert report["gate_cleanup"]["confirmed"] is True
    assert drill_runs == ["synthetic"]
    assert list((tmp_path / "work").iterdir()) == []


# ---------------------------------------------------------------------------
# Achado 1 do PR #6: área de trabalho, cópias e credenciais privadas
# ---------------------------------------------------------------------------

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="modos de arquivo POSIX")


def _mode(path: Path) -> int:
    import stat

    return stat.S_IMODE(path.stat().st_mode)


def _snapshot(directory: Path) -> dict[str, tuple[int, int, bytes]]:
    return {p.name: (_mode(p), p.stat().st_mtime_ns, p.read_bytes()) for p in directory.iterdir()}


@posix_only
def test_copy_mode_is_private_under_umask_022_and_leaves_the_source_untouched(
    tmp_path: Path, any_work_root
) -> None:
    import os

    manifest = _copy_source(tmp_path, "cartorio_lab")
    for item in manifest.parent.iterdir():
        item.chmod(0o600)
    before = _snapshot(manifest.parent)
    (tmp_path / "raiz").mkdir()
    previous = os.umask(0o022)  # o cenário do achado: umask permissivo do operador
    try:
        ctx = _ctx(tmp_path / "raiz", "r-privado")
        source = drill._copy_phase(ctx, manifest, 1, "COD-SINTETICO", "cartorio_lab")
    finally:
        os.umask(previous)

    artifact_dir = source["dir"]
    assert _mode(ctx.work) == 0o700 and _mode(artifact_dir) == 0o700
    assert _mode(ctx.work / WORK_MARKER) == 0o600
    copies = sorted(artifact_dir.iterdir())
    assert [p.name for p in copies] == sorted(before)
    assert {_mode(p) for p in copies} == {0o600}
    assert {p.name: p.read_bytes() for p in copies} == {k: v[2] for k, v in before.items()}
    assert _snapshot(manifest.parent) == before  # origem intocada: modo, mtime e conteúdo
    assert ctx.report["isolation"] == {
        "work_dir": "0700",
        "artifact_dir": "0700",
        "artifact_files": ["0600"],
    }


@posix_only
def test_credentials_are_private_from_creation(tmp_path: Path, any_work_root, fake_pg) -> None:
    import os

    class RecordingTools(FakeTools):
        pwfile_mode: int | None = None

        def __call__(self, cmd, *, env, log, timeout=120):
            if Path(cmd[0]).name == "initdb":
                pwfile = Path(next(a for a in cmd if a.startswith("--pwfile=")).split("=", 1)[1])
                self.pwfile_mode = _mode(pwfile)
            return super().__call__(cmd, env=env, log=log, timeout=timeout)

    tools = fake_pg(RecordingTools())
    previous = os.umask(0o022)
    try:
        ctx = _ctx(tmp_path, "r-credenciais")
        cluster = pgcluster.Cluster(
            label="destino", run_id="r-credenciais", pg_bin=tmp_path, root=ctx.work / "destino"
        )
        cluster.initialize({})
        cluster.port = 15432
        drill._pgpass(ctx, cluster, "cartorio_drill_destino", "senha-gerada")
    finally:
        os.umask(previous)
    assert tools.pwfile_mode == 0o600  # já 0600 quando o initdb o leu
    assert not (cluster.root / "initdb.pw").exists()
    assert _mode(cluster.root) == 0o700
    assert _mode(ctx.work / "pgpass-destino") == 0o600


@posix_only
def test_area_kept_after_failure_stays_private(tmp_path: Path, any_work_root, fake_pg) -> None:
    fake_pg(FakeTools())
    ctx = _ctx(tmp_path, "r-mantida")
    ctx.clusters.append(_running_cluster(ctx.work, "destino"))
    cleanup = drill._cleanup(ctx, keep=True)
    assert cleanup["kept"] == "keep_on_failure"
    assert _mode(ctx.work) == 0o700


def test_copy_mode_is_refused_before_copying_where_isolation_is_unprovable(
    tmp_path: Path, any_work_root, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(drill, "copy_mode_supported", lambda: False)
    for name in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS"):
        monkeypatch.delenv(name, raising=False)
    manifest = _copy_source(tmp_path, "cartorio_lab")
    before = {p.name: p.read_bytes() for p in manifest.parent.iterdir()}
    args = _drill_args(
        tmp_path,
        "--from-manifest",
        str(manifest),
        "--expect-finding-id",
        "1",
        "--expect-finding-code",
        "COD-SINTETICO",
        "--expect-database",
        "cartorio_lab",
    )
    assert drill.main(args) == 2
    capsys.readouterr()
    report = json.loads((tmp_path / "drill.json").read_text(encoding="utf-8"))
    assert (report["verdict"], report["reason"]) == ("refused", "copy_mode_unsupported_platform")
    assert report["cleanup"] == {"confirmed": True, "work_dir_created": False}
    assert list((tmp_path / "work").iterdir()) == []  # nada copiado
    assert {p.name: p.read_bytes() for p in manifest.parent.iterdir()} == before


def test_copy_mode_platform_rule() -> None:
    assert drill.copy_mode_supported("win32") is False
    assert drill.copy_mode_supported("linux") is True


def test_report_with_a_generated_credential_is_never_written() -> None:
    report = {"schema": "s", "run_id": "r", "verdict": "passed", "detalhe": "x senha-gerada-123 y"}
    cleaned = drill.without_secrets(report, ["senha-gerada-123"])
    assert (cleaned["verdict"], cleaned["reason"]) == ("failed", "secret_in_report")
    assert "senha-gerada-123" not in json.dumps(cleaned)
    assert drill.without_secrets(report, ["outra"]) is report


# ---------------------------------------------------------------------------
# Gate: modo cópia ponta a ponta a partir da cópia sintética exportada
# ---------------------------------------------------------------------------


def _scripted_drills(monkeypatch, overrides=None, *, mutate_source=False):
    """Substitui ``pg_gate._drill``: a prova sintética "exporta" uma cópia; os demais
    ensaios devolvem o desfecho roteirizado."""
    healthy = {
        "drill": (0, {"verdict": "passed", "record": {"finding_id": 7, "finding_code": "DRILL-X"}}),
        "copy": (0, {"verdict": "passed", "isolation": dict(pg_gate.PRIVATE_AREA)}),
        "copy-foreign": (
            2,
            {"verdict": "refused", "reason": "database_mismatch", "cleanup": {"clusters": {}}},
        ),
    }
    outcomes = healthy | (overrides or {})
    calls: list[dict] = []

    def fake(args, name, *extra, umask=None):
        calls.append({"name": name, "extra": extra, "umask": umask})
        if name == "drill":
            export = Path(extra[extra.index("--export-artifact") + 1])
            export.mkdir(parents=True)
            (export / "backup-20260101T000000Z.json").write_text("{}", encoding="utf-8")
            (export / "backup-20260101T000000Z.dump").write_bytes(b"sintetico")
        elif mutate_source:
            manifest = Path(extra[extra.index("--from-manifest") + 1])
            manifest.with_suffix(".dump").write_bytes(b"alterado")
        code, data = outcomes[name]
        return code, data, f"{name}.json"

    monkeypatch.setattr(pg_gate, "_drill", fake)
    return calls


def test_gate_copy_proofs_restore_the_expected_database_and_refuse_a_foreign_one(
    tmp_path: Path, monkeypatch
) -> None:
    calls = _scripted_drills(monkeypatch)
    results, reasons = pg_gate._drill_proofs(None, tmp_path / "artefato")
    assert reasons == []
    assert [c["name"] for c in calls] == ["drill", "copy", "copy-foreign"]
    assert calls[0]["umask"] is None
    assert calls[1]["umask"] == calls[2]["umask"] == 0o022
    assert calls[1]["extra"][-2:] == ("--expect-database", drill.ORIGIN_DB)
    assert calls[2]["extra"][-2:] == ("--expect-database", pg_gate.FOREIGN_DATABASE)
    for call in calls[1:]:
        assert call["extra"][call["extra"].index("--expect-finding-id") + 1] == "7"
    assert results["copy"]["isolation"] == pg_gate.PRIVATE_AREA
    assert results["copy_foreign_database"]["cluster_provisioned"] is False
    assert results["copy_source_untouched"] is True


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"copy": (1, {"verdict": "failed", "reason": "restore_failed"})}, "copy_drill_not_passed"),
        (
            {"copy": (0, {"verdict": "passed", "isolation": {"work_dir": "0755"}})},
            "copy_area_not_private",
        ),
        (
            {"copy-foreign": (0, {"verdict": "passed", "cleanup": {"clusters": {"destino": "x"}}})},
            "foreign_copy_not_refused",
        ),
        (
            {"copy-foreign": (2, {"verdict": "refused", "reason": "copy_incomplete"})},
            "foreign_copy_not_refused",
        ),
    ],
)
def test_gate_copy_proofs_fail_on_each_broken_guarantee(
    tmp_path: Path, monkeypatch, overrides, reason
) -> None:
    _scripted_drills(monkeypatch, overrides)
    _, reasons = pg_gate._drill_proofs(None, tmp_path / "artefato")
    assert reason in reasons


def test_gate_copy_proofs_notice_a_modified_source(tmp_path: Path, monkeypatch) -> None:
    _scripted_drills(monkeypatch, mutate_source=True)
    results, reasons = pg_gate._drill_proofs(None, tmp_path / "artefato")
    assert results["copy_source_untouched"] is False
    assert "copy_source_modified" in reasons


def test_gate_runs_no_copy_proof_without_a_passing_synthetic_drill(
    tmp_path: Path, monkeypatch
) -> None:
    calls = _scripted_drills(monkeypatch, {"drill": (1, {"verdict": "failed"})})
    _, reasons = pg_gate._drill_proofs(None, tmp_path / "artefato")
    assert reasons == ["restore_drill_not_passed"]
    assert [c["name"] for c in calls] == ["drill"]


def test_gate_removes_the_exported_copy(tmp_path: Path, any_work_root, monkeypatch) -> None:
    import argparse

    _scripted_drills(monkeypatch)
    (tmp_path / "work").mkdir()
    args = argparse.Namespace(work_root=tmp_path / "work")
    results, reasons = pg_gate._run_drills(args, "r-gate")
    assert (reasons, results["export_removed"]) == ([], True)
    assert list((tmp_path / "work").iterdir()) == []


def test_published_files_with_a_password_in_a_url_are_flagged(tmp_path: Path) -> None:
    report = tmp_path / "gate.json"
    (tmp_path / "gate-copy.log").write_text(
        "conectando em postgresql+psycopg://app:segredo-ficticio@127.0.0.1:5432/db", "utf-8"
    )
    (tmp_path / "gate-drill.log").write_text("postgresql+psycopg://app:***@127.0.0.1/db", "utf-8")
    (tmp_path / "gate-drill.json").write_text('{"verdict": "passed"}', "utf-8")
    (tmp_path / "outro.log").write_text("postgresql://app:segredo@127.0.0.1/db", "utf-8")
    assert pg_gate.published_credentials(report) == ["gate-copy.log"]
