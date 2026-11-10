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

import errno
import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, BinaryIO

from sqlalchemy import exc as sa_exc
from sqlalchemy.engine import make_url

from app.ops.config import DATABASE_NAME, OpsConfig, UnitSpec
from app.ops.report import (
    CheckResult,
    Status,
    config_invalid,
    config_missing,
    signal,
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
# Leitura relativa a um diretório aberto: sem seguir link e sem bloquear num FIFO.
_READ_NOFOLLOW = (
    os.O_RDONLY
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_NONBLOCK", 0)
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_BINARY", 0)
)

RESTORE_DRILL_SCHEMA = "cartorio_system.ops.restore_drill"

# Perfil de serviço da libpq: completa a conexão com parâmetros de fora da DSN.
_SERVICE_KEYS = {"service", "servicefile"}
_NOT_POSTGRESQL = "dsn_not_postgresql"


def parse_stamp(text: object) -> datetime | None:
    if not isinstance(text, str) or not re.fullmatch(STAMP, text):
        return None
    try:
        return datetime.strptime(text, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return _sha256_stream(handle)


def _sha256_stream(handle: BinaryIO) -> str:
    digest = hashlib.sha256()
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


class _NotRegularAnymore(Exception):
    """Entre o ``lstat`` e a abertura, o nome virou link ou outra coisa (só com ``dir_fd``)."""


class _Folder:
    """Onde a publicação é lida. Sem ``fd``, pelo caminho — o verificador, como sempre
    foi. Com ``fd`` (diretório já aberto pelo chamador, POSIX), cada nome é aberto
    relativo a ele e sem seguir link: o caminho não é resolvido de novo, e trocar um
    componente dele depois da abertura não muda o que se lê."""

    def __init__(self, path: Path, fd: int | None) -> None:
        self.path = path
        self.fd = fd

    def lstat(self, name: str) -> os.stat_result:
        if self.fd is None:
            return (self.path / name).lstat()
        return os.stat(name, dir_fd=self.fd, follow_symlinks=False)

    def stat(self, name: str) -> os.stat_result:
        if self.fd is None:
            return (self.path / name).stat()
        return os.stat(name, dir_fd=self.fd, follow_symlinks=False)

    def open(self, name: str) -> BinaryIO:
        if self.fd is None:
            return (self.path / name).open("rb")
        try:
            fd = os.open(name, _READ_NOFOLLOW, dir_fd=self.fd)
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise _NotRegularAnymore from exc
            raise
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise _NotRegularAnymore
        return os.fdopen(fd, "rb")

    def inside(self, name: str) -> bool:
        """Com ``fd``, um nome sem separador que não é link está no diretório aberto por
        construção; pelo caminho, confere a resolução."""
        if self.fd is not None:
            return True
        path = self.path / name
        return path.resolve().parent == self.path.resolve()


def _regular_file_inside(folder: _Folder, name: str) -> tuple[str | None, str | None]:
    """Recusa nome com separador ou ``..``, link simbólico e o que resolva fora do
    diretório configurado."""
    if not name or name != Path(name).name or name in (".", "..") or "\\" in name:
        return None, "reference_outside_dir"
    try:
        info = folder.lstat(name)
    except FileNotFoundError:
        return None, "artifact_missing"
    if stat.S_ISLNK(info.st_mode) or not folder.inside(name):
        return None, "reference_outside_dir"
    if not stat.S_ISREG(info.st_mode):
        return None, "artifact_not_regular"
    return name, None


def database_from_dsn(url_text: str | None) -> tuple[str | None, str | None]:
    """Banco que a DSN PostgreSQL abriria, lido como o dialeto psycopg do SQLAlchemy entrega
    os parâmetros à libpq: ``make_url`` (valor vazio na querystring é descartado), o banco
    do caminho e, por cima, ``dbname`` da querystring. ``(nome, None)`` ou
    ``(None, motivo)``.

    Ambíguo — sem identidade verificável enquanto a conexão não é observada: DSN ilegível,
    perfil de serviço, nenhum ``dbname`` efetivo (a libpq cairia em ``PGDATABASE``, no
    perfil ou no usuário) ou ``dbname`` repetido ou inválido.
    """
    if url_text is None:
        return None, "expected_database_missing"
    try:
        url = make_url(url_text)
    except (sa_exc.ArgumentError, ValueError):
        return None, "expected_database_ambiguous"
    if url.get_backend_name() != "postgresql":
        return None, _NOT_POSTGRESQL
    if {key.lower() for key in url.query} & _SERVICE_KEYS:
        return None, "expected_database_ambiguous"
    name = {**url.translate_connect_args(database="dbname"), **url.query}.get("dbname")
    if not isinstance(name, str) or not DATABASE_NAME.match(name):
        return None, "expected_database_ambiguous"
    return name, None


@dataclass(frozen=True)
class ConnectionIdentity:
    """Modo combinado (database e backup juntos, em PostgreSQL): o banco que a conexão
    somente leitura da checagem database abriu, ou ``None`` se ela não o observou."""

    database: str | None


def expected_database(
    cfg: OpsConfig, connection: ConnectionIdentity | None = None
) -> tuple[str | None, str]:
    """Banco de que as publicações precisam ser: ``(nome, origem)`` ou ``(None, motivo)``.

    Modo combinado: vale o banco que a conexão abriu; o nome explícito e o da DSN, quando
    existem, precisam coincidir com ele. Isolado: o da DSN e/ou o explícito, coincidentes;
    o explícito sozinho só vale sem DSN PostgreSQL (backup isolado, bancada SQLite).
    """
    explicit = cfg.backup_expected_database
    from_dsn, dsn_problem = database_from_dsn(cfg.database_url)
    if connection is not None:
        observed = connection.database
        if observed is None:
            return None, "expected_database_unproven"
        if any(name not in (None, observed) for name in (explicit, from_dsn)):
            return None, "expected_database_conflict"
        return observed, "expected_database_from_connection"
    if from_dsn is not None:
        if explicit is not None and explicit != from_dsn:
            return None, "expected_database_conflict"
        return from_dsn, "expected_database_from_dsn"
    if explicit is not None and dsn_problem in ("expected_database_missing", _NOT_POSTGRESQL):
        return explicit, "expected_database_explicit"
    if dsn_problem == "expected_database_missing":
        return None, dsn_problem
    return None, "expected_database_ambiguous"


def evaluate_publication(
    directory: Path,
    stamp: str,
    now: datetime,
    expected_database: str | None,
    *,
    dir_fd: int | None = None,
) -> Evaluation:
    """Avalia ``backup-<stamp>.json`` e o artefato que ele referencia. O manifesto é a
    evidência: o campo ``database`` precisa ser o banco esperado. Sem banco esperado
    comprovado (``None``) só a identidade fica sem avaliar. ``dir_fd``: ``directory`` já
    aberto pelo chamador; a leitura fica presa a ele (ver :class:`_Folder`)."""
    folder = _Folder(directory, dir_fd)
    manifest = f"backup-{stamp}.json"
    try:
        info = folder.lstat(manifest)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            return Evaluation(stamp, "invalid", "reference_outside_dir")
        if info.st_size > MAX_MANIFEST_BYTES:
            return Evaluation(stamp, "invalid", "manifest_invalid")
        with folder.open(manifest) as handle:
            raw = handle.read()
    except FileNotFoundError:
        return Evaluation(stamp, "unavailable", "manifest_missing")
    except PermissionError:
        return Evaluation(stamp, "unreadable", "manifest_unreadable")
    except _NotRegularAnymore:
        return Evaluation(stamp, "invalid", "reference_outside_dir")
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

    artifact, problem = _regular_file_inside(folder, name)
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
    if expected_database is not None and database != expected_database:
        # Sem os nomes na saída: o motivo basta, e o nome real é inventário interno.
        return Evaluation(stamp, "invalid", "database_mismatch", facts)
    if problem is not None or artifact is None:
        return Evaluation(stamp, "invalid", problem or "artifact_missing", facts)

    artifact_info = folder.stat(artifact)
    facts["size_bytes"] = artifact_info.st_size
    facts["mtime_utc"] = utc_iso(datetime.fromtimestamp(artifact_info.st_mtime, tz=UTC))
    if artifact_info.st_size != size:
        return Evaluation(stamp, "invalid", "size_mismatch", facts, recovery_point)
    try:
        with folder.open(artifact) as handle:
            observed = _sha256_stream(handle)
    except PermissionError:
        return Evaluation(stamp, "unreadable", "artifact_unreadable", facts, recovery_point)
    except _NotRegularAnymore:
        return Evaluation(stamp, "invalid", "reference_outside_dir", facts, recovery_point)
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
    last_valid: Evaluation | None, now: datetime, max_age: float, *, identity_proven: bool
) -> dict[str, dict[str, Any]]:
    """``last_valid_copy`` e ``age``, medida pelo ponto de recuperação, nunca pelo mtime.

    Sem o banco esperado comprovado, a cópia íntegra mais nova pode ser de outro banco: só
    o que vale para qualquer uma delas continua conclusivo — nenhuma cópia íntegra, ou
    todas vencidas.
    """
    if last_valid is None or last_valid.recovery_point is None:
        return {
            "last_valid_copy": signal(Status.FAIL, "no_valid_copy"),
            "age": signal(Status.NOT_EVALUATED, "no_valid_copy", max_age_hours=max_age),
        }
    point = last_valid.recovery_point
    age = round((now - point).total_seconds() / 3600, 3)
    fresh = age <= max_age
    facts = {"age_hours": age, "max_age_hours": max_age, "recovery_point_utc": utc_iso(point)}
    stale = signal(Status.FAIL, "backup_stale", **facts)
    if not identity_proven:
        unproven = signal(Status.NOT_EVALUATED, "expected_database_unresolved")
        return {"last_valid_copy": unproven, "age": unproven if fresh else stale}
    return {
        "last_valid_copy": signal(Status.OK, "available", age_hours=age, **last_valid.facts),
        "age": signal(Status.OK, "within_max_age", **facts) if fresh else stale,
    }


def check_backup(
    cfg: OpsConfig,
    *,
    now: datetime,
    runner: ShowRunner = run_systemctl_show,
    connection: ConnectionIdentity | None = None,
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
    expected, resolution = expected_database(cfg, connection)
    # Sem banco comprovado a checagem nunca é saudável, mas as falhas que independem dele
    # (cópia ausente, vencida, corrompida) continuam aparecendo.
    proven = expected is not None
    identity = (
        signal(Status.OK, resolution)
        if proven
        else signal(
            Status.INCONCLUSIVE,
            resolution,
            variables=["CARTORIO_OPS_BACKUP_EXPECTED_DATABASE", "DATABASE_URL"],
        )
    )
    try:
        scan = scan_directory(directory)
    except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
        reason = (
            "backup_dir_unreadable"
            if isinstance(exc, PermissionError)
            else "backup_dir_unavailable"
        )
        directory_signal = {"directory": signal(Status.INCONCLUSIVE, reason)}
        return CheckResult.from_signals(
            "backup", _with_identity(identity, directory_signal), empty_reason="no_signal"
        )

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
    last_sha = latest.facts.get("sha256") if proven and latest and latest.state == "valid" else None
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
        **_age_signals(last_valid, now, max_age, identity_proven=proven),
        "last_attempt": _unit_signal(cfg, cfg.backup_service_unit, "oneshot", runner),
        "timer": _unit_signal(cfg, cfg.backup_timer_unit, "timer", runner),
        "restore_test": restore_signal(
            cfg.restore_evidence, cfg.restore_max_age_days, last_sha, now
        ),
    }
    return CheckResult.from_signals(
        "backup", _with_identity(identity, signals), empty_reason="no_signal"
    )


def _with_identity(
    identity: dict[str, Any], signals: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Identidade sem prova abre a lista (é o motivo do inconclusivo quando nada falha);
    comprovada vai ao fim e nunca vira o motivo de uma checagem saudável."""
    if identity["status"] == Status.OK.value:
        return {**signals, "expected_database": identity}
    return {"expected_database": identity, **signals}
