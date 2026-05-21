"""Testes das validações estruturais e numéricas do inventário."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.modules.notas.inventarios.application.validator import InventarioValidator
from app.modules.notas.inventarios.domain.errors import InventarioInputError
from app.modules.notas.inventarios.domain.models import (
    BENEFICIARIO_MEEIRO,
    Bem,
    Distribuicao,
    Herdeiro,
    Inventario,
    TipoBem,
)
from app.modules.notas.inventarios.infrastructure.loaders import (
    inventario_from_mapping,
    load_inventario,
)

EXAMPLES = Path("app/modules/notas/inventarios/examples")


def _inventario_valido() -> Inventario:
    return Inventario(
        tipo_ato="inventario_extrajudicial",
        possui_meeiro=True,
        percentual_meacao=Decimal("50"),
        patrimonio_total=Decimal("1000000.00"),
        herdeiros=(
            Herdeiro(id="HERDEIRO_1", percentual_heranca=Decimal("50")),
            Herdeiro(id="HERDEIRO_2", percentual_heranca=Decimal("50")),
        ),
        bens=(
            Bem(
                id="IMOVEL_1",
                tipo=TipoBem.IMOVEL,
                descricao_generica="Imóvel urbano [MATRICULA]",
                valor=Decimal("1000000.00"),
                distribuicao=(
                    Distribuicao(beneficiario=BENEFICIARIO_MEEIRO, percentual=Decimal("50")),
                    Distribuicao(beneficiario="HERDEIRO_1", percentual=Decimal("25")),
                    Distribuicao(beneficiario="HERDEIRO_2", percentual=Decimal("25")),
                ),
            ),
        ),
    )


def test_inventario_valido_passa() -> None:
    result = InventarioValidator().validate(_inventario_valido())
    assert result.ok, f"erros inesperados: {result.errors}"


def test_tipo_ato_invalido_falha() -> None:
    inv = _inventario_valido()
    novo = Inventario(
        tipo_ato="escritura_qualquer",
        possui_meeiro=inv.possui_meeiro,
        percentual_meacao=inv.percentual_meacao,
        patrimonio_total=inv.patrimonio_total,
        herdeiros=inv.herdeiros,
        bens=inv.bens,
    )
    result = InventarioValidator().validate(novo)
    assert not result.ok
    assert any("tipo_ato" in e for e in result.errors)


def test_patrimonio_zero_falha() -> None:
    inv = Inventario(
        tipo_ato="inventario_extrajudicial",
        possui_meeiro=False,
        percentual_meacao=Decimal("0"),
        patrimonio_total=Decimal("0"),
        herdeiros=(Herdeiro(id="H", percentual_heranca=Decimal("100")),),
        bens=(
            Bem(
                id="B",
                tipo=TipoBem.OUTRO,
                descricao_generica="",
                valor=Decimal("0"),
                distribuicao=(Distribuicao(beneficiario="H", percentual=Decimal("100")),),
            ),
        ),
    )
    result = InventarioValidator().validate(inv)
    assert not result.ok
    assert any("patrimonio_total" in e for e in result.errors)


def test_soma_percentual_herdeiros_diferente_de_100_falha() -> None:
    base = _inventario_valido()
    inv = Inventario(
        tipo_ato=base.tipo_ato,
        possui_meeiro=base.possui_meeiro,
        percentual_meacao=base.percentual_meacao,
        patrimonio_total=base.patrimonio_total,
        herdeiros=(
            Herdeiro(id="HERDEIRO_1", percentual_heranca=Decimal("60")),
            Herdeiro(id="HERDEIRO_2", percentual_heranca=Decimal("50")),
        ),
        bens=base.bens,
    )
    result = InventarioValidator().validate(inv)
    assert not result.ok
    assert any("percentuais de herança" in e for e in result.errors)


def test_soma_valores_bens_diferente_de_patrimonio_falha() -> None:
    base = _inventario_valido()
    inv = Inventario(
        tipo_ato=base.tipo_ato,
        possui_meeiro=base.possui_meeiro,
        percentual_meacao=base.percentual_meacao,
        patrimonio_total=Decimal("999999.00"),
        herdeiros=base.herdeiros,
        bens=base.bens,
    )
    result = InventarioValidator().validate(inv)
    assert not result.ok
    assert any("Soma dos valores dos bens" in e for e in result.errors)


def test_beneficiario_inexistente_falha() -> None:
    inv = Inventario(
        tipo_ato="inventario_extrajudicial",
        possui_meeiro=True,
        percentual_meacao=Decimal("50"),
        patrimonio_total=Decimal("100.00"),
        herdeiros=(Herdeiro(id="HERDEIRO_1", percentual_heranca=Decimal("100")),),
        bens=(
            Bem(
                id="B",
                tipo=TipoBem.OUTRO,
                descricao_generica="",
                valor=Decimal("100.00"),
                distribuicao=(
                    Distribuicao(beneficiario=BENEFICIARIO_MEEIRO, percentual=Decimal("50")),
                    Distribuicao(beneficiario="HERDEIRO_FANTASMA", percentual=Decimal("50")),
                ),
            ),
        ),
    )
    result = InventarioValidator().validate(inv)
    assert not result.ok
    assert any("HERDEIRO_FANTASMA" in e for e in result.errors)


def test_beneficiario_meeiro_sem_meeiro_falha() -> None:
    inv = Inventario(
        tipo_ato="inventario_extrajudicial",
        possui_meeiro=False,
        percentual_meacao=Decimal("0"),
        patrimonio_total=Decimal("100.00"),
        herdeiros=(Herdeiro(id="HERDEIRO_1", percentual_heranca=Decimal("100")),),
        bens=(
            Bem(
                id="B",
                tipo=TipoBem.OUTRO,
                descricao_generica="",
                valor=Decimal("100.00"),
                distribuicao=(
                    Distribuicao(beneficiario=BENEFICIARIO_MEEIRO, percentual=Decimal("50")),
                    Distribuicao(beneficiario="HERDEIRO_1", percentual=Decimal("50")),
                ),
            ),
        ),
    )
    result = InventarioValidator().validate(inv)
    assert not result.ok
    assert any("possui_meeiro=false" in e for e in result.errors)


def test_distribuicao_de_um_bem_nao_soma_100_falha() -> None:
    base = _inventario_valido()
    bem_quebrado = Bem(
        id="IMOVEL_1",
        tipo=TipoBem.IMOVEL,
        descricao_generica="",
        valor=Decimal("1000000.00"),
        distribuicao=(
            Distribuicao(beneficiario=BENEFICIARIO_MEEIRO, percentual=Decimal("50")),
            Distribuicao(beneficiario="HERDEIRO_1", percentual=Decimal("30")),
            Distribuicao(beneficiario="HERDEIRO_2", percentual=Decimal("25")),
        ),
    )
    inv = Inventario(
        tipo_ato=base.tipo_ato,
        possui_meeiro=base.possui_meeiro,
        percentual_meacao=base.percentual_meacao,
        patrimonio_total=base.patrimonio_total,
        herdeiros=base.herdeiros,
        bens=(bem_quebrado,),
    )
    result = InventarioValidator().validate(inv)
    assert not result.ok
    assert any("soma dos percentuais da distribuição" in e for e in result.errors)


def test_herdeiro_id_duplicado_falha() -> None:
    base = _inventario_valido()
    inv = Inventario(
        tipo_ato=base.tipo_ato,
        possui_meeiro=base.possui_meeiro,
        percentual_meacao=base.percentual_meacao,
        patrimonio_total=base.patrimonio_total,
        herdeiros=(
            Herdeiro(id="HERDEIRO_1", percentual_heranca=Decimal("50")),
            Herdeiro(id="HERDEIRO_1", percentual_heranca=Decimal("50")),
        ),
        bens=base.bens,
    )
    result = InventarioValidator().validate(inv)
    assert not result.ok
    assert any("duplicado" in e for e in result.errors)


def test_id_reservado_meeiro_para_herdeiro_falha() -> None:
    inv = Inventario(
        tipo_ato="inventario_extrajudicial",
        possui_meeiro=False,
        percentual_meacao=Decimal("0"),
        patrimonio_total=Decimal("100.00"),
        herdeiros=(Herdeiro(id="MEEIRO", percentual_heranca=Decimal("100")),),
        bens=(
            Bem(
                id="B",
                tipo=TipoBem.OUTRO,
                descricao_generica="",
                valor=Decimal("100.00"),
                distribuicao=(Distribuicao(beneficiario="MEEIRO", percentual=Decimal("100")),),
            ),
        ),
    )
    result = InventarioValidator().validate(inv)
    assert not result.ok
    assert any("reservado" in e for e in result.errors)


def test_percentual_meacao_zero_com_meeiro_falha() -> None:
    inv = Inventario(
        tipo_ato="inventario_extrajudicial",
        possui_meeiro=True,
        percentual_meacao=Decimal("0"),
        patrimonio_total=Decimal("100.00"),
        herdeiros=(Herdeiro(id="HERDEIRO_1", percentual_heranca=Decimal("100")),),
        bens=(
            Bem(
                id="B",
                tipo=TipoBem.OUTRO,
                descricao_generica="",
                valor=Decimal("100.00"),
                distribuicao=(Distribuicao(beneficiario="HERDEIRO_1", percentual=Decimal("100")),),
            ),
        ),
    )
    result = InventarioValidator().validate(inv)
    assert not result.ok
    assert any("percentual_meacao" in e for e in result.errors)


def test_exemplo_yaml_simples_carrega_e_valida() -> None:
    inv = load_inventario(EXAMPLES / "inventario_simples.yaml")
    result = InventarioValidator().validate(inv)
    assert result.ok, f"erros: {result.errors}"


def test_exemplo_yaml_sem_meeiro_carrega_e_valida() -> None:
    inv = load_inventario(EXAMPLES / "inventario_sem_meeiro.yaml")
    result = InventarioValidator().validate(inv)
    assert result.ok, f"erros: {result.errors}"


def test_arquivo_inexistente_levanta_input_error() -> None:
    with pytest.raises(InventarioInputError, match="não encontrado"):
        load_inventario(Path("nao_existe.yaml"))


def test_yaml_malformado_levanta_input_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("tipo_ato: inventario_extrajudicial\n bens: [\n", encoding="utf-8")
    with pytest.raises(InventarioInputError, match="YAML inválido"):
        load_inventario(bad)


def test_campo_obrigatorio_ausente_levanta_input_error() -> None:
    with pytest.raises(InventarioInputError, match="patrimonio_total"):
        inventario_from_mapping(
            {
                "tipo_ato": "inventario_extrajudicial",
                "possui_meeiro": True,
                "percentual_meacao": 50,
                "herdeiros": [],
                "bens": [],
            }
        )


def test_tipo_de_bem_invalido_levanta_input_error() -> None:
    with pytest.raises(InventarioInputError, match="tipo inválido"):
        inventario_from_mapping(
            {
                "tipo_ato": "inventario_extrajudicial",
                "possui_meeiro": False,
                "percentual_meacao": 0,
                "patrimonio_total": 100,
                "herdeiros": [{"id": "H", "percentual_heranca": 100}],
                "bens": [
                    {
                        "id": "B",
                        "tipo": "criptomoeda_exotica",
                        "valor": 100,
                        "distribuicao": [{"beneficiario": "H", "percentual": 100}],
                    }
                ],
            }
        )
