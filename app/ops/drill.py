"""Prova de recuperação em PostgreSQL descartável (CARTORIO-OPS-1) — só bancada.

Uso (raiz do repositório)::

    python -m app.ops.drill --pg-bin DIR --work-root DIR --report ARQUIVO
        [--export-artifact DIR]
    python -m app.ops.drill --pg-bin DIR --work-root DIR --report ARQUIVO \\
        --from-manifest backup-<carimbo>.json --expect-finding-id N --expect-finding-code COD

Modo sintético: cria a ORIGEM (cluster próprio), aplica as migrations, grava um achado
sintético pela API real, gera o dump no formato da rotina de backup existente
(``backup-<carimbo>.dump`` + manifesto) e o verifica com o mesmo avaliador do
verificador. Desliga a origem — daí em diante o registro só pode vir do destino —,
cria o DESTINO (outro cluster, identidade distinta e comprovada, banco vazio criado
por esta execução), restaura com ferramentas da mesma versão principal do servidor,
confere a revisão Alembic e consulta o registro pela API apontada para o destino.

Modo cópia (``--from-manifest``): pula a origem e restaura uma cópia existente,
conferida contra o próprio manifesto — o formato da futura recuperação a partir da
cópia guardada no PC dedicado. O arquivo original nunca é alterado: o ensaio trabalha
numa cópia dentro do diretório de trabalho.

Nunca recebe DSN: todo alvo é criado aqui, em loopback, com credencial gerada. Limpeza
restrita ao que esta execução criou, inclusive em falha. Tempos são medições de
bancada, não RTO de produção.

Saída: 0 aprovado · 1 reprovado (uma verificação falhou) · 2 recusado ou não executável
(alvo sem identidade comprovada, ferramenta ausente ou de versão principal diferente,
ambiente com override de conexão).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.ops.backup import RESTORE_DRILL_SCHEMA, evaluate_publication, parse_stamp, sha256_file
from app.ops.checks import direct_opener, release_heads
from app.ops.config import DATABASE_NAME
from app.ops.pgcluster import (
    LOOPBACK,
    Cluster,
    DrillFailed,
    DrillRefused,
    create_work_dir,
    free_port,
    pg_binary,
    remove_work_dir,
    require_clean_libpq_env,
    run_tool,
    subprocess_env,
    tool_version,
    verify_restore_target,
)
from app.ops.report import Clock, utc_iso, utc_now, write_json_atomic

SCHEMA_VERSION = "1.0"
APP_ROLE = "cartorio_drill_app"
ORIGIN_DB = "cartorio_drill_origem"
TARGET_DB = "cartorio_drill_destino"
REPO_ROOT = Path(__file__).resolve().parents[2]
_REVISION = re.compile(r"\b[0-9a-f]{12}\b")
_ARCHIVE_CREATED = re.compile(r"Archive created at (.+)$", re.MULTILINE)
_TOC_ENTRIES = re.compile(r"^;\s+TOC Entries:\s+(\d+)\s*$", re.MULTILINE)
_EXIT = {"passed": 0, "failed": 1, "refused": 2}


@dataclass
class Ctx:
    run_id: str
    pg_bin: Path
    work: Path
    clock: Clock
    base_env: dict[str, str]
    secrets: list[str] = field(default_factory=list)
    clusters: list[Cluster] = field(default_factory=list)
    report: dict[str, Any] = field(default_factory=dict)
    marks: dict[str, float] = field(default_factory=dict)

    def mark(self, name: str) -> None:
        self.marks[name] = time.monotonic()

    def span(self, start: str, end: str) -> float:
        return round(self.marks[end] - self.marks[start], 3)


def _scrub(text: str, hidden: Sequence[str]) -> str:
    for value in hidden:
        if value:
            text = text.replace(value, "***")
    return re.sub(r"://([^:/@\s]+):([^@/\s]+)@", r"://\1:***@", text)


def _db_url(cluster: Cluster, dbname: str, password: str) -> str:
    host = cluster.address()
    return f"postgresql+psycopg://{APP_ROLE}:{password}@{host}:{cluster.port}/{dbname}"


def _git_release() -> dict[str, Any]:
    def git(*args: str) -> str | None:
        try:
            proc = subprocess.run(
                ["git", *args],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=20,
                stdin=subprocess.DEVNULL,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return proc.stdout.strip() if proc.returncode == 0 else None

    status = git("status", "--porcelain", "--untracked-files=no")
    return {"git_sha": git("rev-parse", "HEAD"), "worktree_dirty": bool(status)}


def _python_tool(ctx: Ctx, args: list[str], env: Mapping[str, str], log: Path) -> str:
    result = run_tool([sys.executable, "-m", *args], env=env, log=log, timeout=180)
    output = log.read_text(encoding="utf-8", errors="replace")
    if result.returncode != 0:
        tail = _scrub("\n".join(output.splitlines()[-20:]), ctx.secrets)
        print(f"[drill] {' '.join(args[:2])} falhou:\n{tail}", file=sys.stderr)
        raise DrillFailed(f"{args[0]}_{args[1]}_failed", exit_code=result.returncode)
    return output


def _alembic(ctx: Ctx, url: str, *args: str) -> str:
    env = subprocess_env(ctx.base_env, DATABASE_URL=url, PYTHONDONTWRITEBYTECODE="1")
    log = ctx.work / f"alembic-{args[0]}-{secrets.token_hex(2)}.log"
    return _python_tool(ctx, ["alembic", *args], env, log)


def _revisions(output: str) -> list[str]:
    lines = (line for line in output.splitlines() if not line.startswith("$ "))
    return sorted({rev for line in lines for rev in _REVISION.findall(line)})


class ApiProcess:
    """Instância efêmera da API real (uvicorn), apontada para um banco do ensaio."""

    def __init__(self, ctx: Ctx, database_url: str, app_name: str, label: str) -> None:
        self.ctx = ctx
        self.app_name = app_name
        self.port = free_port()
        self.base = f"http://{LOOPBACK}:{self.port}/api/v1"
        self.log = ctx.work / f"api-{label}.log"
        self.env = subprocess_env(
            ctx.base_env,
            DATABASE_URL=database_url,
            APP_NAME=app_name,
            API_PREFIX="/api/v1",
            DEBUG="false",
            LOG_LEVEL="WARNING",
            PYTHONDONTWRITEBYTECODE="1",
        )
        self.process: subprocess.Popen[bytes] | None = None
        self._opener = direct_opener()

    def __enter__(self) -> ApiProcess:
        with self.log.open("wb") as handle:
            self.process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    LOOPBACK,
                    "--port",
                    str(self.port),
                    "--workers",
                    "1",
                ],
                cwd=REPO_ROOT,
                env=self.env,
                stdout=handle,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
            )
        try:
            self._wait_ready()
        except BaseException:
            self.__exit__()  # __exit__ não roda quando __enter__ falha
            raise
        return self

    def _wait_ready(self) -> None:
        if self.process is None:
            raise DrillFailed("api_not_started")
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise DrillFailed("api_exited", exit_code=self.process.returncode)
            try:
                health = self.request("GET", "/health")
            except (urllib.error.URLError, OSError):
                time.sleep(0.2)
                continue
            # Prova de QUAL instância respondeu: o nome foi definido por este ensaio.
            if health.get("app") != self.app_name:
                raise DrillRefused("api_identity_mismatch")
            return
        raise DrillFailed("api_not_ready")

    def __exit__(self, *exc: object) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=10)

    def request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            self.base + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        with self._opener.open(req, timeout=10) as response:
            body = json.loads(response.read())
        if not isinstance(body, dict):
            raise DrillFailed("api_unexpected_body")
        return body


def _new_cluster(ctx: Ctx, label: str) -> Cluster:
    cluster = Cluster(label=label, run_id=ctx.run_id, pg_bin=ctx.pg_bin, root=ctx.work / label)
    ctx.clusters.append(cluster)
    env = subprocess_env(ctx.base_env)
    cluster.initialize(env)
    ctx.secrets.append(cluster.password)
    cluster.start(env)
    cluster.prove_identity()
    return cluster


def _create_app_database(
    cluster: Cluster, dbname: str, password: str, marker: str | None = None
) -> None:
    from psycopg import sql

    with cluster.connect() as conn:
        conn.execute(
            sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                sql.Identifier(APP_ROLE), sql.Literal(password)
            )
        )
        conn.execute(
            sql.SQL("CREATE DATABASE {} OWNER {} TEMPLATE template0 ENCODING 'UTF8'").format(
                sql.Identifier(dbname), sql.Identifier(APP_ROLE)
            )
        )
        if marker is not None:
            conn.execute(
                sql.SQL("COMMENT ON DATABASE {} IS {}").format(
                    sql.Identifier(dbname), sql.Literal(marker)
                )
            )


def _observe_target(cluster: Cluster, dbname: str) -> dict[str, Any]:
    with cluster.connect(dbname=dbname) as conn:
        comment, owner = conn.execute(
            "SELECT shobj_description(d.oid, 'pg_database'), pg_get_userbyid(d.datdba)"
            " FROM pg_database d WHERE d.datname = current_database()"
        ).fetchone()
        (relations,) = conn.execute(
            "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace"
            " WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')"
            " AND n.nspname NOT LIKE 'pg_toast%%'"
            " AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')"
        ).fetchone()
    return {"comment": comment, "owner": owner, "user_relations": int(relations)}


def _pgpass(ctx: Ctx, cluster: Cluster, dbname: str, password: str) -> dict[str, str]:
    path = ctx.work / f"pgpass-{cluster.label}"
    line = f"{cluster.address()}:{cluster.port}:{dbname}:{APP_ROLE}:{password}\n"
    path.write_text(line, "ascii")
    path.chmod(0o600)
    return subprocess_env(ctx.base_env, PGPASSFILE=str(path), PGCONNECT_TIMEOUT="10")


def _tools(ctx: Ctx) -> dict[str, Any]:
    versions = {
        name: tool_version(pg_binary(ctx.pg_bin, name))
        for name in ("initdb", "pg_ctl", "pg_dump", "pg_restore")
    }
    majors = {major for _, major in versions.values()}
    if len(majors) != 1:
        raise DrillRefused("pg_tools_major_mismatch")
    return {name: version for name, (version, _) in versions.items()} | {"major": majors.pop()}


def _require_same_major(tools: dict[str, Any], *clusters: Cluster) -> None:
    servers = {c.server_major for c in clusters}
    if servers != {tools["major"]}:
        raise DrillRefused("pg_tools_server_major_mismatch")


def parse_toc_listing(text: str) -> tuple[int, str | None]:
    """Entradas do TOC (cabeçalho ``TOC Entries``; na falta dele, linhas de entrada) e
    o instante em que o arquivo foi criado, como o ``pg_restore --list`` os imprime."""
    header = _TOC_ENTRIES.search(text)
    entries = (
        int(header.group(1))
        if header
        else sum(1 for line in text.splitlines() if line[:1].isdigit())
    )
    created = _ARCHIVE_CREATED.search(text)
    return entries, created.group(1).strip() if created else None


def _list_archive(ctx: Ctx, artifact: Path) -> tuple[int, str | None]:
    log = ctx.work / f"pg_restore-list-{secrets.token_hex(3)}.log"
    restore = pg_binary(ctx.pg_bin, "pg_restore")
    result = run_tool([str(restore), "--list", str(artifact)], env=ctx.base_env, log=log)
    if result.returncode != 0:
        raise DrillFailed("artifact_toc_invalid", exit_code=result.returncode)
    return parse_toc_listing(log.read_text(encoding="utf-8", errors="replace"))


def _write_synthetic_record(ctx: Ctx, url: str) -> dict[str, Any]:
    """Grava o achado sintético pelo caminho normal da aplicação (API real) e o relê."""
    code = f"DRILL-{ctx.run_id}"
    title = f"Ensaio de recuperação {ctx.run_id}"
    with ApiProcess(ctx, url, f"Cartorio System - ensaio origem {ctx.run_id}", "origem") as api:
        created = api.request(
            "POST",
            "/audit/findings",
            {
                "finding_code": code,
                "title": title,
                "description": "Registro sintético do ensaio de recuperação (CARTORIO-OPS-1).",
                "category": "SYSTEM",
                "origin": "MANUAL",
                "severity": "LOW",
                "probability": "LOW",
                "impact": "LOW",
                "priority": "BACKLOG",
                "evidence_summary": "Ensaio automatizado de bancada.",
                "recommended_action": "Nenhuma -- registro de teste.",
            },
        )
        finding_id = int(created["id"])
        if api.request("GET", f"/audit/findings/{finding_id}").get("finding_code") != code:
            raise DrillFailed("origin_record_not_persisted")
    return {"finding_id": finding_id, "code": code, "title": title}


def _publish_dump(ctx: Ctx, origin: Cluster, password: str) -> tuple[Path, str]:
    """Gera a cópia como a rotina de backup: dump num staging, validação do TOC,
    rename atômico e, só depois, o manifesto no mesmo formato."""
    artifact_dir = ctx.work / "artefato"
    staging = artifact_dir / ".tmp"
    staging.mkdir(parents=True)
    stamp = ctx.clock().strftime("%Y%m%dT%H%M%SZ")
    staged = staging / f"staging-{stamp}.dump"
    result = run_tool(
        [
            str(pg_binary(ctx.pg_bin, "pg_dump")),
            f"--host={origin.address()}",
            f"--port={origin.port}",
            f"--username={APP_ROLE}",
            f"--dbname={ORIGIN_DB}",
            "--format=custom",
            "--no-password",
            f"--file={staged}",
        ],
        env=_pgpass(ctx, origin, ORIGIN_DB, password),
        log=ctx.work / "pg_dump.log",
    )
    if result.returncode != 0:
        raise DrillFailed("pg_dump_failed", exit_code=result.returncode)
    _list_archive(ctx, staged)
    digest = sha256_file(staged)
    final = artifact_dir / f"backup-{stamp}.dump"
    staged.rename(final)
    manifest = {
        "arquivo": final.name,
        "sha256": digest,
        "tamanho_bytes": final.stat().st_size,
        "gerado_em_utc": stamp,
        "database": ORIGIN_DB,
    }
    (artifact_dir / f"backup-{stamp}.json").write_text(json.dumps(manifest, indent=2), "utf-8")
    return artifact_dir, stamp


def _origin_phase(ctx: Ctx, tools: dict[str, Any], heads: list[str]) -> dict[str, Any]:
    origin = _new_cluster(ctx, "origem")
    _require_same_major(tools, origin)
    password = secrets.token_urlsafe(24)
    ctx.secrets.append(password)
    # Sem COMMENT na origem: a identidade dela é a do cluster, e propriedade de banco
    # no dump é só ruído para o pg_restore sem --create.
    _create_app_database(origin, ORIGIN_DB, password)
    url = _db_url(origin, ORIGIN_DB, password)
    _alembic(ctx, url, "upgrade", "head")
    origin_revisions = _revisions(_alembic(ctx, url, "current"))
    if origin_revisions != heads:
        raise DrillFailed("origin_revision_mismatch")
    record = _write_synthetic_record(ctx, url)
    artifact_dir, stamp = _publish_dump(ctx, origin, password)
    ctx.report["origin"] = origin.describe() | {"alembic_revisions": origin_revisions}
    ctx.report["record"] = {
        "finding_id": record["finding_id"],
        "finding_code": record["code"],
        "title": record["title"],
    }
    # Origem desligada antes da restauração: daí em diante o registro só vem do destino.
    if not origin.stop(subprocess_env(ctx.base_env)):
        raise DrillFailed("origin_stop_failed")
    ctx.report["origin"]["stopped_before_restore"] = True
    # A identidade esperada da cópia é a da origem que o próprio ensaio criou.
    return {"dir": artifact_dir, "stamp": stamp, "database": ORIGIN_DB, **record}


def _copy_phase(
    ctx: Ctx, manifest: Path, finding_id: int, code: str, database: str
) -> dict[str, Any]:
    stamp = manifest.name.removeprefix("backup-").removesuffix(".json")
    if parse_stamp(stamp) is None:
        raise DrillRefused("manifest_name_invalid")
    artifact_dir = ctx.work / "artefato"
    artifact_dir.mkdir()
    for name in (manifest.name, f"backup-{stamp}.dump"):
        source = manifest.parent / name
        if not source.is_file() or source.is_symlink():
            raise DrillFailed("copy_incomplete", missing=name)
        shutil.copyfile(source, artifact_dir / name)
    ctx.report["record"] = {"finding_id": finding_id, "code_informed_by_operator": True}
    return {
        "dir": artifact_dir,
        "stamp": stamp,
        "finding_id": finding_id,
        "code": code,
        "database": database,
    }


def _verify_artifact(ctx: Ctx, source: dict[str, Any]) -> Path:
    """Mesma validação do verificador, inclusive o banco esperado — antes de restaurar."""
    evaluation = evaluate_publication(
        source["dir"], source["stamp"], ctx.clock(), source["database"]
    )
    if evaluation.reason == "database_mismatch":
        raise DrillRefused("database_mismatch")
    if evaluation.state != "valid":
        raise DrillFailed("artifact_not_verified", evaluation=evaluation.reason)
    artifact = source["dir"] / f"backup-{source['stamp']}.dump"
    entries, created_at = _list_archive(ctx, artifact)
    ctx.report["artifact"] = {
        "file": artifact.name,
        "sha256": evaluation.facts.get("sha256"),
        "size_bytes": evaluation.facts.get("size_bytes"),
        "toc_entries": entries,
        "archive_created_at": created_at,
        "recovery_point_utc": evaluation.facts.get("recovery_point_utc"),
        "manifest_format": "rotina_backup_homologacao",
        "verifier_evaluation": evaluation.reason,
        "database_matched": True,
    }
    return artifact


def _pg_restore(ctx: Ctx, target: Cluster, password: str, artifact: Path) -> None:
    """Mesmas opções do procedimento já validado na homologação."""
    result = run_tool(
        [
            str(pg_binary(ctx.pg_bin, "pg_restore")),
            f"--host={target.address()}",
            f"--port={target.port}",
            f"--username={APP_ROLE}",
            f"--dbname={TARGET_DB}",
            "--single-transaction",
            "--no-owner",
            "--no-privileges",
            "--exit-on-error",
            "--no-password",
            str(artifact),
        ],
        env=_pgpass(ctx, target, TARGET_DB, password),
        log=ctx.work / "pg_restore.log",
        timeout=600,
    )
    if result.returncode != 0:
        raise DrillFailed("pg_restore_failed", exit_code=result.returncode)


def _restore_phase(
    ctx: Ctx, tools: dict[str, Any], heads: list[str], artifact: Path, source: dict[str, Any]
) -> None:
    ctx.mark("recovery_start")
    recovery_started = ctx.clock()
    target = _new_cluster(ctx, "destino")
    _require_same_major(tools, target)
    origin_ids = {c.system_identifier for c in ctx.clusters if c is not target}
    if target.system_identifier in origin_ids:
        raise DrillRefused("target_identity_not_distinct")
    distinct = True if origin_ids else None  # modo cópia: não há origem nesta bancada
    password = secrets.token_urlsafe(24)
    ctx.secrets.append(password)
    marker = f"cartorio-ops-drill:{ctx.run_id}:destino"
    _create_app_database(target, TARGET_DB, password, marker)
    verify_restore_target(
        expected_marker=marker, expected_owner=APP_ROLE, observed=_observe_target(target, TARGET_DB)
    )
    ctx.mark("target_ready")

    _pg_restore(ctx, target, password, artifact)
    ctx.mark("restored")

    url = _db_url(target, TARGET_DB, password)
    target_revisions = _revisions(_alembic(ctx, url, "current"))
    if target_revisions != heads:
        raise DrillFailed("target_revision_mismatch")
    if "No new upgrade operations detected." not in _alembic(ctx, url, "check"):
        raise DrillFailed("target_schema_drift")
    ctx.mark("alembic_verified")

    app_name = f"Cartorio System - ensaio destino {ctx.run_id}"
    with ApiProcess(ctx, url, app_name, "destino") as api:
        ctx.mark("api_ready")
        fetched = api.request("GET", f"/audit/findings/{source['finding_id']}")
        if fetched.get("finding_code") != source["code"]:
            raise DrillFailed("record_mismatch")
        if "title" in source and fetched.get("title") != source["title"]:
            raise DrillFailed("record_mismatch")
        ctx.mark("queried")
        first_query = ctx.clock()

    ctx.report["destination"] = target.describe() | {
        "alembic_revisions": target_revisions,
        "alembic_check": "no_drift",
        "distinct_from_origin": distinct,
        "api_app_name_confirmed": True,
        "database_marker_confirmed": True,
    }
    ctx.report["record"]["matched_on_destination"] = True
    ctx.report["recovery"] = {
        "started_at": utc_iso(recovery_started),
        "first_successful_query_at": utc_iso(first_query),
        "duration_seconds": ctx.span("recovery_start", "queried"),
        "phases_seconds": {
            "provision_destination": ctx.span("recovery_start", "target_ready"),
            "pg_restore": ctx.span("target_ready", "restored"),
            "alembic_verification": ctx.span("restored", "alembic_verified"),
            "api_startup": ctx.span("alembic_verified", "api_ready"),
            "record_query": ctx.span("api_ready", "queried"),
        },
    }


def run_drill(args: argparse.Namespace, *, clock: Clock = utc_now) -> int:
    started = clock()
    run_id = f"{started.strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(3)}"
    report: dict[str, Any] = {
        "schema": RESTORE_DRILL_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "mode": "artifact" if args.from_manifest else "synthetic",
        "classification": (
            "isolated_restore_measurement" if args.from_manifest else "bench_measurement"
        ),
        "started_at": utc_iso(started),
    }
    ctx: Ctx | None = None
    verdict, reason, facts = "passed", "ok", {}
    try:
        require_clean_libpq_env(os.environ)
        if not (REPO_ROOT / "alembic" / "versions").is_dir():
            raise DrillRefused("repo_root_not_checkout")
        report["release"] = _git_release()
        heads, _ = release_heads(REPO_ROOT)
        report["release"]["alembic_heads"] = heads
        ctx = Ctx(
            run_id=run_id,
            pg_bin=args.pg_bin,
            work=create_work_dir(args.work_root, run_id),
            clock=clock,
            base_env=subprocess_env(os.environ),
            report=report,
        )
        tools = _tools(ctx)
        report["postgres"] = {"tools": tools}
        if args.from_manifest:
            source = _copy_phase(
                ctx,
                args.from_manifest,
                args.expect_finding_id,
                args.expect_finding_code,
                args.expect_database,
            )
        else:
            source = _origin_phase(ctx, tools, heads)
        artifact = _verify_artifact(ctx, source)
        if args.export_artifact:  # o parser só aceita no modo sintético
            args.export_artifact.mkdir(parents=True, exist_ok=True)
            for item in source["dir"].glob(f"backup-{source['stamp']}.*"):
                shutil.copyfile(item, args.export_artifact / item.name)
            report["artifact"]["exported"] = True
        _restore_phase(ctx, tools, heads, artifact, source)
        report["postgres"]["server_version"] = ctx.clusters[-1].server_version
        report["postgres"]["server_major"] = ctx.clusters[-1].server_major
    except DrillRefused as exc:
        verdict, reason, facts = "refused", exc.reason, exc.facts
    except DrillFailed as exc:
        verdict, reason, facts = "failed", exc.reason, exc.facts
    except Exception as exc:  # relatório e limpeza acontecem em qualquer desfecho
        verdict, reason, facts = "failed", "unexpected_error", {"error_class": type(exc).__name__}
    finally:
        try:
            report["cleanup"] = _cleanup(ctx, keep=args.keep_on_failure and verdict != "passed")
        except Exception as exc:
            report["cleanup"] = {"error_class": type(exc).__name__, "work_dir_removed": False}
    report.update(verdict=verdict, reason=reason, finished_at=utc_iso(clock()))
    if facts:
        report["failure"] = dict(facts)
    write_json_atomic(args.report, report)
    print(json.dumps({k: report.get(k) for k in ("run_id", "mode", "verdict", "reason")}))
    return _EXIT[verdict]


def _cleanup(ctx: Ctx | None, *, keep: bool) -> dict[str, Any]:
    if ctx is None:
        return {"work_dir_created": False}
    env = subprocess_env(ctx.base_env)
    # Lista, não gerador: todo cluster recebe a ordem de parada, mesmo se um falhar.
    stopped = all([cluster.stop(env) for cluster in ctx.clusters])
    if keep:
        print(f"[drill] diretório preservado para diagnóstico: {ctx.work}", file=sys.stderr)
        return {"clusters_stopped": stopped, "work_dir_removed": False, "kept_on_failure": True}
    return {"clusters_stopped": stopped, "work_dir_removed": remove_work_dir(ctx.work, ctx.run_id)}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.ops.drill",
        description="Prova de recuperação em PostgreSQL descartável (bancada).",
    )
    parser.add_argument("--pg-bin", type=Path, required=True, help="binários do PostgreSQL")
    parser.add_argument(
        "--work-root", type=Path, required=True, help="raiz do diretório de trabalho"
    )
    parser.add_argument("--report", type=Path, required=True, help="relatório JSON do ensaio")
    parser.add_argument("--export-artifact", type=Path, help="copia o dump+manifesto para cá")
    parser.add_argument("--from-manifest", type=Path, help="restaura esta cópia em vez da origem")
    parser.add_argument("--expect-finding-id", type=int, help="id do achado conhecido na cópia")
    parser.add_argument("--expect-finding-code", help="código do achado conhecido na cópia")
    parser.add_argument(
        "--expect-database",
        help="banco de que a cópia precisa ser (informado à parte; nunca lido da cópia)",
    )
    parser.add_argument(
        "--keep-on-failure", action="store_true", help="preserva o diretório se reprovar"
    )
    return parser


def main(argv: Sequence[str] | None = None, *, clock: Clock = utc_now) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.from_manifest:
        if args.expect_finding_id is None or not args.expect_finding_code:
            parser.error("--from-manifest exige --expect-finding-id e --expect-finding-code")
        if not args.expect_database or not DATABASE_NAME.match(args.expect_database):
            parser.error("--from-manifest exige --expect-database com um nome de banco válido")
        if args.export_artifact:
            parser.error("--export-artifact só existe no modo sintético")
    elif args.expect_database:
        parser.error("--expect-database só existe no modo cópia (--from-manifest)")
    return run_drill(args, clock=clock)


if __name__ == "__main__":
    raise SystemExit(main())
