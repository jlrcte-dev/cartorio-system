"""Renderização dos modelos ``.service``/``.timer`` do verificador.

Os modelos em ``deploy/ops/*.in`` usam marcadores ``@NOME@``. Todo marcador precisa de
valor, todo valor precisa ser usado, e cada valor passa por validação própria — um
caminho relativo, um ``%`` (especificador do systemd) ou uma quebra de linha mudariam
o significado da unidade sem erro visível.
"""

from __future__ import annotations

import re
from pathlib import Path

TEMPLATES = {
    "cartorio-ops-check.service.in": "{prefix}-check.service",
    "cartorio-ops-check.timer.in": "{prefix}-check.timer",
    "cartorio-ops-alert.service.in": "{prefix}-alert.service",
}

_PLACEHOLDER = re.compile(r"@([A-Z][A-Z0-9_]*)@")
_ABSOLUTE = re.compile(r"^/[A-Za-z0-9._/@+-]*$")
_RULES: dict[str, re.Pattern[str]] = {
    "UNIT_PREFIX": re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$"),
    "SERVICE_USER": re.compile(r"^[a-z_][a-z0-9_-]{0,31}$"),
    "SERVICE_GROUP": re.compile(r"^[a-z_][a-z0-9_-]{0,31}$"),
    "RELEASE_DIR": _ABSOLUTE,
    "PYTHON": _ABSOLUTE,
    "CONFIG_FILE": _ABSOLUTE,
    "DB_ENV_FILE": _ABSOLUTE,
    "STATE_DIR_NAME": re.compile(r"^[a-z0-9][a-z0-9._-]{0,62}$"),
    "CHECK_CALENDAR": re.compile(r"^[A-Za-z0-9*:/,.~ -]{1,64}$"),
}


class UnitParamsError(ValueError):
    def __init__(self, problems: list[str]) -> None:
        super().__init__(", ".join(problems))
        self.problems = problems


def load_params(text: str) -> dict[str, str]:
    params: dict[str, str] = {}
    problems: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, sep, value = stripped.partition("=")
        key = key.strip()
        if not sep or not key:
            problems.append(f"linha {number}: esperado CHAVE=valor")
        elif key in params:
            problems.append(f"{key}: repetido")
        else:
            params[key] = value.strip()
    if problems:
        raise UnitParamsError(problems)
    return params


def validate_params(params: dict[str, str]) -> None:
    problems = [f"{key}: ausente" for key in _RULES if key not in params]
    problems += [f"{key}: desconhecido" for key in params if key not in _RULES]
    problems += [
        f"{key}: valor inválido"
        for key, rule in _RULES.items()
        if key in params and not rule.match(params[key])
    ]
    if problems:
        raise UnitParamsError(sorted(problems))


def render_template(text: str, params: dict[str, str]) -> str:
    unknown = sorted({m.group(1) for m in _PLACEHOLDER.finditer(text)} - params.keys())
    if unknown:
        raise UnitParamsError([f"{name}: marcador sem valor" for name in unknown])
    return _PLACEHOLDER.sub(lambda m: params[m.group(1)], text)


def render_units(templates_dir: Path, params: dict[str, str]) -> dict[str, str]:
    validate_params(params)
    rendered: dict[str, str] = {}
    used: set[str] = set()
    for template, target in TEMPLATES.items():
        text = (templates_dir / template).read_text(encoding="utf-8")
        used.update(m.group(1) for m in _PLACEHOLDER.finditer(text))
        rendered[target.format(prefix=params["UNIT_PREFIX"])] = render_template(text, params)
    unused = sorted(params.keys() - used)
    if unused:
        raise UnitParamsError([f"{name}: não usado por nenhum modelo" for name in unused])
    return rendered
