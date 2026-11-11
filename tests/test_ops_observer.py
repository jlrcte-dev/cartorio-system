"""Piloto OPS-2 — observador fora do host (``app.ops.observer``).

Roda em qualquer bancada: só lê o relatório do verificador e as gerações da cópia, e
nunca acessa banco.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta

import pytest

from app.ops import observer, offsite
from app.ops.report import CheckResult, Status, build_report, write_json_atomic
from tests.ops_support import (
    CONTENT,
    NOW,
    REPO_ROOT,
    clean_env,
    fixed_clock,
    stamp_of,
    write_publication,
)

DB = "cartorio_lab"
SIGNAL_AGE = timedelta(minutes=45)
COPY_AGE = timedelta(hours=26)
RECENT = NOW - timedelta(hours=2)
POSIX_ONLY = pytest.mark.skipif(os.name != "posix", reason="links simbólicos: CI Linux")


def healthy_checks() -> list[CheckResult]:
    return [CheckResult(name, Status.OK, "ok") for name in ("alembic", "api", "backup", "database")]


def write_signal(path, generated_at, checks=None):
    write_json_atomic(path, build_report(checks or healthy_checks(), generated_at))
    return path


def publish(copies, moment, **kwargs):
    folder = copies / offsite.GENERATIONS / stamp_of(moment)
    write_publication(folder, moment, **kwargs)
    return folder


def look(signal_path, copies, **kwargs):
    kwargs.setdefault("now", NOW)
    kwargs.setdefault("signal_max_age", SIGNAL_AGE)
    kwargs.setdefault("copy_max_age", COPY_AGE)
    expected = kwargs.pop("expected", DB)
    return observer.observe(signal_path, copies, expected, **kwargs)


def summary(result: dict) -> tuple[str, str, int]:
    return result["overall"], result["reason"], result["exit_code"]


@pytest.fixture
def copies(tmp_path):
    root = tmp_path / "copias"
    publish(root, RECENT, content=b"PGDMP-copia-recente")
    return root


@pytest.fixture
def fresh_signal(tmp_path):
    return write_signal(tmp_path / "last-check.json", NOW - timedelta(minutes=10))


def test_fresh_healthy_signal_and_fresh_copy_are_ok(fresh_signal, copies):
    result = look(fresh_signal, copies)

    assert summary(result) == ("ok", "all_ok", 0)
    app, check, copy = (
        result["signals"][k] for k in ("application_signal", "last_check", "offsite_copy")
    )
    assert (app["reason"], app["age_minutes"], app["max_age_minutes"]) == (
        "signal_fresh",
        10.0,
        45.0,
    )
    assert (check["reason"], check["problems"]) == ("check_ok", [])
    assert (copy["reason"], copy["generations"], copy["max_age_hours"]) == ("copy_fresh", 1, 26.0)
    assert result["last_valid_copy"] == {
        "stamp": stamp_of(RECENT),
        "recovery_point_utc": "2026-11-07T10:00:00Z",
        "age_hours": 2.0,
        "size_bytes": len(b"PGDMP-copia-recente"),
        "sha256": hashlib.sha256(b"PGDMP-copia-recente").hexdigest(),
    }


def test_recent_check_with_a_failure_fails_and_names_the_check(tmp_path, copies):
    checks = [*healthy_checks()[:3], CheckResult("database", Status.FAIL, "unavailable")]
    path = write_signal(tmp_path / "last-check.json", NOW - timedelta(minutes=5), checks)

    result = look(path, copies)

    assert summary(result) == ("fail", "check_failed", 1)
    assert result["signals"]["application_signal"]["status"] == "ok"
    assert result["signals"]["last_check"]["problems"] == [
        {"check": "database", "status": "fail", "reason": "unavailable"}
    ]
    assert result["signals"]["offsite_copy"]["status"] == "ok"


def _check_doc(**fields) -> bytes:
    base = {"schema": "cartorio_system.ops.check", "schema_version": "1.0"}
    return json.dumps({**base, **fields}).encode()


@pytest.mark.parametrize(
    ("content", "detail"),
    [
        (b"{nao e json", "unparseable"),
        (json.dumps(["lista"]).encode(), "schema"),
        (json.dumps({"schema": "outra.coisa"}).encode(), "schema"),
        (_check_doc(schema_version="2.0"), "schema_version"),
        (_check_doc(generated_at="ontem", overall="ok"), "generated_at"),
        (_check_doc(generated_at="2026-11-07T11:50:00Z", overall="talvez"), "overall"),
        (_check_doc(generated_at="2026-11-07T11:50:00Z", overall=[]), "overall"),
        (_check_doc(generated_at="2026-11-07T11:50:00Z", overall={}), "overall"),
        (_check_doc(generated_at="2026-11-07T11:50:00Z", overall=["ok"]), "overall"),
        (_check_doc(generated_at="2026-11-07T11:50:00Z", overall=None), "overall"),
    ],
)
def test_invalid_report_is_a_signal_failure_and_no_check_is_assumed(
    tmp_path, copies, content, detail
):
    path = tmp_path / "last-check.json"
    path.write_bytes(content)

    result = look(path, copies)

    assert summary(result) == ("fail", "signal_invalid", 1)
    assert result["signals"]["application_signal"]["detail"] == detail
    assert result["signals"]["last_check"] == {"status": "not_evaluated", "reason": "check_unknown"}
    assert result["signals"]["offsite_copy"]["reason"] == "copy_fresh"


@pytest.mark.parametrize("value", [[], {}], ids=["lista", "objeto"])
def test_unhashable_overall_keeps_reading_the_copy_and_its_evidence(tmp_path, copies, value):
    """Lista ou objeto em ``overall`` levantava TypeError antes de a cópia ser lida."""
    path = tmp_path / "last-check.json"
    path.write_bytes(_check_doc(generated_at="2026-11-07T11:50:00Z", overall=value))

    result = look(path, copies)

    assert summary(result) == ("fail", "signal_invalid", 1)
    assert result["signals"]["offsite_copy"]["reason"] == "copy_fresh"
    assert result["last_valid_copy"]["stamp"] == stamp_of(RECENT)


def test_oversized_or_non_file_signal_is_invalid(tmp_path, copies):
    big = tmp_path / "grande.json"
    big.write_bytes(b" " * (observer.MAX_SIGNAL_BYTES + 1))
    folder = tmp_path / "pasta.json"
    folder.mkdir()
    assert look(big, copies)["signals"]["application_signal"]["detail"] == "too_large"
    assert look(folder, copies)["signals"]["application_signal"]["detail"] == "not_a_file"


def test_missing_signal_fails_even_without_any_onfailure(tmp_path, copies):
    result = look(tmp_path / "nunca-chegou.json", copies)
    assert summary(result) == ("fail", "signal_missing", 1)
    assert result["signals"]["offsite_copy"]["status"] == "ok"


def test_stale_signal_fails_and_still_shows_what_the_last_check_said(tmp_path, copies):
    path = write_signal(tmp_path / "last-check.json", NOW - timedelta(hours=3))

    result = look(path, copies)

    app = result["signals"]["application_signal"]
    assert summary(result) == ("fail", "signal_stale", 1)
    assert (app["age_minutes"], app["max_age_minutes"]) == (180.0, 45.0)
    assert result["signals"]["last_check"]["reason"] == "check_ok"


def test_signal_from_the_future_is_never_fresh(tmp_path, copies):
    path = write_signal(tmp_path / "last-check.json", NOW + timedelta(hours=1))
    assert summary(look(path, copies)) == ("fail", "signal_from_future", 1)


def test_origin_unavailable_with_a_valid_copy_at_the_destination(tmp_path, copies):
    """VM fora do ar: o sinal parou, e a cópia externa válida segue como evidência."""
    path = write_signal(tmp_path / "last-check.json", NOW - timedelta(hours=6))

    result = look(path, copies)

    assert summary(result) == ("fail", "signal_stale", 1)
    assert result["signals"]["offsite_copy"]["reason"] == "copy_fresh"
    evidence = result["last_valid_copy"]
    assert (evidence["stamp"], evidence["age_hours"]) == (stamp_of(RECENT), 2.0)


def test_stale_copy_is_judged_by_the_manifest_recovery_point_not_by_mtime(tmp_path, fresh_signal):
    root = tmp_path / "copias"
    folder = publish(root, NOW - timedelta(hours=30))
    for item in folder.iterdir():
        os.utime(item, (NOW.timestamp(), NOW.timestamp()))  # mtime recente não engana

    result = look(fresh_signal, root)

    assert summary(result) == ("fail", "copy_stale", 1)
    assert result["last_valid_copy"]["age_hours"] == 30.0


def test_tampered_newest_generation_fails_and_keeps_the_previous_as_evidence(
    tmp_path, fresh_signal
):
    root = tmp_path / "copias"
    older, newest = NOW - timedelta(hours=20), NOW - timedelta(hours=1)
    publish(root, older)
    folder = publish(root, newest)
    (folder / f"backup-{stamp_of(newest)}.dump").write_bytes(CONTENT[:-1] + b"X")

    result = look(fresh_signal, root)

    copy = result["signals"]["offsite_copy"]
    assert summary(result) == ("fail", "copy_latest_invalid", 1)
    assert copy["latest"] == {
        "stamp": stamp_of(newest),
        "state": "invalid",
        "reason": "digest_mismatch",
    }
    assert copy["invalid_newer"] == 1
    assert result["last_valid_copy"]["stamp"] == stamp_of(older)


def test_staging_and_incomplete_publications_never_count_as_a_copy(tmp_path, fresh_signal):
    root = tmp_path / "copias"
    older, newer = NOW - timedelta(hours=3), NOW - timedelta(minutes=20)
    publish(root, older)
    write_publication(root / offsite.STAGING / f"{stamp_of(newer)}-0a1b2c3d", newer)

    result = look(fresh_signal, root)

    assert result["signals"]["offsite_copy"]["reason"] == "copy_fresh"
    assert result["signals"]["offsite_copy"]["generations"] == 1
    assert result["last_valid_copy"]["stamp"] == stamp_of(older)

    incomplete = publish(root, newer)
    (incomplete / f"backup-{stamp_of(newer)}.dump").unlink()
    (root / offsite.GENERATIONS / "leia-me.txt").write_text("x")
    (root / offsite.GENERATIONS / "nao-e-carimbo").mkdir()

    result = look(fresh_signal, root)

    copy = result["signals"]["offsite_copy"]
    assert copy["reason"] == "copy_latest_invalid"
    assert copy["latest"] == {
        "stamp": stamp_of(newer),
        "state": "invalid",
        "reason": "artifact_missing",
    }
    assert copy["ignored_entries"] == 2
    assert result["last_valid_copy"]["stamp"] == stamp_of(older)


def test_without_any_generation_the_copy_is_missing(tmp_path, fresh_signal):
    result = look(fresh_signal, tmp_path / "copias-inexistentes")
    assert summary(result) == ("fail", "copy_missing", 1)
    assert result["last_valid_copy"] is None


def test_generation_of_another_database_is_never_a_valid_copy(tmp_path, fresh_signal):
    root = tmp_path / "copias"
    publish(root, NOW - timedelta(hours=1), overrides={"database": "outro_banco"})

    result = look(fresh_signal, root)

    copy = result["signals"]["offsite_copy"]
    assert (copy["reason"], copy["latest"]["reason"]) == ("copy_no_valid", "database_mismatch")
    text = json.dumps(result)
    assert "outro_banco" not in text and DB not in text


def test_invalid_expected_database_is_inconclusive_for_the_copy(fresh_signal, copies):
    result = look(fresh_signal, copies, expected="nome; inválido")
    assert result["signals"]["offsite_copy"] == {
        "status": "inconclusive",
        "reason": "expected_database_invalid",
    }
    assert summary(result) == ("inconclusive", "expected_database_invalid", 2)


def test_free_text_from_the_report_never_reaches_the_output(tmp_path, copies):
    checks = [CheckResult("backup", Status.FAIL, "senha=segredo-ficticio-9f1")]
    path = write_signal(tmp_path / "last-check.json", NOW - timedelta(minutes=5), checks)

    result = look(path, copies)

    assert "segredo-ficticio-9f1" not in json.dumps(result)
    assert result["signals"]["last_check"]["problems"][0]["reason"] == "unrecognized"


# 48 hexadecimais começando por letra: passava no formato de código que o observador
# aceitava antes. Fictício.
HEX_FICTICIO = "f3c9a1e07b5d2c8f" * 3
FORMATO_ANTIGO = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def _report_with(**overrides) -> dict:
    report = build_report(
        [*healthy_checks()[:3], CheckResult("database", Status.FAIL, "unavailable")],
        NOW - timedelta(minutes=5),
    )
    report.update(overrides)
    return report


@pytest.mark.parametrize(
    "report",
    [
        _report_with(reason=HEX_FICTICIO),
        _report_with(checks={HEX_FICTICIO: {"status": "fail", "reason": "unavailable"}}),
        _report_with(checks={"database": {"status": HEX_FICTICIO, "reason": "unavailable"}}),
        _report_with(checks={"database": {"status": "fail", "reason": HEX_FICTICIO}}),
    ],
    ids=["motivo_do_relatorio", "nome_da_checagem", "status_da_checagem", "motivo_da_checagem"],
)
def test_value_in_code_format_but_outside_the_contract_never_reaches_the_output(
    tmp_path, copies, capsys, report
):
    assert len(HEX_FICTICIO) == 48 and FORMATO_ANTIGO.match(HEX_FICTICIO)
    path = tmp_path / "last-check.json"
    write_json_atomic(path, report)

    result = look(path, copies)
    argv = ["--signal", str(path), "--copies", str(copies), "--expected-database", DB]
    observer.main(argv, clock=fixed_clock())
    printed = capsys.readouterr().out

    assert HEX_FICTICIO not in json.dumps(result) and HEX_FICTICIO not in printed
    assert summary(result) == ("fail", "check_failed", 1)
    check = result["signals"]["last_check"]
    assert set(check) == {"status", "reason", "generated_at", "reported_reason", "problems"}
    assert check["problems"]
    assert all(set(item) == {"check", "status", "reason"} for item in check["problems"])
    assert "unrecognized" in json.dumps(check)


def test_known_codes_of_the_contract_are_kept(tmp_path, copies):
    checks = [
        CheckResult("alembic", Status.OK, "revision_match"),
        CheckResult("api", Status.INCONCLUSIVE, "systemctl_timeout"),
        CheckResult("backup", Status.FAIL, "backup_stale"),
        CheckResult("database", Status.FAIL, "auth_failed"),
    ]
    path = write_signal(tmp_path / "last-check.json", NOW - timedelta(minutes=5), checks)

    check = look(path, copies)["signals"]["last_check"]

    assert check["reported_reason"] == "check_failed"
    assert check["problems"] == [
        {"check": "api", "status": "inconclusive", "reason": "systemctl_timeout"},
        {"check": "backup", "status": "fail", "reason": "backup_stale"},
        {"check": "database", "status": "fail", "reason": "auth_failed"},
    ]


_VERIFIER_MODULES = ("report", "checks", "backup", "systemd", "verifier")


def _reason_literals_emitted_by_the_verifier() -> set[str]:
    """Literais nas posições de motivo do verificador: argumento de ``signal``/``single``/
    ``ProbeError``/``SystemctlError``/``CheckResult``/``Evaluation``, ``empty_reason=``,
    atribuição a ``reason`` e o par ``(…, "motivo")`` devolvido pelas funções de apoio."""
    positions = {
        "signal": 1,
        "single": 3,
        "ProbeError": 1,
        "SystemctlError": 0,
        "CheckResult": 2,
        "Evaluation": 2,
    }

    def literals(node: ast.AST) -> list[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return [node.value]
        if isinstance(node, ast.IfExp):
            return literals(node.body) + literals(node.orelse)
        if isinstance(node, ast.BoolOp):
            return [v for value in node.values for v in literals(value)]
        return []

    found: set[str] = set()
    for module in _VERIFIER_MODULES:
        tree = ast.parse((REPO_ROOT / "app" / "ops" / f"{module}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
                if name in positions and len(node.args) > positions[name]:
                    found.update(literals(node.args[positions[name]]))
                for keyword in node.keywords:
                    if keyword.arg in ("reason", "empty_reason"):
                        found.update(literals(keyword.value))
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    named = isinstance(target, ast.Name) and target.id == "reason"
                    keyed = isinstance(target, ast.Subscript) and literals(target.slice) == [
                        "reason"
                    ]
                    if named or keyed:
                        found.update(literals(node.value))
            elif isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple):
                if len(node.value.elts) == 2:
                    found.update(literals(node.value.elts[1]))
    return found


def test_every_reason_the_verifier_emits_is_in_the_observer_vocabulary():
    emitted = _reason_literals_emitted_by_the_verifier()
    assert len(emitted) > 60  # a coleta enxerga o verificador, não um arquivo vazio
    # O problema da DSN volta no par de database_from_dsn, mas expected_database o
    # converte antes de virar motivo de sinal.
    not_a_signal_reason = {"dsn_not_postgresql"}
    known = observer._CHECK_REASONS | observer._REPORT_REASONS
    assert emitted - known - not_a_signal_reason == set()


def test_observer_vocabulary_has_no_invented_code():
    """Todo código reconhecido existe como literal no verificador: o vocabulário não
    inventa motivo que o contrato não emite."""
    source = "".join(
        (REPO_ROOT / "app" / "ops" / f"{module}.py").read_text(encoding="utf-8")
        for module in (*_VERIFIER_MODULES, "config")
    )
    vocabulary = observer._CHECK_REASONS | observer._REPORT_REASONS | observer._CHECK_NAMES
    assert {code for code in vocabulary if f'"{code}"' not in source} == set()


@POSIX_ONLY
@pytest.mark.parametrize("part", ["root", offsite.GENERATIONS])
def test_linked_copy_layout_is_never_followed(tmp_path, fresh_signal, part):
    real = tmp_path / "real"
    publish(real, RECENT)
    root = tmp_path / "copias"
    if part == "root":
        root.symlink_to(real, target_is_directory=True)
    else:
        root.mkdir()
        (root / offsite.GENERATIONS).symlink_to(
            real / offsite.GENERATIONS, target_is_directory=True
        )

    result = look(fresh_signal, root)

    assert summary(result) == ("fail", "copies_layout_invalid", 1)
    assert result["last_valid_copy"] is None


@POSIX_ONLY
def test_ancestor_link_in_the_copies_path_is_never_followed(tmp_path, fresh_signal):
    """OPS-3 (S1): o leitor também não atravessa link num ancestral da raiz das cópias,
    mesmo com uma cópia válida e recente do outro lado."""
    real = tmp_path / "real"
    publish(real / "copias", RECENT)
    (tmp_path / "atalho").symlink_to(real, target_is_directory=True)

    result = look(fresh_signal, tmp_path / "atalho" / "copias")

    assert summary(result) == ("fail", "copies_layout_invalid", 1)
    assert result["last_valid_copy"] is None


def test_copy_imported_by_the_pilot_is_what_the_observer_sees(tmp_path, fresh_signal):
    source = tmp_path / "origem"
    write_publication(source, NOW - timedelta(hours=1))
    root = tmp_path / "copias"
    assert offsite.run_import(source, root, DB, now=NOW, platform="linux")["verdict"] == "published"
    shutil.rmtree(source)  # a origem sai do fluxo

    result = look(fresh_signal, root)

    assert summary(result) == ("ok", "all_ok", 0)
    assert result["last_valid_copy"]["stamp"] == stamp_of(NOW - timedelta(hours=1))


@pytest.mark.parametrize(("age", "code"), [(timedelta(minutes=5), 0), (timedelta(hours=2), 1)])
def test_cli_exit_code_follows_the_overall_state(tmp_path, copies, capsys, age, code):
    path = write_signal(tmp_path / "last-check.json", NOW - age)
    argv = ["--signal", str(path), "--copies", str(copies), "--expected-database", DB]

    assert observer.main(argv, clock=fixed_clock()) == code
    out = capsys.readouterr().out
    assert json.loads(out)["exit_code"] == code
    assert str(tmp_path) not in out and DB not in out


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "-inf", "1e300", "abc"])
@pytest.mark.parametrize("flag", ["--signal-max-age-minutes", "--copy-max-age-hours"])
def test_cli_rejects_invalid_thresholds(fresh_signal, copies, capsys, flag, value):
    """``nan``, ``inf`` e valores enormes chegavam ao ``timedelta`` e encerravam com
    exceção; agora são argumento inválido (saída 2 do argparse)."""
    argv = ["--signal", str(fresh_signal), "--copies", str(copies), "--expected-database", DB]
    with pytest.raises(SystemExit) as exc:
        observer.main([*argv, flag, value])
    assert exc.value.code == 2
    assert flag in capsys.readouterr().err


@pytest.mark.parametrize(
    ("flag", "value"), [("--signal-max-age-minutes", "0.5"), ("--copy-max-age-hours", "1e6")]
)
def test_cli_accepts_finite_positive_thresholds(fresh_signal, copies, capsys, flag, value):
    argv = ["--signal", str(fresh_signal), "--copies", str(copies), "--expected-database", DB]
    observer.main([*argv, flag, value], clock=fixed_clock())
    assert json.loads(capsys.readouterr().out)["schema"] == observer.OBSERVATION_SCHEMA


def test_cli_runs_with_no_database_configuration_at_all(tmp_path):
    """Processo próprio, sem DATABASE_URL nem CARTORIO_OPS_*: o observador não precisa de
    banco para concluir."""
    now = datetime.now(UTC).replace(microsecond=0)
    path = write_signal(tmp_path / "last-check.json", now - timedelta(minutes=5))
    root = tmp_path / "copias"
    publish(root, now - timedelta(hours=1))
    env = clean_env()
    assert "DATABASE_URL" not in env

    done = subprocess.run(
        [sys.executable, "-m", "app.ops.observer", "--signal", str(path), "--copies", str(root)]
        + ["--expected-database", DB],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert done.returncode == 0, done.stdout + done.stderr
    result = json.loads(done.stdout)
    assert summary(result) == ("ok", "all_ok", 0)
    assert str(tmp_path) not in done.stdout and DB not in done.stdout
