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
        "--publish-dir",
        str(tmp_path / "liberados"),
    ]


def _gate_report(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "liberados" / pg_gate.GATE_REPORT).read_text(encoding="utf-8"))


@pytest.fixture
def fake_gate(monkeypatch, fake_pg):
    """Gate com ferramentas falsas: suíte "aprovada" e prova de restauração espiã, que
    deixa na área bruta os relatórios e logs que os ensaios reais deixariam — limpos,
    salvo o conteúdo dado em ``raw`` (nome do arquivo -> texto)."""
    drill_runs: list[str] = []

    def install(tools: FakeTools, raw: dict[str, str] | None = None) -> list[str]:
        fake_pg(tools)
        monkeypatch.setattr(pg_gate, "pg_binary", lambda pg_bin, name: Path(name))
        monkeypatch.setattr(pg_gate, "tool_version", lambda binary: ("18.0", 18))

        def prove(self) -> None:
            self.server_version, self.server_major = "18.0", 18

        monkeypatch.setattr(pgcluster.Cluster, "prove_identity", prove)
        monkeypatch.setattr(pg_gate, "_run_suite", lambda *args: [])

        def fake_drills(args, run_id):
            drill_runs.append("synthetic")
            for name in pg_gate.DRILLS:
                for file, clean in (
                    (f"pg-gate-report-{name}.json", json.dumps({"verdict": "passed"})),
                    (f"pg-gate-{name}.log", f"[drill] {name}: ok\n"),
                ):
                    text = (raw or {}).get(file, clean)
                    (args.raw_dir / file).write_text(text, encoding="utf-8")
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
    report = _gate_report(tmp_path)
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
    report = _gate_report(tmp_path)
    assert report["gate_cleanup"]["confirmed"] is True
    assert drill_runs == ["synthetic"]
    assert list((tmp_path / "work").iterdir()) == []  # cluster, cópia e área bruta


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
# Revisão final do PR #6: a exportação nunca altera um destino que já existe
# ---------------------------------------------------------------------------

STAMP = "20260101T000000Z"
EXPORTED = {f"backup-{STAMP}.dump": b"PGDMP-sintetico", f"backup-{STAMP}.json": b"{}"}


def _export_source(tmp_path: Path) -> Path:
    source = tmp_path / "artefato"
    source.mkdir()
    for name, data in EXPORTED.items():
        (source / name).write_bytes(data)
    return source


def _export(source: Path, destination: Path) -> str:
    import os

    previous = os.umask(0o022)  # o umask permissivo do operador
    try:
        return drill.export_copy(source, STAMP, destination)
    finally:
        os.umask(previous)


def _exported(destination: Path) -> dict[str, tuple[int, bytes]]:
    return {
        name: (_mode(destination / name), (destination / name).read_bytes()) for name in EXPORTED
    }


def _sentinel(directory: Path) -> tuple[int, int, bytes]:
    sentinel = directory / "sentinela.txt"
    return _mode(sentinel), sentinel.stat().st_mtime_ns, sentinel.read_bytes()


def _existing_dir(tmp_path: Path, name: str, mode: int) -> Path:
    directory = tmp_path / name
    directory.mkdir()
    (directory / "sentinela.txt").write_text("conteúdo de outra pessoa", encoding="utf-8")
    directory.chmod(mode)
    return directory


@posix_only
def test_export_destination_new_is_created_private_under_umask_022(tmp_path: Path) -> None:
    source = _export_source(tmp_path)
    destination = tmp_path / "pai-novo" / "copia"
    assert _export(source, destination) == "created"
    assert _mode(destination) == 0o700 and _mode(destination.parent) == 0o700
    assert _exported(destination) == {name: (0o600, data) for name, data in EXPORTED.items()}
    assert {p.name: p.read_bytes() for p in source.iterdir()} == EXPORTED  # origem intocada


def _octal(mode: int) -> str:
    return f"{mode:04o}"


