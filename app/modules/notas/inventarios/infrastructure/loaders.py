"""Carrega o inventário a partir de YAML/JSON em disco.

A camada de I/O resolve apenas:

- existência e extensão do arquivo;
- desserialização YAML/JSON;
- garantia de que a raiz é um mapping.

A validação estrutural do conteúdo (campos obrigatórios, tipos, ``Decimal``
seguro, ``extra="forbid"``) fica em
:mod:`app.modules.notas.inventarios.interfaces.schemas`. Validações de
**negócio** (soma de percentuais, integridade referencial, política de
centavos) ficam em
:mod:`app.modules.notas.inventarios.application.validator`.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from app.modules.notas.inventarios.domain.errors import InventarioInputError
from app.modules.notas.inventarios.domain.models import Inventario
from app.modules.notas.inventarios.interfaces.schemas import parse_inventario_input

_YAML_EXTS = {".yaml", ".yml"}
_JSON_EXTS = {".json"}


def load_inventario(path: str | Path) -> Inventario:
    p = Path(path)
    if not p.exists():
        raise InventarioInputError(f"arquivo não encontrado: {p}")

    suffix = p.suffix.lower()
    text = p.read_text(encoding="utf-8")

    if suffix in _YAML_EXTS:
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise InventarioInputError(f"YAML inválido em {p}: {exc}") from exc
    elif suffix in _JSON_EXTS:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise InventarioInputError(f"JSON inválido em {p}: {exc}") from exc
    else:
        raise InventarioInputError(
            f"extensão não suportada: '{suffix}' (esperado .yaml, .yml, .json)"
        )

    return inventario_from_mapping(data)


def inventario_from_mapping(data: object) -> Inventario:
    """Valida o mapping com o schema Pydantic e converte para o domínio."""

    return parse_inventario_input(data)
