"""Gate PostgreSQL de bancada (CARTORIO-OPS-1) — o mesmo comando no CI e localmente.

    python scripts/ops/pg_gate.py --pg-bin DIR --work-root DIR --report ARQUIVO \\
        [--require-major 18]

1. Recusa ambiente com override de conexão libpq (mesma proteção da suíte do PR #5).
2. Confere e registra a versão das ferramentas e do servidor (padrão: 18).
3. Cria um cluster descartável com a identidade que a suíte do PR #5 exige
   (``cartorio_fase_b``/``cartorio_fase_b_test``), em loopback, senha gerada — e nele os
   dois bancos da prova de vínculo ao banco efetivo (``BINDING_DATABASES``).
4. Roda ``tests/test_postgres_compat.py`` e ``tests/test_ops_postgres.py`` apontados
   para ele. Qualquer teste PULADO reprova o gate: prova obrigatória não passa por
   skip de configuração ausente.
5. Derruba o cluster (limpeza restrita ao que criou) e roda a prova de recuperação.
6. A partir da cópia exportada pela prova sintética, roda o modo cópia: o banco
   esperado restaura numa área privada mesmo sob umask 022; um banco divergente é
   recusado antes de qualquer cluster; a cópia de origem sai intocada.
7. Grava um relatório JSON sem segredos e confere que nada do que publica carrega
   URL com senha. Saída 0 só com tudo aprovado.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path
from typing import Any

from defusedxml import ElementTree

from app.ops.backup import sha256_file
from app.ops.drill import ORIGIN_DB
from app.ops.pgcluster import (
    STOPPED_STATES,
    Cluster,
    DrillFailed,
    DrillRefused,
    create_work_dir,
    pg_binary,
    remove_work_dir,
    require_clean_libpq_env,
    run_tool,
    stop_all,
    subprocess_env,
    tool_version,
)
from app.ops.report import utc_iso, utc_now, write_json_atomic

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "cartorio_system.ops.pg_gate"
PR5_USER = "cartorio_fase_b"
PR5_DATABASE = "cartorio_fase_b_test"
# Dois bancos reais da mesma bancada, para provar o vínculo do backup ao banco que a
# conexão abriu (tests/test_ops_postgres.py). Nomes fixos, como a identidade do PR #5.
BINDING_DATABASES = ("cartorio_ops_vinculo_a", "cartorio_ops_vinculo_b")
TEST_FILES = ("tests/test_postgres_compat.py", "tests/test_ops_postgres.py")
# Banco que a cópia NÃO é: o modo cópia precisa recusá-la antes de restaurar.
FOREIGN_DATABASE = "outro_banco_ficticio"
# Área do modo cópia que o relatório do ensaio precisa mostrar, seja qual for o umask.
PRIVATE_AREA = {"work_dir": "0700", "artifact_dir": "0700", "artifact_files": ["0600"]}
# usuário:senha@ numa URL. Senha mascarada (***) não conta.
CREDENTIAL_IN_URL = re.compile(r"://[^\s/@:]+:(?!\*+@)[^\s/@]+@")


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
        for database in (PR5_DATABASE, *BINDING_DATABASES):
            conn.execute(
                sql.SQL("CREATE DATABASE {} OWNER {} TEMPLATE template0").format(
                    sql.Identifier(database), sql.Identifier(PR5_USER)
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
                "-rps",
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


def _drill(
    args: argparse.Namespace, name: str, *extra: str, umask: int = 0o077
) -> tuple[int, dict[str, Any], str]:
    """Um ensaio em processo próprio, sob o umask dado; relatório e log ficam ao lado do
    relatório do gate."""
    report = args.report.with_name(f"{args.report.stem}-{name}.json")
    log = args.report.with_name(f"{args.report.stem}-{name}.log")
    cmd = [
        sys.executable,
        "-m",
        "app.ops.drill",
        "--pg-bin",
        str(args.pg_bin),
        "--work-root",
        str(args.work_root),
        "--report",
        str(report),
        *extra,
    ]
    previous = os.umask(umask)
    try:
        proc = run_tool(cmd, env=subprocess_env(os.environ), log=log, timeout=1200)
    finally:
        os.umask(previous)
    print(log.read_text(encoding="utf-8", errors="replace"))
    data = json.loads(report.read_text(encoding="utf-8")) if report.exists() else {}
    return proc.returncode, data, report.name


def _summary(code: int, data: dict[str, Any], report_file: str) -> dict[str, Any]:
    return {
        "exit_code": code,
        "report_file": report_file,
        "verdict": data.get("verdict"),
        "reason": data.get("reason"),
        "server_version": (data.get("postgres") or {}).get("server_version"),
        "recovery_duration_seconds": (data.get("recovery") or {}).get("duration_seconds"),
    }


def _snapshot(directory: Path) -> dict[str, tuple[int, int, str]]:
    return {
        p.name: (p.stat().st_mode, p.stat().st_mtime_ns, sha256_file(p))
        for p in sorted(directory.iterdir())
    }


def _drill_proofs(args: argparse.Namespace, export: Path) -> tuple[dict[str, Any], list[str]]:
    code, data, report_file = _drill(args, "drill", "--export-artifact", str(export))
    results: dict[str, Any] = {"synthetic": _summary(code, data, report_file)}
    if code != 0 or data.get("verdict") != "passed":
        return results, ["restore_drill_not_passed"]
    (manifest,) = export.glob("backup-*.json")
    record = data["record"]
    copy = [
        "--from-manifest",
        str(manifest),
        "--expect-finding-id",
        str(record["finding_id"]),
        "--expect-finding-code",
        str(record["finding_code"]),
    ]
    before = _snapshot(export)
    reasons: list[str] = []

    # umask 022 de propósito: a área privada não pode depender do umask de quem chama.
    code, data, report_file = _drill(
        args, "copy", *copy, "--expect-database", ORIGIN_DB, umask=0o022
    )
    results["copy"] = _summary(code, data, report_file) | {"isolation": data.get("isolation")}
    if code != 0 or data.get("verdict") != "passed":
        reasons.append("copy_drill_not_passed")
    if data.get("isolation") != PRIVATE_AREA:
        reasons.append("copy_area_not_private")

    code, data, report_file = _drill(
        args, "copy-foreign", *copy, "--expect-database", FOREIGN_DATABASE, umask=0o022
    )
    # No modo cópia não há origem: qualquer cluster na limpeza seria o destino.
    provisioned = bool((data.get("cleanup") or {}).get("clusters"))
    results["copy_foreign_database"] = _summary(code, data, report_file) | {
        "cluster_provisioned": provisioned
    }
    refused = (code, data.get("verdict"), data.get("reason")) == (2, "refused", "database_mismatch")
    if not refused or provisioned:
        reasons.append("foreign_copy_not_refused")

    results["copy_source_untouched"] = _snapshot(export) == before
    if not results["copy_source_untouched"]:
        reasons.append("copy_source_modified")
    return results, reasons


def _run_drills(args: argparse.Namespace, run_id: str) -> tuple[dict[str, Any], list[str]]:
    """Prova sintética exportando a cópia; depois o modo cópia sobre ela. A cópia
    exportada vive numa área marcada deste gate e sai junto com ela."""
    export_id = f"{run_id}-copia"
    export_root = create_work_dir(args.work_root, export_id)
    try:
        results, reasons = _drill_proofs(args, export_root / "artefato")
    finally:
        removed = remove_work_dir(export_root, export_id)
    results["export_removed"] = removed
    if not removed:
        reasons.append("export_not_removed")
    return results, reasons


def published_credentials(report: Path) -> list[str]:
    """Relatórios e logs de ensaio publicados ao lado do relatório do gate que tragam
    URL com senha embutida."""
    return sorted(
        p.name
        for p in report.parent.glob(f"{report.stem}-*")
        if p.is_file() and CREDENTIAL_IN_URL.search(p.read_text(encoding="utf-8", errors="replace"))
    )


def gate_cleanup(cluster: Cluster | None, work: Path | None, run_id: str) -> dict[str, Any]:
    """Para e confirma o cluster dos testes; só então remove o diretório. Parada
    incerta preserva a área para diagnóstico e reprova o gate."""
    clusters = [cluster] if cluster is not None else []
    state = stop_all(clusters, subprocess_env(os.environ)).get("gate", "not_started")
    stopped = state in STOPPED_STATES
    removed = True
    if work is not None:
        if stopped:
            removed = remove_work_dir(work, run_id)
        else:
            removed = False
            print(
                f"[gate] cluster possivelmente ativo: diretório preservado em {work}; "
                "diagnóstico: pg_ctl status -D <diretório>/gate/data",
                file=sys.stderr,
            )
    return {
        "cluster": state,
        "work_dir_removed": removed,
        "confirmed": stopped and removed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python scripts/ops/pg_gate.py")
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--require-major", type=int, default=18)
    args = parser.parse_args(argv)
    # O que o gate e seus processos filhos criarem nasce privado.
    previous = os.umask(0o077)
    try:
        return _gate(args)
    finally:
        os.umask(previous)


def _gate(args: argparse.Namespace) -> int:
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
        report["gate_cleanup"] = gate_cleanup(cluster, work, run_id)
    if not report["gate_cleanup"]["confirmed"]:
        reasons.append("gate_cleanup_unconfirmed")

    # A prova de restauração só começa com o cluster dos testes confirmado parado e
    # o diretório dele removido.
    if not reasons:
        try:
            report["drill"], drill_reasons = _run_drills(args, run_id)
        except Exception as exc:  # o relatório do gate sai em qualquer desfecho
            drill_reasons = [f"unexpected_error:{type(exc).__name__}"]
        reasons += drill_reasons

    leaks = published_credentials(args.report)
    report["published_scan"] = {"credential_in_url": leaks}
    if leaks:
        reasons.append("credential_in_published_output")

    report.update(verdict="passed" if not reasons else "failed", reasons=reasons)
    report["finished_at"] = utc_iso(utc_now())
    write_json_atomic(args.report, report)
    print(json.dumps({k: report.get(k) for k in ("run_id", "verdict", "reasons")}))
    return 0 if not reasons else 1


if __name__ == "__main__":
    raise SystemExit(main())
