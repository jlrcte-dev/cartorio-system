"""Passo da OPS-2 no ``postgres-gate`` (``scripts/ops/offsite_gate.py``): as regras que
decidem aprovação rodam em qualquer bancada; a prova real é do CI Linux com PostgreSQL 18.
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.ops import pgcluster
from app.ops.pgcluster import IDENTITY_FILE, WORK_MARKER, create_work_dir, private_write
from tests.ops_support import REPO_ROOT
from tests.test_ops_drill import FakeTools

sys.path.insert(0, str(REPO_ROOT / "scripts" / "ops"))
import offsite_gate  # noqa: E402

HEALTHY = {
    "export": {"verdict": "passed"},
    "import": {
        "verdict": "published",
        "sha256_matches_export": True,
        "modes": {"destination": "0700", "generation": "0700", "files": "0600"},
    },
    "observer_healthy": {"overall": "ok"},
    "observer_signal_lost": {
        "overall": "fail",
        "application_signal": "signal_missing",
        "offsite_copy": "copy_fresh",
        "last_valid_copy_is_the_import": True,
    },
    "origin_removed_before_restore": True,
    "restore": {
        name: True
        for name in (
            "verdict_passed",
            "same_sha256",
            "digest_verified",
            "database_matched",
            "distinct_cluster",
            "alembic_compatible",
            "api_read",
            "cleanup_confirmed",
            "generation_untouched",
        )
    },
    "work_cleanup": {
        "drills": {"ensaio-sintetico": "confirmed", "restauracao-do-destino": "confirmed"},
        "leftover_clusters": {"stopped": 0, "not_started": 0, "uncertain": 0},
        "work_preserved": False,
    },
    "work_removed": True,
}
OK_TOTALS = {"tests": 13, "failures": 0, "errors": 0, "skipped": 0, "exit_code": 0}
PASSED = [f"tests/test_ops_offsite.py::caso_{n}" for n in range(13)]


def test_posix_selection_collects_exactly_the_13_posix_cases():
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "--collect-only", "-q"]
        + [*offsite_gate.POSIX_FILES, "-k", offsite_gate.POSIX_SELECTION],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    ids = [line for line in done.stdout.splitlines() if "::" in line]
    assert len(ids) == offsite_gate.POSIX_EXPECTED == 13, done.stdout
    assert all(offsite_gate._PASSED.match(f"PASSED {node}") for node in ids)


def test_posix_proof_passes_only_with_13_named_passes_and_no_skip():
    assert offsite_gate.posix_reasons(OK_TOTALS, PASSED) == []
    skipped = OK_TOTALS | {"skipped": 2}
    assert "mandatory_proof_skipped" in offsite_gate.posix_reasons(skipped, PASSED[:11])
    assert "posix_tests_not_all_passed" in offsite_gate.posix_reasons(skipped, PASSED[:11])
    assert offsite_gate.posix_reasons(OK_TOTALS | {"tests": 12}, PASSED[:12]) == [
        "posix_tests_not_all_passed"
    ]
    assert "tests_failed" in offsite_gate.posix_reasons(OK_TOTALS | {"failures": 1}, PASSED)


def test_complete_end_to_end_facts_pass():
    assert offsite_gate.e2e_reasons(HEALTHY) == []


@pytest.mark.parametrize(
    ("path", "value", "reason"),
    [
        (("export", "verdict"), "failed", "export_not_passed"),
        (("import", "sha256_matches_export"), False, "import_not_verified"),
        (("import", "modes"), {"destination": "0755"}, "import_not_private"),
        (("observer_healthy", "overall"), "fail", "observer_not_ok_with_signal"),
        (
            ("observer_signal_lost", "application_signal"),
            "signal_fresh",
            "signal_loss_not_detected",
        ),
        (("observer_signal_lost", "offsite_copy"), "copy_missing", "signal_loss_not_detected"),
        (
            ("observer_signal_lost", "last_valid_copy_is_the_import"),
            False,
            "last_valid_copy_not_kept",
        ),
        (("origin_removed_before_restore",), False, "origin_still_present"),
        (("restore", "same_sha256"), False, "restore_same_sha256"),
        (("restore", "distinct_cluster"), False, "restore_distinct_cluster"),
        (("restore", "alembic_compatible"), False, "restore_alembic_compatible"),
        (("restore", "api_read"), False, "restore_api_read"),
        (("restore", "cleanup_confirmed"), False, "restore_cleanup_confirmed"),
        (("restore", "generation_untouched"), False, "restore_generation_untouched"),
        (("work_removed",), False, "work_not_removed"),
        (
            ("work_cleanup", "drills", "restauracao-do-destino"),
            "timeout",
            "drill_cleanup_unconfirmed",
        ),
        (("work_cleanup", "drills"), {}, "drill_cleanup_unconfirmed"),
        (("work_cleanup", "work_preserved"), True, "work_preserved_cluster_stop_unconfirmed"),
    ],
)
def test_each_missing_proof_fails_with_its_own_reason(path, value, reason):
    facts = copy.deepcopy(HEALTHY)
    target = facts
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    assert offsite_gate.e2e_reasons(facts) == [reason]


def test_a_proof_that_never_ran_is_a_failure_not_a_pass():
    reasons = offsite_gate.e2e_reasons({"export": {"verdict": "failed"}})
    assert "export_not_passed" in reasons and "restore_verdict_passed" in reasons


def test_summary_with_a_credential_is_withheld_and_a_clean_one_is_released():
    leak = {"end_to_end": {"nota": "postgresql://app:segredo-ficticio-77@127.0.0.1/x"}}
    text, found = offsite_gate.released_summary(leak)
    assert (text, found) == (None, ["credential_in_url"])
    text, found = offsite_gate.released_summary({"verdict": "passed", "reasons": []})
    assert found == [] and '"verdict": "passed"' in text


SHA = "a" * 64
SYNTHETIC = {
    "release": {"alembic_heads": ["f4a5b6c7d8e9"]},
    "origin": {"system_identifier": "111"},
    "destination": {"system_identifier": "222"},
    "cleanup": {"confirmed": True},
}
RESTORED = {
    "verdict": "passed",
    "artifact": {"sha256": SHA, "verifier_evaluation": "digest_verified", "database_matched": True},
    "destination": {
        "system_identifier": "333",
        "alembic_revisions": ["f4a5b6c7d8e9"],
        "alembic_check": "no_drift",
        "api_app_name_confirmed": True,
    },
    "record": {"matched_on_destination": True},
    "cleanup": {"confirmed": True},
}


def test_restore_from_the_destination_with_healthy_reports_proves_every_check():
    facts = offsite_gate.restore_facts(0, SYNTHETIC, RESTORED, SHA)
    checks = [name for name in offsite_gate.RESTORE_CHECKS if name != "generation_untouched"]
    assert all(facts[name] is True for name in checks)


@pytest.mark.parametrize(
    ("section", "field", "value", "check"),
    [
        ("destination", "system_identifier", "111", "distinct_cluster"),
        ("destination", "system_identifier", None, "distinct_cluster"),
        ("destination", "alembic_check", "drift", "alembic_compatible"),
        ("artifact", "sha256", "b" * 64, "same_sha256"),
        ("cleanup", "confirmed", False, "cleanup_confirmed"),
        ("record", "matched_on_destination", False, "api_read"),
    ],
)
def test_restore_check_fails_on_its_own_evidence(section, field, value, check):
    restored = copy.deepcopy(RESTORED)
    restored[section][field] = value
    assert offsite_gate.restore_facts(0, SYNTHETIC, restored, SHA)[check] is False


def test_restore_without_an_exported_digest_never_matches():
    assert offsite_gate.restore_facts(0, SYNTHETIC, {}, None)["same_sha256"] is False


def test_workflow_runs_ops2_after_the_ops1_publication_without_touching_the_gate():
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    upload = workflow.index("Publicar relatórios liberados (sem segredos)")
    step = workflow.index("OPS-2: cópia fora do host (POSIX + ponta a ponta)")
    assert upload < step
    assert "python scripts/ops/offsite_gate.py" in workflow[step:]
    assert '--publish-dir "$RUNNER_TEMP/pg-gate-liberados"' in workflow[:upload]


# --- Limpeza da área do passo: os ensaios filhos vivem DENTRO dela -------------------


@pytest.fixture
def any_work_root(monkeypatch):
    """O tmp_path desta máquina pode ser não-ASCII; a recusa disso é testada à parte."""
    monkeypatch.setattr(pgcluster, "ansi_safe", lambda path: True)


@pytest.fixture
def fake_pg(monkeypatch):
    """``pg_ctl`` simulado pelo mesmo ``FakeTools`` dos testes do ensaio: a parada e a
    confirmação por ``pg_ctl status`` são as do ``Cluster`` real."""

    def install(tools: FakeTools) -> FakeTools:
        monkeypatch.setattr(pgcluster, "run_tool", tools)
        monkeypatch.setattr(pgcluster, "pg_binary", lambda pg_bin, name: Path(name))
        return tools

    return install


def _child_area(work: Path, run_id: str, label: str = "destino", *, started: bool = True):
    """Área de um ensaio filho como o ``app.ops.drill`` a deixa: marcador da execução e
    ``<rótulo>/data`` com o token de identidade gravado antes de qualquer partida."""
    area = create_work_dir(work, run_id)
    data = area / label / "data"
    data.mkdir(parents=True)
    if started:
        private_write(data / IDENTITY_FILE, b"token-ficticio")
    return area


def _gate(tmp_path, monkeypatch, end_to_end):
    root = tmp_path / "raiz"
    root.mkdir()
    monkeypatch.setattr(offsite_gate, "_posix", lambda raw: ({"tests": 13, "passed": PASSED}, []))
    monkeypatch.setattr(offsite_gate, "_end_to_end", end_to_end)
    args = argparse.Namespace(pg_bin=tmp_path / "bin", work_root=root)
    return args, lambda: offsite_gate._gate(args)


def _summary(out: str) -> dict:
    return json.loads(out[: out.rindex("}") + 1])


def _healthy_e2e() -> dict:
    return copy.deepcopy({k: v for k, v in HEALTHY.items() if k != "work_cleanup"})


def test_inconclusive_child_stop_preserves_the_nested_area_and_fails(
    tmp_path, monkeypatch, capsys, any_work_root, fake_pg
):
    """O filho não confirmou a parada e preservou a área dele (aninhada): o pai tenta
    parar, a confirmação segue incerta, e nada é removido."""
    tools = fake_pg(FakeTools(stop={"destino": 1}, status={"destino": 0}))
    seen = {}

    def end_to_end(args, raw):
        seen["child"] = _child_area(args.work, "filho-inconclusivo")
        args.drills["restauracao-do-destino"] = "unconfirmed"
        return _healthy_e2e()

    args, run = _gate(tmp_path, monkeypatch, end_to_end)
    assert run() == 1

    captured = capsys.readouterr()
    child = seen["child"]
    assert args.work.exists() and (args.work / WORK_MARKER).is_file()
    assert (child / WORK_MARKER).is_file()
    assert (child / "destino" / "data" / IDENTITY_FILE).read_bytes() == b"token-ficticio"
    assert ("stop", "destino") in tools.calls and ("status", "destino") in tools.calls
    summary = _summary(captured.out)
    assert summary["verdict"] == "failed"
    assert {"drill_cleanup_unconfirmed", "work_preserved_cluster_stop_unconfirmed"} <= set(
        summary["reasons"]
    )
    assert summary["end_to_end"]["work_cleanup"]["leftover_clusters"] == {
        "stopped": 0,
        "not_started": 0,
        "uncertain": 1,
    }
    assert summary["end_to_end"]["work_removed"] is False
    assert "cluster possivelmente ativo" in captured.err
    for text in (captured.out, captured.err):
        assert str(tmp_path) not in text and "filho-inconclusivo" not in text


@pytest.mark.parametrize(("status", "removed"), [(3, True), (0, False)], ids=["parado", "incerto"])
def test_interruption_mid_drill_handles_the_leftover_cluster_before_removing(
    tmp_path, monkeypatch, capsys, any_work_root, fake_pg, status, removed
):
    """Interrupção com o ensaio ainda em curso: o registro anterior à execução faz o pai
    tratar o cluster que pode ter ficado antes de remover a área."""
    tools = fake_pg(FakeTools(status={"origem": status}))

    def end_to_end(args, raw):
        args.drills["ensaio-sintetico"] = "running"
        _child_area(args.work, "filho-interrompido", "origem")
        raise KeyboardInterrupt

    args, run = _gate(tmp_path, monkeypatch, end_to_end)
    with pytest.raises(KeyboardInterrupt):
        run()

    assert ("status", "origem") in tools.calls
    assert args.work.exists() is not removed
    assert ("cluster possivelmente ativo" in capsys.readouterr().err) is not removed


def test_missing_report_from_a_drill_sweeps_its_clusters_before_removal(
    tmp_path, monkeypatch, capsys, any_work_root, fake_pg
):
    """Ensaio filho real (``_drill``) que morre sem relatório depois de subir um cluster:
    o pai para e confirma, e só então remove."""
    tools = fake_pg(FakeTools(status={"destino": 3}))

    def drill_without_report(cmd, *, env, log, timeout):
        work_root = Path(cmd[cmd.index("--work-root") + 1])
        _child_area(work_root, "filho-sem-relatorio")
        return subprocess.CompletedProcess(cmd, -9)

    monkeypatch.setattr(offsite_gate, "run_tool", drill_without_report)

    def end_to_end(args, raw):
        code, report = offsite_gate._drill(args, raw, "ensaio-sintetico")
        assert (code, report) == (-9, {})
        return {"export": {"exit_code": code, "verdict": None}}

    args, run = _gate(tmp_path, monkeypatch, end_to_end)
    assert run() == 1

    summary = _summary(capsys.readouterr().out)
    cleanup = summary["end_to_end"]["work_cleanup"]
    assert cleanup["drills"] == {"ensaio-sintetico": "no_report"}
    assert cleanup["leftover_clusters"] == {"stopped": 1, "not_started": 0, "uncertain": 0}
    assert ("stop", "destino") in tools.calls and ("status", "destino") in tools.calls
    assert not args.work.exists() and summary["end_to_end"]["work_removed"] is True
    assert "drill_cleanup_unconfirmed" in summary["reasons"]
    assert "work_preserved_cluster_stop_unconfirmed" not in summary["reasons"]


def test_healthy_drills_remove_the_area_without_touching_any_cluster(
    tmp_path, monkeypatch, capsys, any_work_root, fake_pg
):
    tools = fake_pg(FakeTools())

    def end_to_end(args, raw):
        args.drills.update({"ensaio-sintetico": "confirmed", "restauracao-do-destino": "confirmed"})
        return _healthy_e2e()

    args, run = _gate(tmp_path, monkeypatch, end_to_end)
    assert run() == 0

    summary = _summary(capsys.readouterr().out)
    assert (summary["verdict"], summary["reasons"]) == ("passed", [])
    assert summary["end_to_end"]["work_cleanup"]["leftover_clusters"] == {
        "stopped": 0,
        "not_started": 0,
        "uncertain": 0,
    }
    assert not args.work.exists() and tools.calls == []


def test_area_left_on_disk_is_swept_even_if_every_drill_reported_confirmed(
    tmp_path, monkeypatch, capsys, any_work_root, fake_pg
):
    """Quem decide é o disco, não só o relatório: área de ensaio que ficou é tratada
    mesmo com todos os relatórios dizendo que a limpeza foi confirmada."""
    tools = fake_pg(FakeTools(stop={"destino": 1}, status={"destino": 0}))

    def end_to_end(args, raw):
        args.drills.update({"ensaio-sintetico": "confirmed", "restauracao-do-destino": "confirmed"})
        _child_area(args.work, "filho-nao-registrado")
        return _healthy_e2e()

    args, run = _gate(tmp_path, monkeypatch, end_to_end)
    assert run() == 1

    summary = _summary(capsys.readouterr().out)
    assert summary["reasons"] == ["work_preserved_cluster_stop_unconfirmed", "work_not_removed"]
    assert args.work.exists() and ("status", "destino") in tools.calls


def test_cluster_that_never_started_needs_no_stop(tmp_path, any_work_root, fake_pg):
    tools = fake_pg(FakeTools())
    work = create_work_dir(tmp_path, "passo")
    _child_area(work, "filho-sem-partida", started=False)
    counts = offsite_gate.stop_leftover_clusters(work, tmp_path)
    assert counts == {"stopped": 0, "not_started": 1, "uncertain": 0}
    assert tools.calls == []


@pytest.mark.parametrize(
    ("outcome", "state"),
    [
        ("timeout", "timeout"),
        ("sem_relatorio", "no_report"),
        ({"cleanup": {"confirmed": False, "kept": "cluster_stop_unconfirmed"}}, "unconfirmed"),
        ({"verdict": "failed"}, "no_report"),
        ({"cleanup": {"confirmed": True}}, "confirmed"),
    ],
)
def test_drill_records_what_the_parent_knows_about_its_cleanup(
    tmp_path, monkeypatch, outcome, state
):
    def fake_run(cmd, *, env, log, timeout):
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(cmd, timeout)
        if isinstance(outcome, dict):
            Path(cmd[cmd.index("--report") + 1]).write_text(json.dumps(outcome), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(offsite_gate, "run_tool", fake_run)
    args = argparse.Namespace(pg_bin=tmp_path, work=tmp_path, drills={})
    offsite_gate._drill(args, tmp_path, "ensaio")
    assert args.drills == {"ensaio": state}
