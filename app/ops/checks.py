"""Checagens de processo/API, PostgreSQL e Alembic — todas somente leitura.

Classificação, comum a todas: ``fail`` quando o verificador obteve evidência de que o
sistema monitorado diverge do esperado (recusa de conexão, HTTP fora de 200, revisão
divergente, unidade parada); ``inconclusive`` quando não conseguiu evidência nenhuma
(configuração ausente ou inválida do próprio verificador, driver ausente, tabela
ilegível). Timeout conta como falha: o serviço não respondeu no prazo combinado.

Nada de mensagem de exceção, DSN, host ou usuário chega à saída: só motivo estável,
nome da classe do erro e, quando o servidor o enviou, o SQLSTATE.
"""

from __future__ import annotations

import http.client
import json
import math
import sqlite3
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import create_engine
from sqlalchemy import exc as sa_exc
from sqlalchemy.engine import Connection, Engine, make_url
from sqlalchemy.pool import NullPool

from app.ops.config import OpsConfig
from app.ops.report import CheckResult, Status, config_invalid, config_missing, signal, single
from app.ops.systemd import ShowRunner, probe_unit, run_systemctl_show

if TYPE_CHECKING:
    from alembic.script import ScriptDirectory

_MAX_HEALTH_BODY = 64 * 1024


# ---------------------------------------------------------------------------
# Processo e API
# ---------------------------------------------------------------------------


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: object, **kwargs: object) -> None:
        return None  # 3xx vira HTTPError: o /health saudável responde 200 direto


def direct_opener() -> urllib.request.OpenerDirector:
    """Sem proxy do ambiente (HTTP(S)_PROXY) e sem seguir redirect: a pergunta é sobre
    ESTE host, e a resposta tem de vir dele."""
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


def probe_health(url: str, *, timeout: float, expected_app: str | None) -> dict[str, Any]:
    opener = direct_opener()
    request = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": "cartorio-ops-verifier/1"}
    )
    start = time.monotonic()
    try:
        with opener.open(request, timeout=timeout) as response:
            status_code = response.status
            body = response.read(_MAX_HEALTH_BODY)
    except urllib.error.HTTPError as exc:
        exc.close()
        return signal(Status.FAIL, "http_status", status_code=exc.code)
    except urllib.error.URLError as exc:
        reason = "timeout" if isinstance(exc.reason, TimeoutError) else "unreachable"
        return signal(Status.FAIL, reason, error_class=type(exc.reason).__name__)
    except TimeoutError:
        return signal(Status.FAIL, "timeout", error_class="TimeoutError")
    except http.client.HTTPException as exc:
        return signal(Status.FAIL, "unexpected_response", error_class=type(exc).__name__)
    except OSError as exc:
        return signal(Status.FAIL, "unreachable", error_class=type(exc).__name__)
    latency_ms = round((time.monotonic() - start) * 1000)

    if status_code != 200:
        return signal(Status.FAIL, "http_status", status_code=status_code)
    try:
        payload = json.loads(body)
    except ValueError:
        payload = None
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        return signal(Status.FAIL, "unexpected_body", status_code=200)
    if expected_app is not None and payload.get("app") != expected_app:
        return signal(Status.FAIL, "app_mismatch", status_code=200)
    version = payload.get("version")
    return signal(
        Status.OK,
        "healthy",
        status_code=200,
        latency_ms=latency_ms,
        app_version=version if isinstance(version, str) else None,
    )


def check_api(cfg: OpsConfig, *, runner: ShowRunner = run_systemctl_show) -> CheckResult:
    if problems := cfg.problems_for("api"):
        return config_invalid("api", problems)
    if cfg.health_url is None and not cfg.units:
        return config_missing("api", ["CARTORIO_OPS_HEALTH_URL", "CARTORIO_OPS_UNITS"])

    signals: dict[str, dict[str, Any]] = {}
    for spec in cfg.units:
        signals[f"unit:{spec.name}"] = probe_unit(
            spec, systemctl=cfg.systemctl, timeout=cfg.timeout_seconds * 2, runner=runner
        )
    if not cfg.units:
        signals["units"] = signal(Status.NOT_CONFIGURED, "not_configured")
    if cfg.health_url is not None:
        signals["health"] = probe_health(
            cfg.health_url, timeout=cfg.timeout_seconds, expected_app=cfg.expected_app_name
        )
    else:
        signals["health"] = signal(Status.NOT_CONFIGURED, "not_configured")
    return CheckResult.from_signals("api", signals, empty_reason="no_signal")


