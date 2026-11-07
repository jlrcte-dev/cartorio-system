"""Leitura somente leitura das cópias publicadas pela rotina de backup existente.

Formato reaproveitado da rotina de homologação, sem alterá-la: cada publicação é
``backup-<carimbo>.dump`` — publicado por rename atômico depois de ``pg_dump`` E
``pg_restore --list`` passarem — seguido de ``backup-<carimbo>.json`` com ``arquivo``,
``sha256``, ``tamanho_bytes``, ``gerado_em_utc`` (o mesmo carimbo ``AAAAMMDDTHHMMSSZ``,
tirado antes do ``pg_dump``: o ponto de recuperação) e ``database``.

Publicação parcial: como o manifesto é escrito DEPOIS do rename (e sem escrita
atômica), ``.dump`` sem ``.json``, ou ``.json`` ilegível, é publicação parcial —
indisponível, nunca contada como cópia. Dentro de ``PARTIAL_GRACE`` (medida pela data
de modificação, único uso dela além de informação auxiliar) ela é tratada como escrita
em andamento; passada a carência, é cópia sem evidência verificável e a checagem falha.

Integridade, presa ao mesmo artefato: a validação estrutural roda na cadência da
rotina, antes de o digest ser gravado; o verificador recalcula o SHA-256 na própria
cadência, e a igualdade prova que o arquivo publicado é, bit a bit, o que foi validado.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from sqlalchemy import exc as sa_exc
from sqlalchemy.engine import make_url

from app.ops.config import OpsConfig, UnitSpec
from app.ops.report import (
    CheckResult,
    Status,
    config_invalid,
    config_missing,
    signal,
    single,
    utc_iso,
)
from app.ops.systemd import ShowRunner, probe_unit, run_systemctl_show

STAMP = r"\d{8}T\d{6}Z"
_MANIFEST = re.compile(rf"^backup-({STAMP})\.json$")
_ARTIFACT = re.compile(rf"^backup-({STAMP})\.dump$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STAGING_DIR = ".tmp"

MAX_MANIFEST_BYTES = 64 * 1024
# Folga para relógios levemente dessincronizados; além disso, horário futuro é inválido.
FUTURE_TOLERANCE = timedelta(minutes=5)
# A rotina grava o manifesto milissegundos depois do rename do dump.
PARTIAL_GRACE = timedelta(minutes=10)
_HASH_CHUNK = 1024 * 1024
_LISTED_LIMIT = 10

RESTORE_DRILL_SCHEMA = "cartorio_system.ops.restore_drill"

# Chaves libpq que, na querystring da DSN, trocam ou escondem o banco efetivo.
_DATABASE_OVERRIDES = {"dbname", "service", "servicefile"}


def parse_stamp(text: object) -> datetime | None:
    if not isinstance(text, str) or not re.fullmatch(STAMP, text):
        return None
    try:
        return datetime.strptime(text, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_HASH_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class Evaluation:
    """Uma publicação. ``state``: valid | invalid | unavailable | unreadable."""

    stamp: str
    state: str
    reason: str
    facts: dict[str, Any] = field(default_factory=dict)
    recovery_point: datetime | None = None


def _regular_file_inside(directory: Path, name: str) -> tuple[Path | None, str | None]:
    """Recusa nome com separador ou ``..``, link simbólico e o que resolva fora do
    diretório configurado."""
    if not name or name != Path(name).name or name in (".", "..") or "\\" in name:
        return None, "reference_outside_dir"
    path = directory / name
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None, "artifact_missing"
    if stat.S_ISLNK(info.st_mode) or path.resolve().parent != directory.resolve():
        return None, "reference_outside_dir"
    if not stat.S_ISREG(info.st_mode):
        return None, "artifact_not_regular"
    return path, None


def database_from_dsn(url_text: str | None) -> tuple[str | None, str | None]:
    """Banco que a DSN PostgreSQL nomeia sem ambiguidade: ``(nome, None)`` ou
    ``(None, motivo)``. Banco ausente na DSN (libpq cairia no usuário ou em
    ``PGDATABASE``) e override na querystring (``dbname``, ``service``) são ambíguos."""
    if url_text is None:
        return None, "expected_database_missing"
    try:
        url = make_url(url_text)
    except (sa_exc.ArgumentError, ValueError):
        return None, "expected_database_ambiguous"
    if url.get_backend_name() != "postgresql" or not url.database:
        return None, "expected_database_ambiguous"
    # keep_blank_values: `?dbname=` vazio também é override.
    query = urlsplit(url_text, allow_fragments=False).query
    keys = {key.lower() for key, _ in parse_qsl(query, keep_blank_values=True)}
    if keys & _DATABASE_OVERRIDES:
        return None, "expected_database_ambiguous"
    return url.database, None


def expected_database(cfg: OpsConfig) -> tuple[str | None, str | None]:
    """Banco de que as publicações precisam ser: o explícito e/ou o da DSN.

    Se os dois existem, precisam coincidir. Com a DSN ambígua, só o explícito vale.
    """
    from_dsn, dsn_problem = database_from_dsn(cfg.database_url)
    explicit = cfg.backup_expected_database
    if explicit and from_dsn and explicit != from_dsn:
        return None, "expected_database_conflict"
    if explicit:
        return explicit, None
    if from_dsn:
        return from_dsn, None
    return None, dsn_problem


def evaluate_publication(
    directory: Path, stamp: str, now: datetime, expected_database: str
) -> Evaluation:
    """Avalia ``backup-<stamp>.json`` e o artefato que ele referencia. O manifesto é a
    evidência: o campo ``database`` precisa ser o banco esperado."""
    manifest_path = directory / f"backup-{stamp}.json"
    try:
        info = manifest_path.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            return Evaluation(stamp, "invalid", "reference_outside_dir")
        if info.st_size > MAX_MANIFEST_BYTES:
            return Evaluation(stamp, "invalid", "manifest_invalid")
        raw = manifest_path.read_bytes()
    except FileNotFoundError:
        return Evaluation(stamp, "unavailable", "manifest_missing")
    except PermissionError:
        return Evaluation(stamp, "unreadable", "manifest_unreadable")
    try:
        manifest = json.loads(raw)
    except (UnicodeDecodeError, ValueError):
        return Evaluation(stamp, "unavailable", "manifest_unparseable")
    if not isinstance(manifest, dict):
        return Evaluation(stamp, "invalid", "manifest_invalid")

    name = manifest.get("arquivo")
    digest = manifest.get("sha256")
    size = manifest.get("tamanho_bytes")
    generated = manifest.get("gerado_em_utc")
    database = manifest.get("database")
    if not isinstance(name, str) or not isinstance(database, str) or not database:
        return Evaluation(stamp, "invalid", "manifest_incomplete")
    if not isinstance(digest, str) or not _SHA256.match(digest):
        return Evaluation(stamp, "invalid", "manifest_incomplete")
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        return Evaluation(stamp, "invalid", "manifest_incomplete")

    artifact, problem = _regular_file_inside(directory, name)
    if problem == "reference_outside_dir":
        return Evaluation(stamp, "invalid", problem)
    if not _ARTIFACT.match(name) or name != f"backup-{stamp}.dump" or generated != stamp:
        return Evaluation(stamp, "invalid", "manifest_inconsistent")

    recovery_point = parse_stamp(generated)
    if recovery_point is None:
        return Evaluation(stamp, "invalid", "recovery_point_unreadable")
    facts: dict[str, Any] = {"file": name, "recovery_point_utc": utc_iso(recovery_point)}
    if recovery_point > now + FUTURE_TOLERANCE:
        return Evaluation(stamp, "invalid", "recovery_point_in_future", facts)
    if database != expected_database:
        # Sem os nomes na saída: o motivo basta, e o nome real é inventário interno.
        return Evaluation(stamp, "invalid", "database_mismatch", facts)
    if problem is not None or artifact is None:
        return Evaluation(stamp, "invalid", problem or "artifact_missing", facts)

    artifact_info = artifact.stat()
    facts["size_bytes"] = artifact_info.st_size
    facts["mtime_utc"] = utc_iso(datetime.fromtimestamp(artifact_info.st_mtime, tz=UTC))
    if artifact_info.st_size != size:
        return Evaluation(stamp, "invalid", "size_mismatch", facts, recovery_point)
    try:
        observed = sha256_file(artifact)
    except PermissionError:
        return Evaluation(stamp, "unreadable", "artifact_unreadable", facts, recovery_point)
    facts["sha256"] = observed
    if observed != digest:
        return Evaluation(stamp, "invalid", "digest_mismatch", facts, recovery_point)
    return Evaluation(stamp, "valid", "digest_verified", facts, recovery_point)


@dataclass
class Scan:
    manifests: dict[str, Path]
    artifacts: dict[str, Path]
    staging_files: int
    staging_oldest: datetime | None


def scan_directory(directory: Path) -> Scan:
    manifests: dict[str, Path] = {}
    artifacts: dict[str, Path] = {}
    staging_files = 0
    staging_oldest: datetime | None = None
    with os.scandir(directory) as entries:
        for entry in entries:
            if entry.name == _STAGING_DIR and entry.is_dir(follow_symlinks=False):
                with os.scandir(entry.path) as staged:
                    for item in staged:
                        staging_files += 1
                        mtime = datetime.fromtimestamp(
                            item.stat(follow_symlinks=False).st_mtime, tz=UTC
                        )
                        staging_oldest = min(staging_oldest or mtime, mtime)
            elif match := _MANIFEST.match(entry.name):
                manifests[match.group(1)] = Path(entry.path)
            elif match := _ARTIFACT.match(entry.name):
                artifacts[match.group(1)] = Path(entry.path)
    return Scan(manifests, artifacts, staging_files, staging_oldest)


def _mtime(path: Path) -> datetime | None:
    try:
        return datetime.fromtimestamp(path.lstat().st_mtime, tz=UTC)
    except OSError:
        return None


def _partial(path: Path, reason: str, now: datetime) -> dict[str, Any]:
    mtime = _mtime(path)
    pending = mtime is not None and now - mtime <= PARTIAL_GRACE
    stamp = path.stem.removeprefix("backup-")
    return {"file": path.name, "reason": reason, "pending": pending, "stamp": stamp}


def _parse_iso(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None


def restore_signal(
    path: Path | None, max_age_days: float | None, last_sha256: str | None, now: datetime
) -> dict[str, Any]:
    """Restauração efetivamente testada — sinal distinto de cópia recente e íntegra.

    Lê o relatório do ensaio (``app.ops.drill``); com ``max_age_days``, vencido falha.
    """
    if path is None:
        return signal(Status.NOT_CONFIGURED, "not_configured")
    try:
        if path.stat().st_size > MAX_MANIFEST_BYTES:
            return signal(Status.INCONCLUSIVE, "restore_evidence_invalid")
        evidence = json.loads(path.read_bytes())
    except FileNotFoundError:
        return signal(Status.INCONCLUSIVE, "restore_evidence_missing")
    except (OSError, UnicodeDecodeError, ValueError):
        return signal(Status.INCONCLUSIVE, "restore_evidence_unreadable")
    if not isinstance(evidence, dict) or evidence.get("schema") != RESTORE_DRILL_SCHEMA:
        return signal(Status.INCONCLUSIVE, "restore_evidence_invalid")
    finished = _parse_iso(evidence.get("finished_at"))
    if finished is None or finished > now + FUTURE_TOLERANCE:
        return signal(Status.INCONCLUSIVE, "restore_evidence_invalid")
    artifact = evidence.get("artifact")
    tested_sha = artifact.get("sha256") if isinstance(artifact, dict) else None
    facts = {
        "tested_at_utc": utc_iso(finished),
        "age_days": round((now - finished).total_seconds() / 86400, 2),
        "max_age_days": max_age_days,
        "mode": evidence.get("mode"),
        "classification": evidence.get("classification"),
        "same_artifact_as_last_copy": last_sha256 is not None and tested_sha == last_sha256,
    }
    if evidence.get("verdict") != "passed":
        return signal(Status.FAIL, "restore_test_failed", **facts)
    if max_age_days is not None and facts["age_days"] > max_age_days:
        return signal(Status.FAIL, "restore_test_stale", **facts)
    return signal(Status.OK, "restore_verified", **facts)


def _unit_signal(cfg: OpsConfig, unit: str | None, kind: str, runner: ShowRunner) -> dict[str, Any]:
    if unit is None:
        return signal(Status.NOT_CONFIGURED, "not_configured")
    result = probe_unit(
        UnitSpec(name=unit, kind=kind),
        systemctl=cfg.systemctl,
        timeout=cfg.timeout_seconds * 2,
        runner=runner,
    )
    if kind == "oneshot" and result["reason"] == "last_run_failed":
        result["reason"] = "last_attempt_failed"
    return result


# Problemas do ARTEFATO com manifesto utilizável: a cópia existe, mas não é a publicada.
_ARTIFACT_PROBLEMS = ("size_mismatch", "digest_mismatch")


def _copy_signals(latest: Evaluation | None, anything: bool) -> dict[str, dict[str, Any]]:
    """``last_copy`` e ``integrity`` da publicação completa mais nova."""
    if latest is None:
        reason = "no_verifiable_copy" if anything else "backup_missing"
        return {
            "last_copy": signal(Status.FAIL, reason),
            "integrity": signal(Status.NOT_EVALUATED, "no_copy"),
        }
    if latest.reason == "manifest_unreadable":
        return {
            "last_copy": signal(Status.INCONCLUSIVE, latest.reason),
            "integrity": signal(Status.NOT_EVALUATED, "manifest_not_usable"),
        }
    if latest.state == "invalid" and latest.reason not in _ARTIFACT_PROBLEMS:
        return {
            "last_copy": signal(Status.FAIL, latest.reason, **latest.facts),
            "integrity": signal(Status.NOT_EVALUATED, "manifest_not_usable"),
        }
    if latest.state == "valid":
        integrity = signal(
            Status.OK,
            "digest_verified",
            sha256=latest.facts.get("sha256"),
            evidence="sha256_recomputed_matches_manifest",
        )
    elif latest.state == "unreadable":
        integrity = signal(Status.INCONCLUSIVE, latest.reason)
    else:
        integrity = signal(Status.FAIL, latest.reason, **latest.facts)
    return {"last_copy": signal(Status.OK, "complete", **latest.facts), "integrity": integrity}


def _age_signals(
    last_valid: Evaluation | None, now: datetime, max_age: float
) -> dict[str, dict[str, Any]]:
    """``last_valid_copy`` e ``age``, medida pelo ponto de recuperação, nunca pelo mtime."""
    if last_valid is None or last_valid.recovery_point is None:
        return {
            "last_valid_copy": signal(Status.FAIL, "no_valid_copy"),
            "age": signal(Status.NOT_EVALUATED, "no_valid_copy", max_age_hours=max_age),
        }
    point = last_valid.recovery_point
    age = round((now - point).total_seconds() / 3600, 3)
    fresh = age <= max_age
    return {
        "last_valid_copy": signal(Status.OK, "available", age_hours=age, **last_valid.facts),
        "age": signal(
            Status.OK if fresh else Status.FAIL,
            "within_max_age" if fresh else "backup_stale",
            age_hours=age,
            max_age_hours=max_age,
            recovery_point_utc=utc_iso(point),
        ),
    }


def check_backup(
    cfg: OpsConfig, *, now: datetime, runner: ShowRunner = run_systemctl_show
) -> CheckResult:
    if problems := cfg.problems_for("backup"):
        return config_invalid("backup", problems)
    directory, max_age = cfg.backup_dir, cfg.backup_max_age_hours
    if directory is None or max_age is None:
        missing = []
        if directory is None:
            missing.append("CARTORIO_OPS_BACKUP_DIR")
        if max_age is None:
            missing.append("CARTORIO_OPS_BACKUP_MAX_AGE_HOURS")
        return config_missing("backup", missing)
    expected, problem = expected_database(cfg)
    if expected is None:
        return single(
            "backup",
            "expected_database",
            Status.INCONCLUSIVE,
            problem or "expected_database_missing",
            variables=["CARTORIO_OPS_BACKUP_EXPECTED_DATABASE", "DATABASE_URL"],
        )
    try:
        scan = scan_directory(directory)
    except (FileNotFoundError, NotADirectoryError):
        return single("backup", "directory", Status.INCONCLUSIVE, "backup_dir_unavailable")
    except PermissionError:
        return single("backup", "directory", Status.INCONCLUSIVE, "backup_dir_unreadable")

    partial = [
        _partial(path, "manifest_missing", now)
        for stamp, path in scan.artifacts.items()
        if stamp not in scan.manifests
    ]
    latest: Evaluation | None = None
    last_valid: Evaluation | None = None
    invalid_between: list[dict[str, str]] = []
    for stamp in sorted(scan.manifests, reverse=True):
        evaluation = evaluate_publication(directory, stamp, now, expected)
        if evaluation.state == "unavailable":
            partial.append(_partial(scan.manifests[stamp], evaluation.reason, now))
            continue
        if latest is None:
            latest = evaluation
        elif evaluation.state != "valid":
            invalid_between.append({"stamp": stamp, "reason": evaluation.reason})
        if evaluation.state == "valid":
            last_valid = evaluation
            break
    partial.sort(key=lambda item: item["stamp"], reverse=True)

    # Parcial mais nova que a última publicação completa e fora da carência: a rotina
    # deixou uma cópia sem evidência verificável no lugar da cópia mais recente.
    newest_complete = latest.stamp if latest else ""
    unverifiable = [p for p in partial if p["stamp"] > newest_complete and not p["pending"]]
    last_sha = latest.facts.get("sha256") if latest and latest.state == "valid" else None
    # A ordem dos sinais é a prioridade do motivo exibido (ver CheckResult.from_signals).
    signals = {
        **_copy_signals(latest, bool(scan.manifests or scan.artifacts)),
        "publications": signal(
            Status.FAIL if unverifiable else Status.OK,
            "unverifiable_copy" if unverifiable else "no_unverifiable_copy",
            partial=[{k: v for k, v in p.items() if k != "stamp"} for p in partial[:_LISTED_LIMIT]],
            invalid_newer_than_last_valid=invalid_between[:_LISTED_LIMIT],
            staging_files=scan.staging_files,
            staging_oldest_utc=utc_iso(scan.staging_oldest) if scan.staging_oldest else None,
        ),
        **_age_signals(last_valid, now, max_age),
        "last_attempt": _unit_signal(cfg, cfg.backup_service_unit, "oneshot", runner),
        "timer": _unit_signal(cfg, cfg.backup_timer_unit, "timer", runner),
        "restore_test": restore_signal(
            cfg.restore_evidence, cfg.restore_max_age_days, last_sha, now
        ),
    }
    return CheckResult.from_signals("backup", signals, empty_reason="no_signal")
