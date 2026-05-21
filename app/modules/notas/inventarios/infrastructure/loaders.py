"""Carrega o inventário a partir de YAML/JSON em disco.

A entrada é convertida para os modelos imutáveis de `domain.models`. Nenhuma
validação semântica é feita aqui — apenas tipagem e estrutura mínima. Validações
de negócio são responsabilidade de `application.validator`.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml

from app.modules.notas.inventarios.domain.errors import InventarioInputError
from app.modules.notas.inventarios.domain.models import (
    Bem,
    Distribuicao,
    Herdeiro,
    Inventario,
    TipoBem,
)

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

    if not isinstance(data, dict):
        raise InventarioInputError(
            f"raiz do arquivo deve ser um objeto/mapping (recebido: {type(data).__name__})."
        )

    return inventario_from_mapping(data)


def inventario_from_mapping(data: dict[str, Any]) -> Inventario:
    try:
        tipo_ato = str(data["tipo_ato"])
        possui_meeiro = bool(data["possui_meeiro"])
        percentual_meacao = _to_decimal(data.get("percentual_meacao", 0), "percentual_meacao")
        patrimonio_total = _to_decimal(data["patrimonio_total"], "patrimonio_total")
        herdeiros_raw = data["herdeiros"]
        bens_raw = data["bens"]
    except KeyError as exc:
        raise InventarioInputError(f"campo obrigatório ausente: {exc.args[0]}") from exc
    except (TypeError, ValueError) as exc:
        raise InventarioInputError(f"campo com tipo inválido: {exc}") from exc

    if not isinstance(herdeiros_raw, list):
        raise InventarioInputError("'herdeiros' deve ser uma lista.")
    if not isinstance(bens_raw, list):
        raise InventarioInputError("'bens' deve ser uma lista.")

    herdeiros = tuple(_herdeiro_from_mapping(h, i) for i, h in enumerate(herdeiros_raw))
    bens = tuple(_bem_from_mapping(b, i) for i, b in enumerate(bens_raw))

    return Inventario(
        tipo_ato=tipo_ato,
        possui_meeiro=possui_meeiro,
        percentual_meacao=percentual_meacao,
        patrimonio_total=patrimonio_total,
        herdeiros=herdeiros,
        bens=bens,
    )


def _herdeiro_from_mapping(raw: object, idx: int) -> Herdeiro:
    if not isinstance(raw, dict):
        raise InventarioInputError(f"herdeiros[{idx}] deve ser um objeto.")
    try:
        return Herdeiro(
            id=str(raw["id"]),
            percentual_heranca=_to_decimal(
                raw["percentual_heranca"], f"herdeiros[{idx}].percentual_heranca"
            ),
        )
    except KeyError as exc:
        raise InventarioInputError(
            f"herdeiros[{idx}]: campo obrigatório ausente: {exc.args[0]}"
        ) from exc


def _bem_from_mapping(raw: object, idx: int) -> Bem:
    if not isinstance(raw, dict):
        raise InventarioInputError(f"bens[{idx}] deve ser um objeto.")
    try:
        tipo_str = str(raw["tipo"])
        try:
            tipo = TipoBem(tipo_str)
        except ValueError as exc:
            raise InventarioInputError(
                f"bens[{idx}].tipo inválido: '{tipo_str}'. "
                f"Valores aceitos: {[t.value for t in TipoBem]}"
            ) from exc

        distribuicao_raw = raw.get("distribuicao", [])
        if not isinstance(distribuicao_raw, list):
            raise InventarioInputError(f"bens[{idx}].distribuicao deve ser uma lista.")

        distribuicao = tuple(
            _distribuicao_from_mapping(d, idx, di) for di, d in enumerate(distribuicao_raw)
        )

        return Bem(
            id=str(raw["id"]),
            tipo=tipo,
            descricao_generica=str(raw.get("descricao_generica", "")),
            valor=_to_decimal(raw["valor"], f"bens[{idx}].valor"),
            distribuicao=distribuicao,
        )
    except KeyError as exc:
        raise InventarioInputError(
            f"bens[{idx}]: campo obrigatório ausente: {exc.args[0]}"
        ) from exc


def _distribuicao_from_mapping(raw: object, bem_idx: int, dist_idx: int) -> Distribuicao:
    if not isinstance(raw, dict):
        raise InventarioInputError(f"bens[{bem_idx}].distribuicao[{dist_idx}] deve ser um objeto.")
    try:
        return Distribuicao(
            beneficiario=str(raw["beneficiario"]),
            percentual=_to_decimal(
                raw["percentual"],
                f"bens[{bem_idx}].distribuicao[{dist_idx}].percentual",
            ),
        )
    except KeyError as exc:
        raise InventarioInputError(
            f"bens[{bem_idx}].distribuicao[{dist_idx}]: campo obrigatório ausente: {exc.args[0]}"
        ) from exc


def _to_decimal(value: object, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise InventarioInputError(f"'{field_name}' não pode ser booleano (recebido: {value}).")
    if isinstance(value, int | float | str):
        try:
            return Decimal(str(value))
        except InvalidOperation as exc:
            raise InventarioInputError(f"'{field_name}' não é um número válido: {value!r}") from exc
    raise InventarioInputError(
        f"'{field_name}' deve ser numérico (recebido: {type(value).__name__})."
    )