@posix_only
@pytest.mark.parametrize("mode", [0o700, 0o750, 0o755], ids=_octal)
def test_export_destination_existing_keeps_its_mode_owner_and_content(
    tmp_path: Path, mode: int
) -> None:
    source = _export_source(tmp_path)
    existing = _existing_dir(tmp_path, "existente", mode)
    owner, sentinel = existing.stat().st_uid, _sentinel(existing)
    assert _export(source, existing) == "existing"
    assert (_mode(existing), existing.stat().st_uid) == (mode, owner)
    assert _sentinel(existing) == sentinel
    assert _exported(existing) == {name: (0o600, data) for name, data in EXPORTED.items()}


@posix_only
@pytest.mark.parametrize("mode", [0o775, 0o770, 0o777, 0o1777], ids=_octal)
def test_export_destination_shared_and_writable_by_others_is_refused_untouched(
    tmp_path: Path, mode: int
) -> None:
    source = _export_source(tmp_path)
    shared = _existing_dir(tmp_path, "compartilhado", mode)
    sentinel = _sentinel(shared)
    with pytest.raises(DrillRefused) as info:
        _export(source, shared)
    assert info.value.reason == "export_dir_writable_by_others"
    assert info.value.facts["mode"] == f"{mode:04o}"
    assert _mode(shared) == mode and _sentinel(shared) == sentinel
    assert sorted(p.name for p in shared.iterdir()) == ["sentinela.txt"]


@posix_only
def test_export_destination_symlink_is_refused_without_touching_its_target(
    tmp_path: Path,
) -> None:
    source = _export_source(tmp_path)
    target = _existing_dir(tmp_path, "alvo", 0o755)
    sentinel = _sentinel(target)
    link = tmp_path / "atalho"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(DrillRefused) as info:
        _export(source, link)
    assert info.value.reason == "export_dir_symlink"
    assert _mode(target) == 0o755 and _sentinel(target) == sentinel
    assert sorted(p.name for p in target.iterdir()) == ["sentinela.txt"]


@posix_only
def test_export_destination_never_overwrites(tmp_path: Path) -> None:
    source = _export_source(tmp_path)
    existing = _existing_dir(tmp_path, "existente", 0o700)
    (existing / f"backup-{STAMP}.json").write_text("anterior", encoding="utf-8")
    with pytest.raises(DrillRefused) as info:
        _export(source, existing)
    assert info.value.reason == "export_file_exists"
    assert (existing / f"backup-{STAMP}.json").read_text(encoding="utf-8") == "anterior"
    assert not (existing / f"backup-{STAMP}.dump").exists()  # nada pela metade


@posix_only
def test_export_destination_unfit_refuses_the_drill_before_any_cluster(
    tmp_path: Path, monkeypatch, capsys, any_work_root
) -> None:
    for name in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS"):
        monkeypatch.delenv(name, raising=False)
    shared = _existing_dir(tmp_path, "compartilhado", 0o777)
    assert drill.main(_drill_args(tmp_path, "--export-artifact", str(shared))) == 2
    capsys.readouterr()
    report = json.loads((tmp_path / "drill.json").read_text(encoding="utf-8"))
    assert (report["verdict"], report["reason"]) == ("refused", "export_dir_writable_by_others")
    assert report["cleanup"] == {"confirmed": True, "work_dir_created": False}
    assert list((tmp_path / "work").iterdir()) == []
    assert _mode(shared) == 0o777


