"""Passo da OPS-2 no ``postgres-gate`` (``scripts/ops/offsite_gate.py``): as regras que
decidem aprovação rodam em qualquer bancada; a prova real é do CI Linux com PostgreSQL 18.
"""

from __future__ import annotations

import copy
import subprocess
import sys

import pytest

from tests.ops_support import REPO_ROOT

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
