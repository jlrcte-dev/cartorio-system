"""Testes do calculador determinístico de inventários."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.notas.inventarios.application.calculator import (
    InventarioCalculator,
    quantize_money,
)
from app.modules.notas.inventarios.domain.models import (
    BENEFICIARIO_MEEIRO,
    Bem,
    Distribuicao,
    Herdeiro,
    Inventario,
    TipoBem,
)


def _build_inventario_com_meeiro() -> Inventario:
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
                valor=Decimal("600000.00"),
                distribuicao=(
                    Distribuicao(beneficiario=BENEFICIARIO_MEEIRO, percentual=Decimal("50")),
                    Distribuicao(beneficiario="HERDEIRO_1", percentual=Decimal("25")),
                    Distribuicao(beneficiario="HERDEIRO_2", percentual=Decimal("25")),
                ),
            ),
            Bem(
                id="SALDO_1",
                tipo=TipoBem.DINHEIRO,
                descricao_generica="Saldo [BANCO]",
                valor=Decimal("400000.00"),
                distribuicao=(
                    Distribuicao(beneficiario=BENEFICIARIO_MEEIRO, percentual=Decimal("50")),
                    Distribuicao(beneficiario="HERDEIRO_1", percentual=Decimal("25")),
                    Distribuicao(beneficiario="HERDEIRO_2", percentual=Decimal("25")),
                ),
            ),
        ),
    )


def _build_inventario_sem_meeiro() -> Inventario:
    return Inventario(
        tipo_ato="inventario_extrajudicial",
        possui_meeiro=False,
        percentual_meacao=Decimal("0"),
        patrimonio_total=Decimal("300000.00"),
        herdeiros=(
            Herdeiro(id="HERDEIRO_1", percentual_heranca=Decimal("33.33")),
            Herdeiro(id="HERDEIRO_2", percentual_heranca=Decimal("33.33")),
            Herdeiro(id="HERDEIRO_3", percentual_heranca=Decimal("33.34")),
        ),
        bens=(
            Bem(
                id="IMOVEL_1",
                tipo=TipoBem.IMOVEL,
                descricao_generica="Imóvel rural [MATRICULA]",
                valor=Decimal("200000.00"),
                distribuicao=(
                    Distribuicao(beneficiario="HERDEIRO_1", percentual=Decimal("33.33")),
                    Distribuicao(beneficiario="HERDEIRO_2", percentual=Decimal("33.33")),
                    Distribuicao(beneficiario="HERDEIRO_3", percentual=Decimal("33.34")),
                ),
            ),
            Bem(
                id="VEICULO_1",
                tipo=TipoBem.VEICULO,
                descricao_generica="Veículo [PLACA]",
                valor=Decimal("100000.00"),
                distribuicao=(
                    Distribuicao(beneficiario="HERDEIRO_1", percentual=Decimal("33.33")),
                    Distribuicao(beneficiario="HERDEIRO_2", percentual=Decimal("33.33")),
                    Distribuicao(beneficiario="HERDEIRO_3", percentual=Decimal("33.34")),
                ),
            ),
        ),
    )


def test_quantize_money_arredonda_para_duas_casas() -> None:
    assert quantize_money(Decimal("1.005")) == Decimal("1.00")  # banker's rounding
    assert quantize_money(Decimal("1.015")) == Decimal("1.02")


def test_patrimonio_e_meacao_com_meeiro() -> None:
    inv = _build_inventario_com_meeiro()
    resumo = InventarioCalculator().compute(inv)

    assert resumo.patrimonio_total == Decimal("1000000.00")
    assert resumo.valor_meacao == Decimal("500000.00")
    assert resumo.monte_partilhavel == Decimal("500000.00")


def test_quinhao_por_herdeiro_com_meeiro() -> None:
    inv = _build_inventario_com_meeiro()
    resumo = InventarioCalculator().compute(inv)

    assert resumo.quinhao_por_herdeiro == {
        "HERDEIRO_1": Decimal("250000.00"),
        "HERDEIRO_2": Decimal("250000.00"),
    }


def test_total_por_beneficiario_fecha_com_patrimonio() -> None:
    inv = _build_inventario_com_meeiro()
    resumo = InventarioCalculator().compute(inv)

    total = sum(resumo.total_por_beneficiario.values(), Decimal("0"))
    assert total == resumo.patrimonio_total


def test_distribuicao_por_bem_respeita_percentuais() -> None:
    inv = _build_inventario_com_meeiro()
    resumo = InventarioCalculator().compute(inv)

    imovel = next(r for r in resumo.bens if r.bem_id == "IMOVEL_1")
    valores = {q.beneficiario: q.valor for q in imovel.quinhoes}

    assert valores[BENEFICIARIO_MEEIRO] == Decimal("300000.00")
    assert valores["HERDEIRO_1"] == Decimal("150000.00")
    assert valores["HERDEIRO_2"] == Decimal("150000.00")


def test_inventario_sem_meeiro_nao_atribui_meacao() -> None:
    inv = _build_inventario_sem_meeiro()
    resumo = InventarioCalculator().compute(inv)

    assert resumo.valor_meacao == Decimal("0")
    assert resumo.monte_partilhavel == resumo.patrimonio_total
    assert BENEFICIARIO_MEEIRO not in resumo.total_por_beneficiario


def test_inventario_sem_meeiro_tolera_pequena_diferenca_de_centavos() -> None:
    """33,33% + 33,33% + 33,34% = 100,00%; valores devem somar ≈ patrimônio."""

    inv = _build_inventario_sem_meeiro()
    resumo = InventarioCalculator().compute(inv)

    total = sum(resumo.total_por_beneficiario.values(), Decimal("0"))
    diferenca = abs(total - resumo.patrimonio_total)
    assert diferenca <= Decimal("0.05"), (
        f"diferença de centavos fora do esperado: {diferenca} (total={total})"
    )


def test_calculator_nao_aceita_float_implicito() -> None:
    """`Decimal` deve ser preservado — float introduziria imprecisão."""

    inv = _build_inventario_com_meeiro()
    resumo = InventarioCalculator().compute(inv)
    for v in resumo.quinhao_por_herdeiro.values():
        assert isinstance(v, Decimal)


@pytest.mark.parametrize(
    "valor,pct,esperado",
    [
        (Decimal("600000.00"), Decimal("50"), Decimal("300000.00")),
        (Decimal("100.00"), Decimal("33.33"), Decimal("33.33")),
        (Decimal("100.00"), Decimal("0"), Decimal("0.00")),
    ],
)
def test_distribuicao_por_percentual(valor: Decimal, pct: Decimal, esperado: Decimal) -> None:
    inv = Inventario(
        tipo_ato="inventario_extrajudicial",
        possui_meeiro=False,
        percentual_meacao=Decimal("0"),
        patrimonio_total=valor,
        herdeiros=(Herdeiro(id="H", percentual_heranca=Decimal("100")),),
        bens=(
            Bem(
                id="B",
                tipo=TipoBem.OUTRO,
                descricao_generica="",
                valor=valor,
                distribuicao=(
                    Distribuicao(beneficiario="H", percentual=pct),
                    Distribuicao(beneficiario="H", percentual=Decimal("100") - pct),
                ),
            ),
        ),
    )
    resumo = InventarioCalculator().compute(inv)
    quinhao = resumo.bens[0].quinhoes[0].valor
    assert quinhao == esperado