# ---------------------------------------------------------------------------
# Banco: conexão somente leitura comum às checagens database e alembic
# ---------------------------------------------------------------------------


class ProbeError(Exception):
    def __init__(self, status: Status, reason: str, **facts: object) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.facts = facts


def _sqlstate(error: object) -> str | None:
    state = getattr(error, "sqlstate", None)
    if state is None:
        state = getattr(getattr(error, "diag", None), "sqlstate", None)
    return state if isinstance(state, str) and state else None


def classify_db_error(
    error: BaseException, *, elapsed: float, timeout: float, connected: bool
) -> ProbeError:
    orig = getattr(error, "orig", None) or error
    facts: dict[str, Any] = {"error_class": type(orig).__name__}
    state = _sqlstate(orig)
    if state:
        facts["sqlstate"] = state
        if state.startswith("28"):
            return ProbeError(Status.FAIL, "auth_failed", **facts)
        if state == "3D000":
            return ProbeError(Status.FAIL, "database_missing", **facts)
        if state == "57014":
            return ProbeError(Status.FAIL, "timeout", **facts)
        if state.startswith("08") or state == "57P03":
            return ProbeError(Status.FAIL, "unavailable", **facts)
        return ProbeError(Status.FAIL, "query_failed", **facts)
    if connected:
        return ProbeError(Status.FAIL, "query_failed", **facts)
    if isinstance(orig, sqlite3.OperationalError):
        # mode=ro: arquivo ausente ou ilegível (mensagens do SQLite não são traduzidas).
        return ProbeError(Status.FAIL, "database_missing", **facts)
    # Sem resposta do servidor. psycopg sinaliza o prazo esgotado com ConnectionTimeout;
    # no Windows até a recusa em loopback chega assim, porque o driver só desiste no prazo.
    if "Timeout" in type(orig).__name__ or elapsed >= timeout * 0.8:
        return ProbeError(Status.FAIL, "timeout", **facts)
    return ProbeError(Status.FAIL, "unavailable", **facts)


def _build_engine(url_text: str, expected_dialect: str, timeout: float) -> Engine:
    try:
        url = make_url(url_text)
    except (sa_exc.ArgumentError, ValueError) as exc:
        raise ProbeError(Status.INCONCLUSIVE, "config_invalid", detail="url_unparseable") from exc
    backend = url.get_backend_name()
    if backend != expected_dialect:
        raise ProbeError(
            Status.FAIL, "dialect_mismatch", expected=expected_dialect, observed=backend
        )
    try:
        if backend == "postgresql":
            # libpq aceita só segundos inteiros, com mínimo efetivo de 2.
            connect_args = {"connect_timeout": max(2, math.ceil(timeout))}
            return create_engine(url, poolclass=NullPool, connect_args=connect_args)
        database = url.database
        if not database or database == ":memory:" or database.startswith("file:"):
            raise ProbeError(Status.INCONCLUSIVE, "config_invalid", detail="sqlite_path")
        # mode=ro: um verificador somente leitura jamais pode CRIAR o arquivo ausente.
        uri = Path(database).resolve().as_uri() + "?mode=ro"

        def connect() -> sqlite3.Connection:
            return sqlite3.connect(uri, uri=True, timeout=timeout)

        return create_engine("sqlite://", poolclass=NullPool, creator=connect)
    except (sa_exc.NoSuchModuleError, ImportError) as exc:
        raise ProbeError(
            Status.INCONCLUSIVE, "config_invalid", detail="driver_unavailable"
        ) from exc


@contextmanager
def read_only_connection(
    url_text: str, expected_dialect: str, timeout: float
) -> Iterator[Connection]:
    """Conexão real em transação somente leitura, sempre revertida e descartada."""
    engine = _build_engine(url_text, expected_dialect, timeout)
    start = time.monotonic()
    connected = False
    try:
        with engine.connect() as conn:
            connected = True
            if engine.dialect.name == "postgresql":
                conn.exec_driver_sql("SET TRANSACTION READ ONLY")
                conn.exec_driver_sql(f"SET LOCAL statement_timeout = {max(1, int(timeout * 1000))}")
            else:
                conn.exec_driver_sql("PRAGMA query_only = ON")
            yield conn
            conn.rollback()
    except sa_exc.DBAPIError as exc:
        raise classify_db_error(
            exc, elapsed=time.monotonic() - start, timeout=timeout, connected=connected
        ) from exc
    finally:
        engine.dispose()


def _db_preflight(name: str, cfg: OpsConfig) -> CheckResult | None:
    if problems := cfg.problems_for(name):
        return config_invalid(name, problems)
    if cfg.database_url is None:
        return config_missing(name, ["DATABASE_URL"])
    return None


