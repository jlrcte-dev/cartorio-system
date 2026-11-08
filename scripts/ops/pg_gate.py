"""Gate PostgreSQL de bancada (CARTORIO-OPS-1) — o mesmo comando no CI e localmente.

    python scripts/ops/pg_gate.py --pg-bin DIR --work-root DIR --publish-dir DIR \\
        [--require-major 18]
    python scripts/ops/pg_gate.py --list-released DIR [--github-output ARQUIVO]

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
7. Publica só no fim. A saída bruta dos subprocessos (logs e relatórios) fica numa área
   privada e nada dela é impresso antes de conferido: log limpo é impresso; com
   credencial, fica retido e só a categoria sai. Relatório limpo vai para a área
   liberada (``--publish-dir``, que não pode existir antes) e entra no manifesto de
   liberação, gravado por último; com credencial, fica retido e o gate reprova.
   Saída 0 só com tudo aprovado.

``--list-released`` é o que o workflow publica: os arquivos do manifesto, conferidos de
novo (nome, SHA-256, varredura). Divergência recusa a liberação inteira.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import stat
import subprocess
import sys
from collections.abc import Sequence
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
    private_mkdir,
    private_write,
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
RELEASE_SCHEMA = "cartorio_system.ops.pg_gate_release"
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

GATE_REPORT = "pg-gate-report.json"
DRILLS = ("drill", "copy", "copy-foreign")
RELEASE_MANIFEST = "pg-gate-liberados.json"
_RELEASABLE = re.compile(r"^pg-gate-report(?:-(?:drill|copy|copy-foreign))?\.json$")
_MAX_RELEASE_BYTES = 1024 * 1024

# Categorias de credencial procuradas em tudo o que o gate imprime ou publica, além das
# credenciais que o próprio gate gerou ("generated_secret"). Só a categoria sai.
CREDENTIAL_PATTERNS: dict[str, re.Pattern[str]] = {
    # usuário:senha@ numa URL; senha mascarada (***) ou marcador de modelo ({senha}) não conta
    "credential_in_url": re.compile(r"://[^\s/@:]+:(?!\*+@|\{[^\s}]*\}@)[^\s/@]+@"),
    # campo de senha, segredo ou token com valor, num JSON
    "secret_field": re.compile(
        r"(?i)\"(?:password|senha|secret|token)\"\s*:\s*\"(?!\*+\")[^\"]+\""
    ),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}


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


def credential_categories(text: str, known: Sequence[str] = ()) -> list[str]:
    """Categorias de credencial presentes no texto (vazio = limpo). Nunca o valor."""
    found = [name for name, pattern in CREDENTIAL_PATTERNS.items() if pattern.search(text)]
    if any(secret and secret in text for secret in known):
        found.append("generated_secret")
    return found


def _run_suite(raw: Path, cluster: Cluster, password: str, report: dict[str, Any]) -> list[str]:
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
    junit = raw / "pytest-junit.xml"
    log = raw / "pytest.log"
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
    # O log fica na área bruta: só sai depois de conferido (ver _publish).
    empty = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    totals = junit_totals(junit) if junit.exists() else empty
    report["pytest"] = {"files": list(TEST_FILES), "exit_code": proc.returncode, **totals}
    return gate_verdict(proc.returncode, totals)


def _drill(
    args: argparse.Namespace, name: str, *extra: str, umask: int = 0o077
) -> tuple[int, dict[str, Any], str]:
    """Um ensaio em processo próprio, sob o umask dado; relatório e log ficam na área
    bruta e só saem dela depois de conferidos."""
    report = args.raw_dir / f"pg-gate-report-{name}.json"
    log = args.raw_dir / f"pg-gate-{name}.log"
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


def _publish(raw: Path, publish: Path, known: Sequence[str], report: dict[str, Any]) -> list[str]:
    """Único ponto em que algo vindo dos subprocessos sai do processo, e só conferido: log
    limpo é impresso, relatório limpo vai para a área liberada; com credencial, os dois
    ficam retidos e só a categoria aparece. Devolve os motivos de reprovação."""
    logs = {"pytest": raw / "pytest.log", **{name: raw / f"pg-gate-{name}.log" for name in DRILLS}}
    reports = [raw / f"pg-gate-report-{name}.json" for name in DRILLS]
    printed: list[str] = []
    released: list[str] = []
    withheld: list[dict[str, Any]] = []
    checked = 0
    for label, path in logs.items():
        if not path.exists():
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        if found := credential_categories(text, known):
            withheld.append({"file": path.name, "categories": found})
            print(
                f"[gate] saída de {label} retida: credencial ({', '.join(found)})", file=sys.stderr
            )
        else:
            print(f"----- {label} -----\n{text}")
            printed.append(label)
    for path in reports:
        if not path.exists():
            continue
        checked += 1
        data = path.read_bytes()
        if found := credential_categories(data.decode("utf-8", errors="replace"), known):
            withheld.append({"file": path.name, "categories": found})
            print(f"[gate] {path.name} retido: credencial ({', '.join(found)})", file=sys.stderr)
        else:
            private_write(publish / path.name, data)
            released.append(path.name)
    report["publication"] = {"logs_printed": printed, "released": released, "withheld": withheld}
    report["secret_scan"] = {
        "method": "patterns_and_generated_secrets",
        "categories": [*CREDENTIAL_PATTERNS, "generated_secret"],
        "files_checked": checked,
    }
    return ["credential_in_output"] if withheld else []


def _write_release(publish: Path, run_id: str, names: list[str]) -> None:
    """Manifesto de liberação, gravado por último: sem ele, nada é publicado."""
    files = [{"name": name, "sha256": sha256_file(publish / name)} for name in names]
    write_json_atomic(
        publish / RELEASE_MANIFEST, {"schema": RELEASE_SCHEMA, "run_id": run_id, "files": files}
    )


def released_files(publish: Path) -> tuple[list[Path], list[str]]:
    """O que pode virar artefato: SÓ os arquivos do manifesto de liberação, conferidos de
    novo — nome esperado, arquivo regular no próprio diretório, SHA-256 e varredura.
    Qualquer divergência recusa a liberação inteira; arquivo fora do manifesto nunca é
    selecionado."""
    manifest = publish / RELEASE_MANIFEST
    try:
        info = manifest.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > _MAX_RELEASE_BYTES:
            return [], ["release_manifest_invalid"]
        data = json.loads(manifest.read_bytes())
    except FileNotFoundError:
        return [], ["release_manifest_missing"]
    except (OSError, ValueError):
        return [], ["release_manifest_invalid"]
    if not isinstance(data, dict) or data.get("schema") != RELEASE_SCHEMA:
        return [], ["release_manifest_invalid"]
    entries = data.get("files")
    if not isinstance(entries, list) or not entries:
        return [], ["release_manifest_invalid"]
    selected: list[Path] = []
    problems: set[str] = set()
    for entry in entries:
        name = entry.get("name") if isinstance(entry, dict) else None
        digest = entry.get("sha256") if isinstance(entry, dict) else None
        if not isinstance(name, str) or not _RELEASABLE.match(name) or not isinstance(digest, str):
            problems.add("release_entry_invalid")
            continue
        path = publish / name
        try:
            info = path.lstat()
        except OSError:
            problems.add("released_file_missing")
            continue
        if path in selected or not stat.S_ISREG(info.st_mode):
            problems.add("released_file_invalid")
        elif info.st_size > _MAX_RELEASE_BYTES or sha256_file(path) != digest:
            problems.add("released_file_modified")
        elif credential_categories(path.read_text(encoding="utf-8", errors="replace")):
            problems.add("credential_in_released_file")
        else:
            selected.append(path)
    if problems:
        return [], sorted(problems)
    return selected, []


def list_released(publish: Path, github_output: Path | None) -> int:
    paths, problems = released_files(publish)
    for problem in problems:
        print(f"[gate] liberação recusada: {problem}", file=sys.stderr)
    if problems:
        return 1
    lines = "\n".join(str(path) for path in paths)
    if github_output is None:
        print(lines)
    else:
        delimiter = f"LIBERADOS_{secrets.token_hex(8)}"
        with github_output.open("a", encoding="utf-8") as handle:
            handle.write(f"paths<<{delimiter}\n{lines}\n{delimiter}\n")
    print(f"[gate] liberados: {', '.join(path.name for path in paths)}", file=sys.stderr)
    return 0


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
    parser.add_argument("--pg-bin", type=Path)
    parser.add_argument("--work-root", type=Path)
    parser.add_argument(
        "--publish-dir", type=Path, help="área liberada (não pode existir): só o conferido"
    )
    parser.add_argument("--require-major", type=int, default=18)
    parser.add_argument(
        "--list-released", type=Path, metavar="DIR", help="lista, conferido, o que o gate liberou"
    )
    parser.add_argument("--github-output", type=Path, help="com --list-released: saída do passo")
    args = parser.parse_args(argv)
    if args.list_released is not None:
        return list_released(args.list_released, args.github_output)
    required = {
        "--pg-bin": args.pg_bin,
        "--work-root": args.work_root,
        "--publish-dir": args.publish_dir,
    }
    if missing := [flag for flag, value in required.items() if value is None]:
        parser.error(f"obrigatório: {' '.join(missing)}")
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
    try:
        # Área liberada nova: nada de outra execução pode ser misturado ou selecionado.
        private_mkdir(args.publish_dir, parents=True)
    except OSError as exc:
        reason = (
            "publish_dir_exists" if isinstance(exc, FileExistsError) else "publish_dir_unusable"
        )
        print(json.dumps({"run_id": run_id, "verdict": "failed", "reasons": [reason]}))
        return 1
    reasons: list[str] = []
    known: list[str] = []  # credenciais geradas por este gate
    raw_id = f"{run_id}-bruto"
    raw: Path | None = None
    work: Path | None = None
    cluster: Cluster | None = None
    try:
        require_clean_libpq_env(os.environ)
        raw = args.raw_dir = create_work_dir(args.work_root, raw_id)
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
        known.append(cluster.password)
        cluster.start(env)
        cluster.prove_identity()
        report["postgres"]["server_version"] = cluster.server_version
        if cluster.server_major != args.require_major:
            raise DrillRefused("pg_major_not_required", required=args.require_major)
        password = secrets.token_urlsafe(24)
        known.append(password)
        reasons += _run_suite(raw, cluster, password, report)
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

    released: list[str] = []
    if raw is not None:
        reasons += _publish(raw, args.publish_dir, known, report)
        released = list(report["publication"]["released"])
        report["publication"]["raw_area_removed"] = remove_work_dir(raw, raw_id)
        if not report["publication"]["raw_area_removed"]:
            reasons.append("raw_area_not_removed")
    report["gitleaks"] = {"executed": False, "reason": "not_available_td10"}

    report.update(verdict="passed" if not reasons else "failed", reasons=reasons)
    report["finished_at"] = utc_iso(utc_now())
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if credential_categories(text, known):  # o próprio relatório também passa pela conferência
        reasons.append("credential_in_output")
    else:
        private_write(args.publish_dir / GATE_REPORT, text.encode("utf-8"))
        released.append(GATE_REPORT)
    _write_release(args.publish_dir, run_id, released)
    verdict = "passed" if not reasons else "failed"
    print(json.dumps({"run_id": run_id, "verdict": verdict, "reasons": reasons}))
    return 0 if not reasons else 1


if __name__ == "__main__":
    raise SystemExit(main())
