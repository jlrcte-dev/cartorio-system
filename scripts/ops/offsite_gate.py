"""Prova da CARTORIO-OPS-2 no job ``postgres-gate`` (piloto de cópia fora do host).

Passo próprio, depois do gate da OPS-1, que fica intocado (comando, testes e os quatro
relatórios publicados). Reaproveita o PostgreSQL 18 instalado e cria só clusters
próprios, em loopback, com credencial gerada e descartada pelo ``app.ops.drill``.

1. **POSIX:** os 13 testes de modos e links do piloto rodam com ``-rA``; reprova se não
   forem exatamente 13 aprovados, com nenhum pulado.
2. **Ponta a ponta**, numa área marcada deste passo:
   ensaio sintético exporta dump + manifesto → ``app.ops.offsite`` importa para um destino
   privado (SHA-256 e modos conferidos) → observador saudável → a origem sai do fluxo e o
   sinal da aplicação para → o observador acusa a perda do sinal e mantém a última cópia
   válida → ``app.ops.drill`` restaura usando só o manifesto da geração no destino.
3. **Saída:** só um resumo sintético (SHA, versão, resultado de cada prova, limpeza),
   conferido contra credencial antes de impresso. Logs brutos nunca saem; a área é
   removida no fim.

Uso: python scripts/ops/offsite_gate.py --pg-bin /usr/lib/postgresql/18/bin --work-root DIR
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

from pg_gate import REPO_ROOT, credential_categories, gate_verdict, junit_totals

from app.ops.backup import sha256_file
from app.ops.drill import ORIGIN_DB
from app.ops.offsite import GENERATIONS
from app.ops.pgcluster import (
    DrillRefused,
    create_work_dir,
    private_mkdir,
    remove_work_dir,
    require_clean_libpq_env,
    run_tool,
    subprocess_env,
)
from app.ops.report import CheckResult, Status, build_report, utc_now, write_json_atomic

SCHEMA = "cartorio_system.ops.offsite_gate"
SCHEMA_VERSION = "1.0"
POSIX_FILES = ("tests/test_ops_offsite.py", "tests/test_ops_observer.py")
POSIX_SELECTION = (
    "umask_022 or writable_by_others or linked_destination or links_in_the_source"
    " or linked_generation or linked_copy_layout"
)
POSIX_EXPECTED = 13
_PASSED = re.compile(r"^PASSED (tests/test_ops_(?:offsite|observer)\.py::\S+)$")
# Destino privado desde a criação, mesmo sob umask 022.
PRIVATE_MODES = {"destination": "0700", "generation": "0700", "files": "0600"}
# Origem e sinal retirados: o observador falha pelo sinal e mantém a cópia válida.
SIGNAL_LOST = ("fail", "signal_missing", "copy_fresh")
RESTORE_CHECKS = (
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


def posix_reasons(totals: dict[str, int], passed: list[str]) -> list[str]:
    """Motivos de reprovação da prova POSIX; vazio = aprovada."""
    reasons = list(gate_verdict(totals.get("exit_code", 0), totals))
    if totals.get("tests") != POSIX_EXPECTED or len(passed) != POSIX_EXPECTED:
        reasons.append("posix_tests_not_all_passed")
    return reasons


def e2e_reasons(facts: dict[str, Any]) -> list[str]:
    """Motivos de reprovação da prova ponta a ponta a partir dos fatos coletados."""
    reasons: list[str] = []
    export, imported = facts.get("export") or {}, facts.get("import") or {}
    healthy, lost = facts.get("observer_healthy") or {}, facts.get("observer_signal_lost") or {}
    restore = facts.get("restore") or {}
    if export.get("verdict") != "passed":
        reasons.append("export_not_passed")
    if imported.get("verdict") != "published" or not imported.get("sha256_matches_export"):
        reasons.append("import_not_verified")
    if imported.get("modes") != PRIVATE_MODES:
        reasons.append("import_not_private")
    if healthy.get("overall") != "ok":
        reasons.append("observer_not_ok_with_signal")
    lost_state = (lost.get("overall"), lost.get("application_signal"), lost.get("offsite_copy"))
    if lost_state != SIGNAL_LOST:
        reasons.append("signal_loss_not_detected")
    if not lost.get("last_valid_copy_is_the_import"):
        reasons.append("last_valid_copy_not_kept")
    if not facts.get("origin_removed_before_restore"):
        reasons.append("origin_still_present")
    reasons += [f"restore_{name}" for name in RESTORE_CHECKS if not restore.get(name)]
    if not facts.get("work_removed"):
        reasons.append("work_not_removed")
    return reasons


def restore_facts(
    code: int, synthetic: dict[str, Any], restored: dict[str, Any], export_sha: str | None
) -> dict[str, Any]:
    """O que a restauração a partir do destino provou, lido só dos relatórios do ensaio
    sintético (origem) e da restauração. ``generation_untouched`` é medido à parte."""
    artifact = restored.get("artifact") or {}
    destination = restored.get("destination") or {}
    heads = (synthetic.get("release") or {}).get("alembic_heads")
    known_clusters = {
        (synthetic.get("origin") or {}).get("system_identifier"),
        (synthetic.get("destination") or {}).get("system_identifier"),
        None,
    }
    return {
        "exit_code": code,
        "verdict_passed": code == 0 and restored.get("verdict") == "passed",
        "same_sha256": export_sha is not None and artifact.get("sha256") == export_sha,
        "digest_verified": artifact.get("verifier_evaluation") == "digest_verified",
        "database_matched": artifact.get("database_matched") is True,
        "distinct_cluster": destination.get("system_identifier") not in known_clusters,
        "alembic_compatible": bool(heads)
        and destination.get("alembic_revisions") == heads
        and destination.get("alembic_check") == "no_drift",
        "api_read": destination.get("api_app_name_confirmed") is True
        and (restored.get("record") or {}).get("matched_on_destination") is True,
        "cleanup_confirmed": (restored.get("cleanup") or {}).get("confirmed") is True
        and (synthetic.get("cleanup") or {}).get("confirmed") is True,
        "recovery_seconds": (restored.get("recovery") or {}).get("duration_seconds"),
    }


def released_summary(summary: dict[str, Any]) -> tuple[str | None, list[str]]:
    """Texto do resumo se estiver limpo; com credencial, nada sai (só as categorias)."""
    text = json.dumps(summary, ensure_ascii=False, indent=2)
    found = credential_categories(text)
    return (None, found) if found else (text, [])


def _mode(path: Path) -> str:
    return f"{stat.S_IMODE(path.stat().st_mode):04o}"


def _python(args: list[str], out: Path, *, umask: int) -> int:
    """Módulo do projeto em processo próprio; saída só para a área bruta."""
    previous = os.umask(umask)
    try:
        with out.open("w", encoding="utf-8") as handle:
            proc = subprocess.run(
                [sys.executable, *args],
                cwd=REPO_ROOT,
                env=subprocess_env(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                stdout=handle,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                timeout=600,
                check=False,
            )
    finally:
        os.umask(previous)
    return proc.returncode


def _json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _posix(raw: Path) -> tuple[dict[str, Any], list[str]]:
    junit, log = raw / "posix-junit.xml", raw / "posix.log"
    code = _python(
        [
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "-rA",
            f"--junitxml={junit}",
            *POSIX_FILES,
            "-k",
            POSIX_SELECTION,
        ],
        log,
        umask=0o022,
    )
    empty = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    totals = {**(junit_totals(junit) if junit.exists() else empty), "exit_code": code}
    passed = sorted(
        m.group(1)
        # A saída do filho vem na codificação do sistema: o que importa aqui é ASCII.
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines()
        if (m := _PASSED.match(line))
    )
    return {**totals, "passed": passed}, posix_reasons(totals, passed)


def _drill(args: argparse.Namespace, raw: Path, name: str, *extra: str) -> tuple[int, dict]:
    report, log = raw / f"{name}.json", raw / f"{name}.log"
    cmd = [sys.executable, "-m", "app.ops.drill", "--pg-bin", str(args.pg_bin)]
    cmd += ["--work-root", str(args.work), "--report", str(report), *extra]
    previous = os.umask(0o022)  # a área privada não pode depender do umask de quem chama
    try:
        proc = run_tool(cmd, env=subprocess_env(os.environ), log=log, timeout=1200)
    finally:
        os.umask(previous)
    return proc.returncode, _json(report)


def _signal(path: Path) -> None:
    checks = [CheckResult(n, Status.OK, "ok") for n in ("alembic", "api", "backup", "database")]
    write_json_atomic(path, build_report(checks, utc_now() - timedelta(minutes=1)))


def _observe(raw: Path, name: str, signal: Path, copies: Path) -> dict[str, Any]:
    out = raw / f"{name}.json"
    argv = ["-m", "app.ops.observer", "--signal", str(signal), "--copies", str(copies)]
    code = _python([*argv, "--expected-database", ORIGIN_DB], out, umask=0o077)
    data = _json(out)
    signals = data.get("signals") or {}
    return {
        "exit_code": code,
        "overall": data.get("overall"),
        "application_signal": (signals.get("application_signal") or {}).get("reason"),
        "offsite_copy": (signals.get("offsite_copy") or {}).get("reason"),
        "last_valid_sha256": (data.get("last_valid_copy") or {}).get("sha256"),
    }


def _snapshot(folder: Path) -> dict[str, tuple[int, str]]:
    return {p.name: (p.stat().st_mode, sha256_file(p)) for p in sorted(folder.iterdir())}


def _end_to_end(args: argparse.Namespace, raw: Path) -> dict[str, Any]:
    work = args.work
    facts: dict[str, Any] = {}
    origin, copies, signal = work / "origem", work / "destino", work / "sinal" / "last-check.json"

    code, synthetic = _drill(args, raw, "ensaio-sintetico", "--export-artifact", str(origin))
    export_sha = (synthetic.get("artifact") or {}).get("sha256")
    facts["export"] = {"exit_code": code, "verdict": synthetic.get("verdict"), "sha256": export_sha}
    if code != 0 or synthetic.get("verdict") != "passed":
        return facts

    out = raw / "offsite.json"
    argv = ["-m", "app.ops.offsite", "--source", str(origin), "--destination", str(copies)]
    code = _python([*argv, "--expected-database", ORIGIN_DB], out, umask=0o022)
    imported = _json(out)
    stamp = (imported.get("source") or {}).get("stamp") or ""
    generation = copies / GENERATIONS / stamp
    dump = generation / f"backup-{stamp}.dump"
    facts["import"] = {"exit_code": code, "verdict": imported.get("verdict")}
    if not dump.is_file():
        return facts
    facts["import"] |= {
        "sha256_matches_export": sha256_file(dump) == export_sha,
        "modes": {
            "destination": _mode(copies),
            "generation": _mode(generation),
            "files": "0600" if {_mode(p) for p in generation.iterdir()} == {"0600"} else "outro",
        },
    }

    _signal(signal)
    facts["observer_healthy"] = _observe(raw, "observador-com-sinal", signal, copies)
    shutil.rmtree(origin)  # a origem de laboratório sai do fluxo...
    signal.unlink()  # ...e o sinal da aplicação deixa de chegar
    facts["origin_removed_before_restore"] = not origin.exists()
    lost = _observe(raw, "observador-sem-sinal", signal, copies)
    lost["last_valid_copy_is_the_import"] = lost.pop("last_valid_sha256") == export_sha
    facts["observer_signal_lost"] = lost

    before = _snapshot(generation)
    record = synthetic.get("record") or {}
    code, restored = _drill(
        args,
        raw,
        "restauracao-do-destino",
        "--from-manifest",
        str(generation / f"backup-{stamp}.json"),
        "--expect-finding-id",
        str(record.get("finding_id")),
        "--expect-finding-code",
        str(record.get("finding_code")),
        "--expect-database",
        ORIGIN_DB,
    )
    facts["restore"] = restore_facts(code, synthetic, restored, export_sha) | {
        "generation_untouched": _snapshot(generation) == before
    }
    facts["release"] = {
        "git_sha": (synthetic.get("release") or {}).get("git_sha"),
        "postgres": (restored.get("postgres") or {}).get("server_version"),
    }
    return facts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    args = parser.parse_args(argv)
    require_clean_libpq_env(os.environ)
    previous = os.umask(0o077)
    try:
        return _gate(args)
    finally:
        os.umask(previous)


def _gate(args: argparse.Namespace) -> int:
    run_id = f"{utc_now().strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(3)}-ops2"
    try:
        work = create_work_dir(args.work_root, run_id)
    except DrillRefused as exc:
        print(f"[ops2] reprovado: área de trabalho recusada ({exc})")
        return 1
    args.work = work
    raw = work / "bruto"
    private_mkdir(raw)
    try:
        posix, reasons = _posix(raw)
        facts = _end_to_end(args, raw)
    finally:
        removed = remove_work_dir(work, run_id)
    facts["work_removed"] = removed and not work.exists()
    reasons += e2e_reasons(facts)
    summary = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "posix_tests": posix,
        "end_to_end": facts,
        "verdict": "failed" if reasons else "passed",
        "reasons": reasons,
    }
    text, found = released_summary(summary)
    if text is None:
        print(f"[ops2] reprovado: resumo retido (credential_in_output: {', '.join(found)})")
        return 1
    print(text)
    print(f"[ops2] veredito: {summary['verdict']}")
    return 1 if reasons else 0


if __name__ == "__main__":
    sys.exit(main())
