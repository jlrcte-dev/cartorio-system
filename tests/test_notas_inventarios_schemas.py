"""Testes do schema Pydantic v2 do input de inventário.

A camada Pydantic cuida apenas do contrato estrutural; regras de negócio
(soma de percentuais, integridade referencial, política de centavos) seguem
sendo cobertas por ``tests/test_notas_inventarios_validator.py``.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.notas.inventarios.domain.errors import InventarioInputError
from app.modules.notas.inventarios.domain.models import TipoBem
from app.modules.notas.inventarios.interfaces.schemas import (
    InventarioInputSchema,
    parse_inventario_input,
)


def _payload_com_meeiro() -> dict[str, object]:
    return {
        "tipo_ato": "inventario_extrajudicial",
        "possui_meeiro": True,
        "percentual_meacao": "50",
        "patrimonio_total": "1000000.00",
        "herdeiros": [
            {"id": "HERDEIRO_1", "percentual_heranca": "50"},
            {"id": "HERDEIRO_2", "percentual_heranca": "50"},
        ],
        "bens": [
            {
                "id": "IMOVEL_1",
                "tipo": "imovel",
                "descricao_generica": "Imóvel urbano [MATRICULA]",
                "valor": "1000000.00",
                "distribuicao": [
                    {"beneficiario": "MEEIRO", "percentual": "50"},
                    {"beneficiario": "HERDEIRO_1", "percentual": "25"},
                    {"beneficiario": "HERDEIRO_2", "percentual": "25"},
                ],
            }
        ],
    }


def _payload_sem_meeiro() -> dict[str, object]:
    return {
        "tipo_ato": "inventario_extrajudicial",
        "possui_meeiro": False,
        "percentual_meacao": "0",
        "patrimonio_total": "300000.00",
        "herdeiros": [
            {"id": "HERDEIRO_1", "percentual_heranca": "33.33"},
            {"id": "HERDEIRO_2", "percentual_heranca": "33.33"},
            {"id": "HERDEIRO_3", "percentual_heranca": "33.34"},
        ],
        "bens": [
            {
                "id": "IMOVEL_1",
                "tipo": "imovel",
                "descricao_generica": "Imóvel rural [MATRICULA]",
                "valor": "300000.00",
                "distribuicao": [
                    {"beneficiario": "HERDEIRO_1", "percentual": "33.33"},
                    {"beneficiario": "HERDEIRO_2", "percentual": "33.33"},
                    {"beneficiario": "HERDEIRO_3", "percentual": "33.34"},
                ],
            }
        ],
    }


# ---------------------------------------------------------------------------
# Casos válidos
# ---------------------------------------------------------------------------


def test_input_valido_com_meeiro_carrega_no_schema() -> None:
    schema = InventarioInputSchema.model_validate(_payload_com_meeiro())
    assert schema.possui_meeiro is True
    assert schema.percentual_meacao == Decimal("50")
    assert schema.patrimonio_total == Decimal("1000000.00")
    assert len(schema.herdeiros) == 2
    assert schema.bens[0].tipo is TipoBem.IMOVEL


def test_input_valido_sem_meeiro_carrega_no_schema() -> None:
    schema = InventarioInputSchema.model_validate(_payload_sem_meeiro())
    assert schema.possui_meeiro is False
    assert schema.percentual_meacao == Decimal("0")
    assert sum(h.percentual_heranca for h in schema.herdeiros) == Decimal("100.00")


def test_to_inventario_preserva_decimais_e_tipos() -> None:
    inv = parse_inventario_input(_payload_com_meeiro())
    assert inv.tipo_ato == "inventario_extrajudicial"
    assert inv.patrimonio_total == Decimal("1000000.00")
    assert isinstance(inv.percentual_meacao, Decimal)
    assert inv.bens[0].tipo is TipoBem.IMOVEL
    assert inv.bens[0].distribuicao[0].percentual == Decimal("50")


# ---------------------------------------------------------------------------
# Conversão segura de Decimal
# ---------------------------------------------------------------------------


def test_decimal_como_string_e_aceito() -> None:
    payload = _payload_com_meeiro()
    payload["patrimonio_total"] = "1234567.89"
    schema = InventarioInputSchema.model_validate(payload)
    assert schema.patrimonio_total == Decimal("1234567.89")


def test_decimal_como_inteiro_e_aceito() -> None:
    payload = _payload_com_meeiro()
    payload["patrimonio_total"] = 1000000
    schema = InventarioInputSchema.model_validate(payload)
    assert schema.patrimonio_total == Decimal("1000000")


def test_decimal_via_float_e_convertido_com_seguranca() -> None:
    """Garante que ``1000000.00`` (float YAML) vira ``Decimal('1000000.0')``,
    sem o ruído binário típico de ``Decimal(0.1)``."""

    payload = _payload_com_meeiro()
    payload["patrimonio_total"] = 1000000.00
    schema = InventarioInputSchema.model_validate(payload)
    assert schema.patrimonio_total == Decimal("1000000.0")


def test_decimal_booleano_e_rejeitado() -> None:
    """``Decimal(True) == 1`` é uma armadilha — o schema deve recusar."""

    payload = _payload_com_meeiro()
    payload["patrimonio_total"] = True
    with pytest.raises(InventarioInputError, match="patrimonio_total"):
        parse_inventario_input(payload)


# ---------------------------------------------------------------------------
# Campos obrigatórios e extras proibidos
# ---------------------------------------------------------------------------


def test_campo_obrigatorio_ausente_falha() -> None:
    payload = _payload_com_meeiro()
    payload.pop("patrimonio_total")
    with pytest.raises(InventarioInputError, match="patrimonio_total"):
        parse_inventario_input(payload)


def test_campo_extra_proibido_na_raiz() -> None:
    payload = _payload_com_meeiro()
    payload["campo_extra"] = "valor"
    with pytest.raises(InventarioInputError, match="campo_extra"):
        parse_inventario_input(payload)


def test_campo_extra_proibido_em_herdeiro() -> None:
    payload = _payload_com_meeiro()
    payload["herdeiros"][0]["nome_real"] = "João da Silva"  # type: ignore[index]
    with pytest.raises(InventarioInputError, match="nome_real"):
        parse_inventario_input(payload)


def test_campo_extra_proibido_em_bem() -> None:
    payload = _payload_com_meeiro()
    payload["bens"][0]["matricula_real"] = "12345"  # type: ignore[index]
    with pytest.raises(InventarioInputError, match="matricula_real"):
        parse_inventario_input(payload)


# ---------------------------------------------------------------------------
# Restrições estruturais
# ---------------------------------------------------------------------------


def test_tipo_ato_invalido_rejeitado_pelo_schema() -> None:
    payload = _payload_com_meeiro()
    payload["tipo_ato"] = "escritura_qualquer"
    with pytest.raises(InventarioInputError, match="tipo_ato"):
        parse_inventario_input(payload)


def test_tipo_de_bem_invalido_tem_mensagem_clara() -> None:
    payload = _payload_com_meeiro()
    payload["bens"][0]["tipo"] = "criptomoeda_exotica"  # type: ignore[index]
    with pytest.raises(InventarioInputError, match="tipo inválido"):
        parse_inventario_input(payload)


def test_herdeiros_lista_vazia_falha() -> None:
    payload = _payload_com_meeiro()
    payload["herdeiros"] = []
    with pytest.raises(InventarioInputError, match="herdeiros"):
        parse_inventario_input(payload)


def test_bens_lista_vazia_falha() -> None:
    payload = _payload_com_meeiro()
    payload["bens"] = []
    with pytest.raises(InventarioInputError, match="bens"):
        parse_inventario_input(payload)


def test_valor_de_bem_invalido_falha() -> None:
    payload = _payload_com_meeiro()
    payload["bens"][0]["valor"] = "nao_e_numero"  # type: ignore[index]
    with pytest.raises(InventarioInputError, match="valor"):
        parse_inventario_input(payload)


def test_raiz_nao_mapping_falha() -> None:
    with pytest.raises(InventarioInputError, match="objeto/mapping"):
        parse_inventario_input(["lista", "no", "topo"])


def test_id_herdeiro_vazio_falha() -> None:
    payload = _payload_com_meeiro()
    payload["herdeiros"][0]["id"] = ""  # type: ignore[index]
    with pytest.raises(InventarioInputError, match="id"):
        parse_inventario_input(payload)
