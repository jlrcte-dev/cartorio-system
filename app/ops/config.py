"""Configuração explícita do verificador, lida só do ambiente do processo.

Não usa ``app.core.config``: aquele ``Settings`` também lê um ``.env`` do diretório
corrente, e o verificador não pode depender de um arquivo implícito. Também não tem
padrão para o que define o aceite (limite de idade do backup, alvos): ausência vira
``config_missing`` na checagem afetada, nunca um valor presumido.

Erros de valor são registrados pelo NOME da variável — o valor pode ser uma DSN.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

PREFIX = "CARTORIO_OPS_"
CHECK_NAMES: tuple[str, ...] = ("api", "database", "alembic", "backup")
UNIT_KINDS = ("service", "oneshot", "timer")
DIALECTS = ("postgresql", "sqlite")

DEFAULT_TIMEOUT_SECONDS = 5.0
MAX_TIMEOUT_SECONDS = 60.0

_UNIT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:_.@-]*\.(service|timer)$")
_RELEASE_ID = re.compile(r"^[0-9a-f]{7,40}$")
# Nome de banco PostgreSQL: até 63 bytes, sem espaço nem caractere de controle.
DATABASE_NAME = re.compile(r"^[^\x00-\x20\x7f]{1,63}$")


@dataclass(frozen=True)
class UnitSpec:
    name: str
    kind: str


@dataclass(frozen=True)
class OpsConfig:
    checks: tuple[str, ...] = CHECK_NAMES
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    systemctl: str = "systemctl"
    health_url: str | None = None
    expected_app_name: str | None = None
    units: tuple[UnitSpec, ...] = ()
    database_url: str | None = None
    expected_dialect: str = "postgresql"
    release_dir: Path | None = None
    release_id: str | None = None
    backup_dir: Path | None = None
    backup_max_age_hours: float | None = None
    backup_expected_database: str | None = None
    backup_service_unit: str | None = None
    backup_timer_unit: str | None = None
    restore_evidence: Path | None = None
    restore_max_age_days: float | None = None
    # nome da checagem (ou "global") -> variáveis com valor inválido
    problems: dict[str, list[str]] = field(default_factory=dict)

    def problems_for(self, check: str) -> list[str]:
        return sorted(self.problems.get("global", []) + self.problems.get(check, []))


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _positive_float(raw: str | None, upper: float | None = None) -> float | None:
    if raw is None:
        return None
    value = float(raw)  # ValueError se não for número
    if not math.isfinite(value) or value <= 0 or (upper is not None and value > upper):
        raise ValueError("out of range")
    return value


def _absolute_path(raw: str | None) -> Path | None:
    if raw is None:
        return None
    path = Path(raw)
    if not path.is_absolute():
        raise ValueError("relative path")
    return path


def database_name(raw: str | None) -> str | None:
    if raw is None:
        return None
    if not DATABASE_NAME.match(raw):
        raise ValueError("invalid database name")
    return raw


def _unit_name(raw: str | None, suffix: str | None = None) -> str | None:
    if raw is None:
        return None
    if not _UNIT_NAME.match(raw) or (suffix and not raw.endswith(suffix)):
        raise ValueError("invalid unit name")
    return raw


def _units(raw: str | None) -> tuple[UnitSpec, ...]:
    if raw is None:
        return ()
    specs: list[UnitSpec] = []
    for item in raw.split(","):
        name, sep, kind = item.strip().partition(":")
        if not sep or kind not in UNIT_KINDS:
            raise ValueError("expected name:kind")
        _unit_name(name, ".timer" if kind == "timer" else ".service")
        specs.append(UnitSpec(name=name, kind=kind))
    return tuple(specs)


def _health_url(raw: str | None) -> str | None:
    if raw is None:
        return None
    parts = urlsplit(raw)
    # Só http(s): urllib também abriria file:// e ftp://.
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("invalid url")
    if parts.username or parts.password:
        raise ValueError("credentials in url")
    return raw


def load_config(environ: Mapping[str, str]) -> OpsConfig:
    """Nunca lança: valor inválido vira problema da checagem que o usa."""
    problems: dict[str, list[str]] = {}
    values: dict[str, Any] = {}

    def read(name: str) -> str | None:
        return _blank_to_none(environ.get(name))

    def parse(
        checks: tuple[str, ...], key: str, var: str, parser: Callable[..., Any], *args: object
    ) -> None:
        try:
            values[key] = parser(read(var), *args)
        except ValueError:
            for check in checks:
                problems.setdefault(check, []).append(var)

    raw_checks = read(f"{PREFIX}CHECKS")
    if raw_checks is not None:
        selected = tuple(dict.fromkeys(c.strip() for c in raw_checks.split(",") if c.strip()))
        if not selected or any(c not in CHECK_NAMES for c in selected):
            problems.setdefault("global", []).append(f"{PREFIX}CHECKS")
        else:
            values["checks"] = selected

    parse(
        ("global",),
        "timeout_seconds",
        f"{PREFIX}TIMEOUT_SECONDS",
        _positive_float,
        MAX_TIMEOUT_SECONDS,
    )
    values["systemctl"] = read(f"{PREFIX}SYSTEMCTL")

    parse(("api",), "health_url", f"{PREFIX}HEALTH_URL", _health_url)
    values["expected_app_name"] = read(f"{PREFIX}EXPECTED_APP_NAME")
    parse(("api",), "units", f"{PREFIX}UNITS", _units)

    # A mesma variável do app: apontar o EnvironmentFile do verificador para o db.env
    # do serviço faz a checagem provar a DSN que o app usa, sem duplicar a credencial.
    values["database_url"] = read("DATABASE_URL")
    dialect = read(f"{PREFIX}EXPECTED_DIALECT")
    if dialect is not None and dialect not in DIALECTS:
        for check in ("database", "alembic"):
            problems.setdefault(check, []).append(f"{PREFIX}EXPECTED_DIALECT")
    else:
        values["expected_dialect"] = dialect

    parse(("alembic",), "release_dir", f"{PREFIX}RELEASE_DIR", _absolute_path)
    release_id = read(f"{PREFIX}RELEASE_ID")
    if release_id is not None and not _RELEASE_ID.match(release_id):
        problems.setdefault("global", []).append(f"{PREFIX}RELEASE_ID")
    else:
        values["release_id"] = release_id

    backup = ("backup",)
    parse(backup, "backup_dir", f"{PREFIX}BACKUP_DIR", _absolute_path)
    parse(backup, "backup_max_age_hours", f"{PREFIX}BACKUP_MAX_AGE_HOURS", _positive_float)
    parse(backup, "backup_expected_database", f"{PREFIX}BACKUP_EXPECTED_DATABASE", database_name)
    parse(backup, "backup_service_unit", f"{PREFIX}BACKUP_SERVICE_UNIT", _unit_name, ".service")
    parse(backup, "backup_timer_unit", f"{PREFIX}BACKUP_TIMER_UNIT", _unit_name, ".timer")
    parse(backup, "restore_evidence", f"{PREFIX}RESTORE_EVIDENCE", _absolute_path)
    parse(backup, "restore_max_age_days", f"{PREFIX}RESTORE_MAX_AGE_DAYS", _positive_float)

    clean = {k: v for k, v in values.items() if v is not None}
    return OpsConfig(problems=problems, **clean)
