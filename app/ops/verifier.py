"""Execução das checagens, isoladas entre si.

Cada checagem tem seus próprios prazos e captura as próprias falhas: um erro
inesperado numa delas vira ``inconclusive``/``unexpected_error`` só nela, e as demais
continuam — o diagnóstico mostra ONDE está o problema.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from typing import Any

from app.ops.backup import ConnectionIdentity, check_backup
from app.ops.checks import check_alembic, check_api, check_database
from app.ops.config import CHECK_NAMES, OpsConfig
from app.ops.report import CheckResult, Clock, Status, build_report, single
from app.ops.systemd import ShowRunner, run_systemctl_show

_SHA = re.compile(r"^[0-9a-f]{40}$")


def release_id(cfg: OpsConfig) -> str | None:
    """Identidade da release consultada: a configurada ou, no layout por SHA
    (``releases/<sha>`` com ``current`` apontando para ela), o nome resolvido."""
    if cfg.release_id:
        return cfg.release_id
    if cfg.release_dir is None:
        return None
    try:
        name = cfg.release_dir.resolve().name
    except OSError:
        return None
    return name if _SHA.match(name) else None


def connection_identity(cfg: OpsConfig, database: CheckResult | None) -> ConnectionIdentity | None:
    """Modo combinado — database e backup na mesma execução, em PostgreSQL: o backup se
    vincula ao banco que a conexão da checagem database abriu. Sem ele observado (conexão
    falhou, checagem quebrou), a identidade fica sem prova."""
    if "database" not in cfg.checks or cfg.expected_dialect != "postgresql":
        return None
    return ConnectionIdentity(database.observed_database if database is not None else None)


def run_checks(
    cfg: OpsConfig,
    *,
    clock: Clock,
    runner: ShowRunner = run_systemctl_show,
    invocation_id: str | None = None,
) -> dict[str, Any]:
    now = clock()
    rid = release_id(cfg)
    done: dict[str, CheckResult] = {}  # "database" roda antes de "backup" (CHECK_NAMES)
    planned: dict[str, Callable[[], CheckResult]] = {
        "api": lambda: check_api(cfg, runner=runner),
        "database": lambda: check_database(cfg),
        "alembic": lambda: check_alembic(cfg, release_id=rid),
        "backup": lambda: check_backup(
            cfg,
            now=now,
            runner=runner,
            connection=connection_identity(cfg, done.get("database")),
        ),
    }
    results: list[CheckResult] = []
    for name in CHECK_NAMES:
        if name not in cfg.checks:
            results.append(CheckResult(name, Status.SKIPPED, "not_selected"))
            continue
        start = time.monotonic()
        try:
            result = planned[name]()
        except Exception as exc:  # isolamento: a falha fica nesta checagem
            result = single(
                name,
                "internal",
                Status.INCONCLUSIVE,
                "unexpected_error",
                error_class=type(exc).__name__,
            )
        result.duration_ms = round((time.monotonic() - start) * 1000)
        results.append(result)
        done[name] = result
    errors = sorted({var for problems in cfg.problems.values() for var in problems})
    release = {"id": rid, "dir_configured": cfg.release_dir is not None}
    return build_report(
        results, now, config_errors=errors, release=release, invocation_id=invocation_id
    )
