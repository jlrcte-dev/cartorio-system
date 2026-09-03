"""Testes da camada autoritativa de formatação — ADR-010.

Sprint **NOTAS-INVENTARIO-FRACOES-1**.

Cobrem o contrato de precisão que separa dinheiro de percentual, o parsing e a
normalização da fração ideal, e a tolerância derivada usada na conferência
fração × percentual.
"""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction

import pytest

from app.modules.notas.inventarios.application.formatting import (
    CASAS_MINIMAS_PERCENTUAL,
    casas_decimais_percentual,
    formatar_fracao,
    formatar_monetario,
    formatar_percentual,
    percentual_da_fracao,
    serializar_monetario,
    serializar_percentual,
    tolerancia_percentual,
)

# ---------------------------------------------------------------------------
# Percentual — leitura humana
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        # Casos comuns: precisam continuar exatamente como antes da ADR-010,
        # sob pena de mudar a redação de documentos que já funcionam.
        ("50", "50,00%"),
        ("50.00", "50,00%"),
        ("12.5", "12,50%"),
        ("12.50", "12,50%"),
        ("12.500", "12,50%"),
        ("33.33", "33,33%"),
        ("33.34", "33,34%"),
        ("6.25", "6,25%"),
        ("100", "100,00%"),
        ("0", "0,00%"),
        ("0.1", "0,10%"),
    ],
)
def test_percentual_comum_preserva_representacao_historica(entrada: str, esperado: str) -> None:
    assert formatar_percentual(Decimal(entrada)) == esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("3.125", "3,125%"),
        ("0.005", "0,005%"),
        ("0.0001", "0,0001%"),
        ("6.2505", "6,2505%"),
    ],
)
def test_percentual_expande_casas_quando_necessario(entrada: str, esperado: str) -> None:
    """Só expande onde havia perda — este é o coração da ADR-010."""

    assert formatar_percentual(Decimal(entrada)) == esperado


def test_percentual_3125_nao_vira_312() -> None:
    """Regressão explícita do defeito que motivou a sprint."""

    resultado = formatar_percentual(Decimal("3.125"))
    assert resultado == "3,125%"
    assert resultado != "3,12%"


def test_percentual_0005_nao_desaparece() -> None:
    """Uma participação pequena não pode ser apresentada como zero."""

    assert formatar_percentual(Decimal("0.005")) == "0,005%"
    assert formatar_percentual(Decimal("0.005")) != "0,00%"


@pytest.mark.parametrize("entrada", ["1E+2", "1E-3", "0.000001", "12345.6789"])
def test_percentual_nunca_usa_notacao_cientifica(entrada: str) -> None:
    resultado = formatar_percentual(Decimal(entrada))
    assert "E" not in resultado.upper()


def test_percentual_usa_virgula_decimal() -> None:
    assert "," in formatar_percentual(Decimal("3.125"))
    assert "." not in formatar_percentual(Decimal("3.125"))


def test_percentual_e_deterministico() -> None:
    valor = Decimal("3.125")
    assert len({formatar_percentual(valor) for _ in range(50)}) == 1


@pytest.mark.parametrize(
    ("entrada", "casas"),
    [("50", 2), ("12.5", 2), ("12.500", 2), ("3.125", 3), ("0.0001", 4), ("1E+2", 2)],
)
def test_casas_decimais_percentual(entrada: str, casas: int) -> None:
    assert casas_decimais_percentual(Decimal(entrada)) == casas


def test_casas_decimais_nunca_abaixo_do_piso() -> None:
    for entrada in ["0", "1", "7", "100", "0.1", "12.5"]:
        assert casas_decimais_percentual(Decimal(entrada)) >= CASAS_MINIMAS_PERCENTUAL


# ---------------------------------------------------------------------------
# Percentual × dinheiro — contratos separados
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [("3.125", "3.125"), ("50", "50.00"), ("33.33", "33.33"), ("0.005", "0.005")],
)
def test_serializacao_de_percentual_preserva_precisao(entrada: str, esperado: str) -> None:
    assert serializar_percentual(Decimal(entrada)) == esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("1000", "1000.00"),
        ("1000.5", "1000.50"),
        ("16374", "16374.00"),
        # Banker's rounding, coerente com o ROUND_HALF_EVEN do calculator:
        # 0.125 -> 0.12 (arredonda para o par) e 0.135 -> 0.14.
        ("0.125", "0.12"),
        ("0.135", "0.14"),
    ],
)
def test_serializacao_monetaria_mantem_duas_casas(entrada: str, esperado: str) -> None:
    """Dinheiro não herda a precisão variável do percentual."""

    assert serializar_monetario(Decimal(entrada)) == esperado


def test_formatador_monetario_e_percentual_sao_contratos_distintos() -> None:
    """O mesmo Decimal produz textos diferentes conforme o domínio."""

    valor = Decimal("3.125")
    assert serializar_monetario(valor) == "3.12"  # arredonda: é dinheiro
    assert serializar_percentual(valor) == "3.125"  # preserva: é percentual


def test_formatacao_monetaria_usa_separadores_brasileiros() -> None:
    assert formatar_monetario(Decimal("1234567.89")) == "R$ 1.234.567,89"


# ---------------------------------------------------------------------------
# Fração ideal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("numerador", "denominador", "esperado"),
    [(1, 32, "1/32"), (1, 16, "1/16"), (1, 2, "1/2"), (2, 64, "1/32"), (4, 8, "1/2")],
)
def test_formatar_fracao_usa_forma_canonica(
    numerador: int, denominador: int, esperado: str
) -> None:
    assert formatar_fracao(Fraction(numerador, denominador)) == esperado


@pytest.mark.parametrize(
    ("fracao", "percentual"),
    [("1/2", "50"), ("1/32", "3.125"), ("1/16", "6.25"), ("1/8", "12.5"), ("1/4", "25")],
)
def test_percentual_da_fracao_bate_com_o_declarado(fracao: str, percentual: str) -> None:
    assert percentual_da_fracao(Fraction(fracao)) == Decimal(percentual)


def test_percentual_da_fracao_com_dizima_nao_quebra() -> None:
    """1/3 tem expansão infinita — precisa produzir Decimal utilizável."""

    resultado = percentual_da_fracao(Fraction(1, 3))
    assert Decimal("33.3") < resultado < Decimal("33.4")


# ---------------------------------------------------------------------------
# Tolerância derivada
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("percentual", "tolerancia"),
    [("50", "0.005"), ("33.33", "0.005"), ("3.125", "0.0005"), ("0.0001", "0.00005")],
)
def test_tolerancia_e_meia_unidade_da_ultima_casa(percentual: str, tolerancia: str) -> None:
    assert tolerancia_percentual(Decimal(percentual)) == Decimal(tolerancia)


def test_tolerancia_nao_e_a_tolerancia_monetaria() -> None:
    """Domínios distintos não podem compartilhar a mesma constante."""

    from app.modules.notas.inventarios.application.calculator import DECIMAL_TOLERANCIA

    assert tolerancia_percentual(Decimal("3.125")) != DECIMAL_TOLERANCIA