def test_export_is_refused_where_isolation_is_unprovable(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(drill, "copy_mode_supported", lambda: False)
    for name in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS"):
        monkeypatch.delenv(name, raising=False)
    destination = tmp_path / "copia"
    assert drill.main(_drill_args(tmp_path, "--export-artifact", str(destination))) == 2
    capsys.readouterr()
    report = json.loads((tmp_path / "drill.json").read_text(encoding="utf-8"))
    assert (report["verdict"], report["reason"]) == ("refused", "export_unsupported_platform")
    assert not destination.exists() and list((tmp_path / "work").iterdir()) == []


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


# ---------------------------------------------------------------------------
# Revisão final do PR #6: o CI público só imprime e publica o que foi conferido
# ---------------------------------------------------------------------------

# Credencial fictícia: o valor nunca pode aparecer em stdout, stderr ou no que sobe.
LEAK = "segredo-ficticio-0b5e"
LEAK_URL = f"postgresql+psycopg://app:{LEAK}@127.0.0.1:5432/banco_ficticio"
FOUR_REPORTS = sorted(
    [pg_gate.GATE_REPORT, *(f"pg-gate-report-{name}.json" for name in pg_gate.DRILLS)]
)


@pytest.mark.parametrize(
    ("text", "known", "expected"),
    [
        (f"conectando em {LEAK_URL}", (), ["credential_in_url"]),
        ("postgresql+psycopg://app:***@127.0.0.1/db", (), []),
        ('url = f"postgresql+psycopg://app:{secret}@127.0.0.1/db"', (), []),
        ('{"detalhe": "x", "password": "' + LEAK + '"}', (), ["secret_field"]),
        ('{"password": "***"}', (), []),
        # Só o cabeçalho, montado em partes: nenhum material de chave no repositório.
        ("-----BEGIN OPENSSH " + "PRIVATE KEY-----", (), ["private_key"]),
        (f"senha impressa: {LEAK}", (LEAK,), ["generated_secret"]),
        ('{"verdict": "passed", "reason": "ok", "--no-password": 1}', (), []),
    ],
)
def test_credential_categories_name_the_category_never_the_value(text, known, expected) -> None:
    assert pg_gate.credential_categories(text, known) == expected


def test_clean_gate_prints_its_logs_and_releases_the_four_reports(
    tmp_path: Path, any_work_root, fake_gate, capsys
) -> None:
    fake_gate(FakeTools(status={"gate": 3}))
    assert pg_gate.main(_gate_args(tmp_path)) == 0
    out = capsys.readouterr().out
    assert all(f"----- {name} -----" in out for name in pg_gate.DRILLS)  # depois de conferidos
    paths, problems = pg_gate.released_files(tmp_path / "liberados")
    assert (problems, sorted(p.name for p in paths)) == ([], FOUR_REPORTS)
    publication = _gate_report(tmp_path)["publication"]
    assert (publication["withheld"], publication["raw_area_removed"]) == ([], True)
    assert list((tmp_path / "work").iterdir()) == []  # área bruta removida


@pytest.mark.parametrize(
    ("raw_file", "content", "printed"),
    [
        ("pg-gate-copy.log", f"[drill] conectando em {LEAK_URL}\n", False),
        ("pg-gate-report-copy.json", json.dumps({"verdict": "passed", "url": LEAK_URL}), True),
    ],
)
def test_credential_in_raw_output_fails_the_gate_and_never_leaves_it(
    tmp_path: Path, any_work_root, fake_gate, capsys, raw_file, content, printed
) -> None:
    fake_gate(FakeTools(status={"gate": 3}), {raw_file: content})
    code = pg_gate.main(_gate_args(tmp_path))
    captured = capsys.readouterr()
    assert code == 1
    assert LEAK not in captured.out + captured.err
    assert "credential_in_url" in captured.err  # diagnóstico mínimo: só a categoria
    assert ("----- copy -----" in captured.out) is printed  # log com credencial não sai

    report = _gate_report(tmp_path)
    assert (report["verdict"], report["reasons"]) == ("failed", ["credential_in_output"])
    assert report["publication"]["withheld"] == [
        {"file": raw_file, "categories": ["credential_in_url"]}
    ]
    publish = tmp_path / "liberados"
    paths, problems = pg_gate.released_files(publish)
    assert problems == [] and raw_file not in {p.name for p in paths}
    assert all(LEAK not in p.read_text(encoding="utf-8") for p in publish.iterdir())
    assert list((tmp_path / "work").iterdir()) == []  # o bruto não sobrevive ao gate


def test_selection_takes_only_files_listed_in_the_release_manifest(tmp_path: Path) -> None:
    publish = tmp_path / "liberados"
    publish.mkdir()
    (publish / pg_gate.GATE_REPORT).write_text('{"verdict": "passed"}', encoding="utf-8")
    pg_gate._write_release(publish, "r-1", [pg_gate.GATE_REPORT])
    # Fora da lista: arquivo bruto ou antigo dentro da área liberada e no diretório temporário.
    (publish / "pg-gate-report-copy.json").write_text(LEAK_URL, encoding="utf-8")
    (tmp_path / "pg-gate-report-velho.json").write_text(LEAK_URL, encoding="utf-8")

    paths, problems = pg_gate.released_files(publish)
    assert (problems, paths) == ([], [publish / pg_gate.GATE_REPORT])
    output = tmp_path / "github_output"
    assert pg_gate.main(["--list-released", str(publish), "--github-output", str(output)]) == 0
    block = output.read_text(encoding="utf-8").splitlines()
    assert block[0].startswith("paths<<") and block[-1] == block[0].removeprefix("paths<<")
    assert block[1:-1] == [str(publish / pg_gate.GATE_REPORT)]


@pytest.mark.parametrize(
    ("tamper", "problem"),
    [
        ("modify", "released_file_modified"),
        ("remove", "released_file_missing"),
        ("leak", "credential_in_released_file"),
        ("no_manifest", "release_manifest_missing"),
    ],
)
def test_selection_publishes_nothing_when_the_release_does_not_hold(
    tmp_path: Path, tamper: str, problem: str, capsys
) -> None:
    publish = tmp_path / "liberados"
    publish.mkdir()
    report = publish / pg_gate.GATE_REPORT
    report.write_text('{"verdict": "passed"}', encoding="utf-8")
    pg_gate._write_release(publish, "r-1", [pg_gate.GATE_REPORT])
    if tamper == "modify":
        report.write_text('{"verdict": "failed"}', encoding="utf-8")
    elif tamper == "remove":
        report.unlink()
    elif tamper == "leak":
        report.write_text(LEAK_URL, encoding="utf-8")
        pg_gate._write_release(publish, "r-1", [pg_gate.GATE_REPORT])  # hash "coerente"
    else:
        (publish / pg_gate.RELEASE_MANIFEST).unlink()
    assert pg_gate.released_files(publish) == ([], [problem])
    output = tmp_path / "github_output"
    assert pg_gate.main(["--list-released", str(publish), "--github-output", str(output)]) == 1
    assert not output.exists()
    assert LEAK not in capsys.readouterr().err


def test_publish_dir_of_another_run_is_never_reused(
    tmp_path: Path, any_work_root, fake_gate, capsys
) -> None:
    drill_runs = fake_gate(FakeTools(status={"gate": 3}))
    publish = tmp_path / "liberados"
    publish.mkdir()
    (publish / "pg-gate-report.json").write_text('{"verdict": "antigo"}', encoding="utf-8")
    assert pg_gate.main(_gate_args(tmp_path)) == 1
    assert json.loads(capsys.readouterr().out)["reasons"] == ["publish_dir_exists"]
    assert drill_runs == [] and list((tmp_path / "work").iterdir()) == []
    assert sorted(p.name for p in publish.iterdir()) == ["pg-gate-report.json"]


# ---------------------------------------------------------------------------
# OPS-3 (S3): registro conhecido inexistente é record_mismatch, não erro operacional
# ---------------------------------------------------------------------------

KNOWN_CODE = "DRILL-CONHECIDO"
_ABSENT_BODY = '{"detail": "Achado de auditoria 1 não encontrado."}'.encode()
# Resposta da API do destino ao GET do achado conhecido: (status, corpo).
_API_ANSWERS: dict[str, tuple[int, bytes]] = {
    "match": (200, json.dumps({"id": 1, "finding_code": KNOWN_CODE}).encode()),
    "different": (200, json.dumps({"id": 1, "finding_code": "OUTRO"}).encode()),
    "absent": (404, _ABSENT_BODY),
    "route_missing": (404, b'{"detail": "Not Found"}'),
    "unauthorized": (401, b'{"detail": "Not authenticated"}'),
    "server_error": (500, b'{"detail": "Erro interno do servidor."}'),
    "invalid_json": (200, b"<html>proxy</html>"),
    "not_an_object": (200, b"[]"),
}


def _fake_api(case: str) -> type:
    """A instância da API do destino sem subir processo: o cliente HTTP do ensaio é o real,
    e só o transporte responde o caso dado."""
    import io
    import urllib.error

    class Opener:
        def open(self, request, timeout):
            if case == "unreachable":
                raise urllib.error.URLError(ConnectionRefusedError(111, "recusada"))
            status, body = _API_ANSWERS[case]
            if status != 200:
                raise urllib.error.HTTPError(request.full_url, status, "x", None, io.BytesIO(body))
            return io.BytesIO(body)

    class FakeApi(drill.ApiProcess):
        def __enter__(self):
            self._opener = Opener()
            return self

        def __exit__(self, *exc):
            return None

    return FakeApi


@pytest.fixture
def copy_drill(tmp_path, monkeypatch, fake_pg, any_work_root):
    """Ensaio no modo cópia, de ponta a ponta, sem PostgreSQL: clusters, ferramentas e
    banco simulados; a cópia, a avaliação dela, a limpeza e o cliente HTTP são os reais."""
    from datetime import UTC, datetime, timedelta

    from app.ops.checks import release_heads
    from tests.ops_support import write_publication

    fake_pg(FakeTools())
    heads, _ = release_heads(drill.REPO_ROOT)

    def alembic(ctx, url, *args):
        return "No new upgrade operations detected." if args[0] == "check" else " ".join(heads)

    def observe(cluster, dbname):
        marker = f"cartorio-ops-drill:{cluster.run_id}:destino"
        return {"comment": marker, "owner": drill.APP_ROLE, "user_relations": 0}

    def prove(self):
        self.server_version, self.server_major = "18.0", 18

    monkeypatch.setattr(drill, "copy_mode_supported", lambda platform=sys.platform: True)
    monkeypatch.setattr(drill, "pg_binary", lambda pg_bin, name: Path(name))
    monkeypatch.setattr(drill, "tool_version", lambda binary: ("18.0", 18))
    monkeypatch.setattr(drill, "_list_archive", lambda ctx, artifact: (7, None))
    monkeypatch.setattr(drill, "_create_app_database", lambda *args: None)
    monkeypatch.setattr(drill, "_observe_target", observe)
    monkeypatch.setattr(drill, "_pg_restore", lambda *args: None)
    monkeypatch.setattr(drill, "_alembic", alembic)
    monkeypatch.setattr(pgcluster.Cluster, "prove_identity", prove)
    for name in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS"):
        monkeypatch.delenv(name, raising=False)
    _, manifest = write_publication(tmp_path / "copia", datetime.now(UTC) - timedelta(hours=1))

    def run_case(case: str) -> tuple[int, dict]:
        monkeypatch.setattr(drill, "ApiProcess", _fake_api(case))
        argv = _drill_args(
            tmp_path,
            "--from-manifest",
            str(manifest),
            "--expect-finding-id",
            "1",
            "--expect-finding-code",
            KNOWN_CODE,
            "--expect-database",
            "cartorio_lab",
        )
        code = drill.main(argv)
        return code, json.loads((tmp_path / "drill.json").read_text(encoding="utf-8"))

    return run_case


@pytest.mark.parametrize(
    ("case", "expected", "failure"),
    [
        ("match", (0, "passed", "ok"), None),
        ("absent", (1, "failed", "record_mismatch"), {"record": "absent"}),
        ("different", (1, "failed", "record_mismatch"), {"record": "different"}),
        ("route_missing", (1, "failed", "unexpected_error"), {"error_class": "HTTPError"}),
        ("unauthorized", (1, "failed", "unexpected_error"), {"error_class": "HTTPError"}),
        ("server_error", (1, "failed", "unexpected_error"), {"error_class": "HTTPError"}),
        ("unreachable", (1, "failed", "unexpected_error"), {"error_class": "URLError"}),
        ("invalid_json", (1, "failed", "unexpected_error"), {"error_class": "JSONDecodeError"}),
        ("not_an_object", (1, "failed", "api_unexpected_body"), None),
    ],
)
def test_known_record_answer_is_classified_and_the_area_is_always_cleaned(
    copy_drill, capsys, case, expected, failure
) -> None:
    """S3 (sonda P8b): só o 404 da própria aplicação vira ``record_mismatch``
    (``record=absent``). Rota inexistente, autenticação, 5xx, conexão e corpo inválido
    continuam o que eram. Em todos os casos o destino para e a área sai."""
    code, report = copy_drill(case)
    capsys.readouterr()

    assert (code, report["verdict"], report["reason"]) == expected
    assert report.get("failure") == failure
    assert report["cleanup"]["clusters"] == {"destino": "stopped"}
    assert (report["cleanup"]["confirmed"], report["cleanup"]["work_dir_removed"]) == (True, True)


def test_absent_record_is_told_apart_from_a_missing_route_on_the_real_app(
    tmp_path: Path, any_work_root
) -> None:
    """S3: a API real (SQLite) responde 404 ao achado inexistente com o ``detail`` da
    aplicação, e 404 à rota inexistente com o ``detail`` do roteador. Só o primeiro prova
    a ausência do registro — e este teste quebra se um dos dois mudar de forma."""
    import os
    import urllib.error

    from tests.ops_support import migrate_sqlite

    url = migrate_sqlite(tmp_path / "api.db")
    ctx = drill.Ctx(
        run_id="api-404",
        pg_bin=tmp_path,
        work=create_work_dir(tmp_path, "api-404"),
        clock=lambda: None,
        base_env=pgcluster.subprocess_env(os.environ),
    )
    with drill.ApiProcess(ctx, url, "Cartorio System - ensaio 404", "x") as api:
        assert drill._fetch_record(api, 999_999) is None
        with pytest.raises(urllib.error.HTTPError) as missing_route:
            api.request("GET", "/audit/rota-que-nao-existe/1")
    assert missing_route.value.code == 404
    assert drill._application_not_found(missing_route.value) is False


# ---------------------------------------------------------------------------
# OPS-3 (S6): filhos auxiliares (versão das ferramentas, release) com ambiente filtrado
# ---------------------------------------------------------------------------

LIBPQ_VARIABLES = (
    "PGHOST",
    "PGHOSTADDR",
    "PGPORT",
    "PGDATABASE",
    "PGUSER",
    "PGPASSWORD",
    "PGPASSFILE",
    "PGSERVICE",
    "PGSERVICEFILE",
    "PGOPTIONS",
    "PGSSLMODE",
    "PGTARGETSESSIONATTRS",
)


@pytest.fixture
def inherited_libpq(monkeypatch) -> dict[str, str]:
    """Todas as variáveis de conexão da libpq, e a DSN da aplicação, herdadas."""
    import os

    for name in LIBPQ_VARIABLES:
        monkeypatch.setenv(name, "herdado")
    monkeypatch.setenv("DATABASE_URL", "postgresql://herdado@db.invalid/x")
    return dict(os.environ)


def _version_probe(tmp_path: Path) -> Path:
    """Executável que diz versão 18 só se não enxergar nenhuma variável de conexão."""
    import os

    names = (*LIBPQ_VARIABLES, "DATABASE_URL")
    if os.name == "nt":
        probe = tmp_path / "pg_probe.cmd"
        lines = ["@echo off", *[f"if defined {name} goto herdou" for name in names]]
        lines += ["echo probe (PostgreSQL) 18.0", "exit /b 0", ":herdou"]
        lines += ["echo probe (PostgreSQL) 99.0"]
        probe.write_text("\r\n".join(lines) + "\r\n", encoding="ascii")
    else:
        seen = "".join("${" + name + "}" for name in names)
        probe = tmp_path / "pg_probe"
        probe.write_text(
            f'#!/bin/sh\nif [ -n "{seen}" ]; then echo "probe (PostgreSQL) 99.0"; '
            'else echo "probe (PostgreSQL) 18.0"; fi\n',
            encoding="ascii",
        )
        probe.chmod(0o755)
    return probe


def test_tool_version_child_never_sees_inherited_connection_variables(
    tmp_path: Path, inherited_libpq
) -> None:
    import os

    probe = _version_probe(tmp_path)
    before = dict(os.environ)
    assert {name: before[name] for name in LIBPQ_VARIABLES} == {
        name: inherited_libpq[name] for name in LIBPQ_VARIABLES
    }

    assert pgcluster.tool_version(probe) == ("18.0", 18)
    assert dict(os.environ) == before  # o ambiente do próprio processo não muda


def test_tool_version_and_release_children_get_only_the_filtered_environment(
    monkeypatch, inherited_libpq
) -> None:
    import os
    import subprocess

    monkeypatch.setenv("GIT_DIR", "/outro/repositorio/.git")
    monkeypatch.setenv("GIT_WORK_TREE", "/outro/repositorio")
    monkeypatch.setenv("GIT_INDEX_FILE", "/outro/repositorio/.git/index")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/config/com/safe-directory")
    seen: list[dict[str, str] | None] = []

    def capture(cmd, **kwargs):
        seen.append(kwargs.get("env"))
        return subprocess.CompletedProcess(cmd, 0, stdout="x (PostgreSQL) 18.6\n", stderr="")

    monkeypatch.setattr(subprocess, "run", capture)
    pgcluster.tool_version(Path("pg_ctl"))
    drill._git_release()

    assert len(seen) == 3 and all(env is not None for env in seen)
    for env in seen:
        assert not [key for key in env if key.upper().startswith("PG")]
        assert "DATABASE_URL" not in env
        assert env.get("PATH") == os.environ.get("PATH")
    tool_env, *git_envs = seen
    assert "GIT_DIR" in tool_env  # o filtro de GIT_* é só do git, que identifica a release
    for env in git_envs:
        assert not {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"} & set(env)
        # Configuração do git (safe.directory de quem roda num checkout alheio) continua.
        assert env.get("GIT_CONFIG_GLOBAL") == "/config/com/safe-directory"


def test_release_without_an_answer_from_git_is_unknown_not_clean(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(drill, "REPO_ROOT", tmp_path)  # fora de qualquer checkout
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))

    assert drill._git_release() == {"git_sha": None, "worktree_dirty": None}


def test_release_identity_is_the_checkout_even_with_git_dir_inherited(
    tmp_path: Path, monkeypatch, inherited_libpq
) -> None:
    """S6: ``GIT_DIR``/``GIT_WORK_TREE`` herdados (de um hook, por exemplo) fariam o
    relatório citar o SHA de outro repositório."""
    import os
    import subprocess

    plain = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    other = tmp_path / "outro"
    identity = ["-c", "user.name=ensaio", "-c", "user.email=ensaio@example.invalid"]
    subprocess.run(["git", "init", "-q", str(other)], env=plain, check=True)
    subprocess.run(
        ["git", "-C", str(other), *identity, "commit", "-q", "--allow-empty", "-m", "x"],
        env=plain,
        check=True,
    )
    expected = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=drill.REPO_ROOT,
        env=plain,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(other))

    assert drill._git_release()["git_sha"] == expected