def check_database(cfg: OpsConfig) -> CheckResult:
    if early := _db_preflight("database", cfg):
        return early
    start = time.monotonic()
    observed: str | None = None
    try:
        with read_only_connection(
            cfg.database_url or "", cfg.expected_dialect, cfg.timeout_seconds
        ) as conn:
            if conn.dialect.name == "postgresql":
                # Banco que a DSN abriu de fato, overrides da libpq incluídos: é a ele que a
                # checagem de backup se vincula. O nome fica em memória, fora do relatório.
                observed = str(conn.exec_driver_sql("SELECT current_database()").scalar_one())
            else:
                conn.exec_driver_sql("SELECT 1").scalar_one()
            info = conn.dialect.server_version_info or ()
    except ProbeError as exc:
        return single("database", "connection", exc.status, exc.reason, **exc.facts)
    result = single(
        "database",
        "connection",
        Status.OK,
        "ok",
        dialect=cfg.expected_dialect,
        read_only=True,
        latency_ms=round((time.monotonic() - start) * 1000),
        server_major=info[0] if info else None,
        identity_observed=observed is not None,
    )
    result.observed_database = observed
    return result


# ---------------------------------------------------------------------------
# Alembic: revisão registrada no banco x heads da release consultada
# ---------------------------------------------------------------------------


def release_heads(release_dir: Path) -> tuple[list[str], ScriptDirectory]:
    """Heads declaradas pelas migrations DA RELEASE — lê arquivos, não abre o banco e
    não executa ``env.py``."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    script_location = release_dir / "alembic"
    if not (script_location / "versions").is_dir():
        raise FileNotFoundError("alembic/versions")
    config = Config()
    # "%" no caminho seria interpolado pelo ConfigParser do Alembic.
    config.set_main_option("script_location", str(script_location).replace("%", "%%"))
    script = ScriptDirectory.from_config(config)
    return sorted(script.get_heads()), script


def _read_db_revisions(conn: Connection) -> list[str]:
    try:
        rows = conn.exec_driver_sql("SELECT version_num FROM alembic_version").all()
    except sa_exc.DBAPIError as exc:
        orig = getattr(exc, "orig", None)
        state = _sqlstate(orig)
        missing = state == "42P01" or (
            isinstance(orig, sqlite3.OperationalError) and "no such table" in str(orig)
        )
        facts: dict[str, Any] = {"error_class": type(orig).__name__}
        if state:
            facts["sqlstate"] = state
        reason = "version_table_missing" if missing else "version_table_unreadable"
        raise ProbeError(Status.INCONCLUSIVE, reason, **facts) from exc
    return sorted({str(row[0]) for row in rows})


def compare_revisions(
    db_revs: list[str], heads: list[str], script: ScriptDirectory
) -> tuple[Status, str]:
    if set(db_revs) == set(heads):
        return Status.OK, "revision_match"
    known: set[str] = set()
    for head in heads:
        known.update(rev.revision for rev in script.iterate_revisions(head, "base"))
    if any(rev not in known for rev in db_revs):
        # Revisão que a release não conhece: banco à frente do código ou de outra linhagem.
        return Status.FAIL, "revision_unknown"
    return Status.FAIL, "revision_behind"


def check_alembic(cfg: OpsConfig, *, release_id: str | None) -> CheckResult:
    if early := _db_preflight("alembic", cfg):
        return early
    if cfg.release_dir is None:
        return config_missing("alembic", ["CARTORIO_OPS_RELEASE_DIR"])
    try:
        heads, script = release_heads(cfg.release_dir)
    except Exception as exc:  # qualquer falha ao ler a release é falta de evidência
        return single(
            "alembic",
            "release",
            Status.INCONCLUSIVE,
            "release_unreadable",
            error_class=type(exc).__name__,
        )
    try:
        with read_only_connection(
            cfg.database_url or "", cfg.expected_dialect, cfg.timeout_seconds
        ) as conn:
            db_revs = _read_db_revisions(conn)
    except ProbeError as exc:
        # Banco inacessível já é a falha da checagem "database"; aqui falta evidência.
        reason = exc.reason if exc.reason.startswith("version_table") else "database_unavailable"
        return single(
            "alembic", "revision", Status.INCONCLUSIVE, reason, cause=exc.reason, **exc.facts
        )
    status, reason = compare_revisions(db_revs, heads, script)
    return single(
        "alembic",
        "revision",
        status,
        reason,
        expected_heads=heads,
        db_revisions=db_revs,
        release_id=release_id,
    )
