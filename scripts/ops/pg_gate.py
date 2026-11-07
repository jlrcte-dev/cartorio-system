"""Gate PostgreSQL de bancada (CARTORIO-OPS-1) — o mesmo comando no CI e localmente.

    python scripts/ops/pg_gate.py --pg-bin DIR --work-root DIR --report ARQUIVO \\
        [--require-major 18]

1. Recusa ambiente com override de conexão libpq (mesma proteção da suíte do PR #5).
2. Confere e registra a versão das ferramentas e do servidor (padrão: 18).
3. Cria um cluster descartável com a identidade que a suíte do PR #5 exige
   (``cartorio_fase_b``/``cartorio_fase_b_test``), em loopback, senha gerada.
4. Roda ``tests/test_postgres_compat.py`` e ``tests/test_ops_postgres.py`` apontados
   para ele. Qualquer teste PULADO reprova o gate: prova obrigatória não passa por
   skip de configuração ausente.
5. Derruba o cluster (limpeza restrita ao que criou) e roda a prova de recuperação.
6. Grava um relatório JSON sem segredos. Saída 0 só com tudo aprovado.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path
from typing import Any

from defusedxml import ElementTree

from app.ops.pgcluster import (
    Cluster,
    DrillFailed,
    DrillRefused,
    create_work_dir,
    pg_binary,
    remove_work_dir,
    require_clean_libpq_env,
    run_tool,
    subprocess_env,
    tool_version,
)
from app.ops.report import utc_iso, utc_now, write_json_atomic

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "cartorio_system.ops.pg_gate"
PR5_USER = "cartorio_fase_b"
PR5_DATABASE = "cartorio_fase_b_test"
TEST_FILES = ("tests/test_postgres_compat.py", "tests/test_ops_postgres.py")


def junit_totals(path: Path) -> dict[str, int]:
    root = ElementTree.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for key in totals:
            totals[key] += int(suite.get(key, 0))
    return totals


def gate_verdict(exit_code: int, totals: dict[str, int]) -> list[str]:
    """Motivos de reprovação; vazio = aprovado. Pulo conta como reprovação."""
    reasons = []
    if exit_code != 0:
        reasons.append("pytest_exit_nonzero")
    if totals["failures"] or totals["errors"]:
        reasons.append("tests_failed")
    if totals["skipped"]:
        reasons.append("mandatory_proof_skipped")
    if totals["tests"] == 0:
        reasons.append("no_tests_collected")
    return reasons


def _run_suite(work: Path, cluster: Cluster, password: str, report: dict[str, Any]) -> list[str]:
    from psycopg import sql

    with cluster.connect() as conn:
        conn.execute(
            sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                sql.Identifier(PR5_USER), sql.Literal(password)
            )
        )
        conn.execute(
            sql.SQL("CREATE DATABASE {} OWNER {} TEMPLATE template0").format(
                sql.Identifier(PR5_DATABASE), sql.Identifier(PR5_USER)
            )
        )
    host = cluster.address()
    url = f"postgresql+psycopg://{PR5_USER}:{password}@{host}:{cluster.port}/{PR5_DATABASE}"
    junit = work / "pytest-junit.xml"
    log = work / "pytest.log"
    env = subprocess_env(os.environ, CARTORIO_TEST_POSTGRES_URL=url, PYTHONDONTWRITEBYTECODE="1")
    with log.open("w", encoding="utf-8") as handle:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "-q",
                "-rs",
                f"--junitxml={junit}",
                *TEST_FILES,
            ],
            cwd=REPO_ROOT,
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            timeout=900,
            check=False,
        )
    output = log.read_text(encoding="utf-8", errors="replace").replace(password, "***")
    print(output)
    empty = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    totals = junit_totals(junit) if junit.exists() else empty
    report["pytest"] = {"files": list(TEST_FILES), "exit_code": proc.returncode, **totals}
    return gate_verdict(proc.returncode, totals)


def _run_drill(args: argparse.Namespace) -> tuple[dict[str, Any], bool]:
    """Prova de recuperação em processo próprio; o relatório completo fica ao lado."""
    drill_report = args.report.with_name(args.report.stem + "-drill.json")
    drill_log = args.report.with_name(args.report.stem + "-drill.log")
    proc = run_tool(
        [
            sys.executable,
            "-m",
            "app.ops.drill",
            "--pg-bin",
            str(args.pg_bin),
            "--work-root",
            str(args.work_root),
            "--report",
            str(drill_report),
        ],
        env=subprocess_env(os.environ),
        log=drill_log,
        timeout=1200,
    )
    print(drill_log.read_text(encoding="utf-8", errors="replace"))
    drill = json.loads(drill_report.read_text(encoding="utf-8")) if drill_report.exists() else {}
    summary = {
        "exit_code": proc.returncode,
        "report_file": drill_report.name,
        "verdict": drill.get("verdict"),
        "reason": drill.get("reason"),
        "server_version": (drill.get("postgres") or {}).get("server_version"),
        "recovery_duration_seconds": (drill.get("recovery") or {}).get("duration_seconds"),
    }
    return summary, proc.returncode == 0 and drill.get("verdict") == "passed"


def main() -> int:
    parser = argparse.ArgumentParser(prog="python scripts/ops/pg_gate.py")
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--require-major", type=int, default=18)
    args = parser.parse_args()

    started = utc_now()
    run_id = f"{started.strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(3)}"
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "schema_version": "1.0",
        "run_id": run_id,
        "started_at": utc_iso(started),
        "classification": "bench",
    }
    reasons: list[str] = []
    work: Path | None = None
    cluster: Cluster | None = None
    try:
        require_clean_libpq_env(os.environ)
        versions = {
            name: tool_version(pg_binary(args.pg_bin, name))
            for name in ("postgres", "initdb", "pg_ctl", "pg_dump", "pg_restore")
        }
        report["postgres"] = {"tools": {name: v for name, (v, _) in versions.items()}}
        if {major for _, major in versions.values()} != {args.require_major}:
            raise DrillRefused("pg_major_not_required", required=args.require_major)
        work = create_work_dir(args.work_root, run_id)
        cluster = Cluster(label="gate", run_id=run_id, pg_bin=args.pg_bin, root=work / "gate")
        env = subprocess_env(os.environ)
        cluster.initialize(env)
        cluster.start(env)
        cluster.prove_identity()
        report["postgres"]["server_version"] = cluster.server_version
        if cluster.server_major != args.require_major:
            raise DrillRefused("pg_major_not_required", required=args.require_major)
        reasons += _run_suite(work, cluster, secrets.token_urlsafe(24), report)
    except (DrillRefused, DrillFailed) as exc:
        reasons.append(exc.reason)
    except Exception as exc:  # relatório e limpeza em qualquer desfecho
        reasons.append(f"unexpected_error:{type(exc).__name__}")
    finally:
        if cluster is not None:
            report["cluster_stopped"] = cluster.stop(subprocess_env(os.environ))
        if work is not None:
            report["work_dir_removed"] = remove_work_dir(work, run_id)

    if not reasons:
        report["drill"], drill_passed = _run_drill(args)
        if not drill_passed:
            reasons.append("restore_drill_not_passed")

    report.update(verdict="passed" if not reasons else "failed", reasons=reasons)
    report["finished_at"] = utc_iso(utc_now())
    write_json_atomic(args.report, report)
    print(json.dumps({k: report.get(k) for k in ("run_id", "verdict", "reasons")}))
    return 0 if not reasons else 1


if __name__ == "__main__":
    raise SystemExit(main())
