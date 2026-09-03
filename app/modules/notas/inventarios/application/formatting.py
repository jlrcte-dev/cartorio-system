"""Camada autoritativa de apresentação e serialização de valores do inventário.

Sprint **NOTAS-INVENTARIO-FRACOES-1**.

Este módulo existe para separar, de forma explícita, três contratos que antes
estavam misturados e que têm regras de precisão **diferentes**:

1. **Monetário** — sempre 2 casas. É o contrato do documento cartorário e do
   ``ResumoInventario``; não muda nesta sprint.
2. **Percentual** — precisão variável, derivada da própria entrada (ver
   :func:`casas_decimais_percentual`). Antes desta sprint, o percentual era
   forçado a 2 casas pelo mesmo formatador usado para dinheiro, o que
   apresentava ``Decimal("3.125")`` como ``3,12%`` e ``Decimal("0.005")`` como
   ``0,00%``.
3. **Fração ideal** — representação textual ``numerador/denominador`` em forma
   canônica, quando informada explicitamente na entrada.

**Nada aqui altera cálculo.** A aritmética monetária continua inteiramente em
:mod:`app.modules.notas.inventarios.application.calculator`, com ``Decimal`` e
``ROUND_HALF_EVEN``, e a política de resíduo de centavos segue governada pela
ADR-009, intacta. A decisão de representação está registrada na
``docs/decisions/ADR-010-inventory-fraction-percentage-rendering.md``.

Convenção de nomes: ``formatar_*`` produz texto para leitura humana no
documento (vírgula decimal, sufixos); ``serializar_*`` produz texto para
artefato técnico/JSON (ponto decimal, sem sufixo).
"""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction

CASAS_MINIMAS_PERCENTUAL = 2
"""Piso de casas decimais do percentual.

Preserva o padrão já consolidado do documento (``50`` continua ``50,00%`` e
``12.5`` continua ``12,50%``), evitando regressão de redação nos casos comuns.
"""

CASAS_MONETARIAS = 2
"""Casas decimais de valores monetários. Contrato fixo do documento."""


def casas_decimais_percentual(value: Decimal) -> int:
    """Quantas casas decimais são necessárias para representar ``value`` sem perda.

    Regra, deliberadamente derivada do dado e não de um número arbitrário:

    - parte-se do expoente do próprio ``Decimal`` — isto é, da precisão que a
      entrada efetivamente carrega;
    - zeros à direita são descartados até o piso, para que ``12.500`` e
      ``12.5`` produzam o mesmo texto;
    - nunca se desce abaixo de :data:`CASAS_MINIMAS_PERCENTUAL`.

    Não há teto arbitrário porque não é preciso: **todo percentual do módulo vem
    da entrada estruturada, nenhum é calculado.** O ``calculator`` copia
    ``Distribuicao.percentual`` para ``QuinhaoBem.percentual`` sem aritmética,
    de modo que não existe dízima a truncar — a precisão é sempre finita e
    escolhida por quem escreveu o arquivo de entrada.
    """

    _, digitos, expoente = value.as_tuple()

    # Expoente não-inteiro ocorre em NaN/Infinity; expoente >= 0 é inteiro puro.
    if not isinstance(expoente, int) or expoente >= 0:
        return CASAS_MINIMAS_PERCENTUAL

    casas = -expoente
    restantes = list(digitos)
    while casas > CASAS_MINIMAS_PERCENTUAL and restantes and restantes[-1] == 0:
        restantes.pop()
        casas -= 1

    return max(casas, CASAS_MINIMAS_PERCENTUAL)


def formatar_percentual(value: Decimal) -> str:
    """Percentual para leitura humana: vírgula decimal e sufixo ``%``.

    ``Decimal("50")`` → ``"50,00%"`` · ``Decimal("3.125")`` → ``"3,125%"``.
    """

    casas = casas_decimais_percentual(value)
    return f"{value:.{casas}f}%".replace(".", ",")


def serializar_percentual(value: Decimal) -> str:
    """Percentual para artefato técnico/JSON: ponto decimal, sem sufixo.

    ``Decimal("50")`` → ``"50.00"`` · ``Decimal("3.125")`` → ``"3.125"``.

    O piso de 2 casas é mantido aqui de propósito: o JSON de validação é
    comparado byte a byte pelos golden files, e o piso preserva a saída
    histórica dos casos que não usam fração.
    """

    return f"{value:.{casas_decimais_percentual(value)}f}"


def formatar_monetario(value: Decimal) -> str:
    """Valor monetário para leitura humana: ``R$ 1.234.567,89``."""

    return f"R$ {value:,.{CASAS_MONETARIAS}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def serializar_monetario(value: Decimal) -> str:
    """Valor monetário para artefato técnico/JSON: sempre 2 casas, ponto decimal."""

    return f"{value:.{CASAS_MONETARIAS}f}"


def formatar_fracao(fracao: Fraction) -> str:
    """Fração ideal em forma canônica textual: ``Fraction(2, 64)`` → ``"1/32"``.

    ``Fraction`` já normaliza na construção, de modo que a forma canônica é
    consequência do tipo, não de lógica adicional.
    """

    return f"{fracao.numerator}/{fracao.denominator}"


def percentual_da_fracao(fracao: Fraction) -> Decimal:
    """Percentual exato correspondente à fração, para conferência.

    Frações de expansão infinita (``1/3``) produzem um ``Decimal`` com a
    precisão do contexto corrente. O resultado destina-se **exclusivamente** à
    comparação com tolerância feita pelo validador — nunca à renderização e
    nunca a cálculo monetário.
    """

    return Decimal(fracao.numerator) / Decimal(fracao.denominator) * Decimal("100")


def tolerancia_percentual(value: Decimal) -> Decimal:
    """Tolerância admitida ao comparar um percentual informado com sua fração.

    Derivada da própria entrada, não arbitrada: quem escreve ``33.33`` está
    declarando o percentual arredondado à segunda casa, e o maior erro legítimo
    desse arredondamento é **meia unidade da última casa** — 0,005. Para
    ``3.125`` (três casas), a tolerância cai para 0,0005.

    Consequências desejadas:

    - ``1/3`` com ``33.33`` é aceito (erro 0,00333 < 0,005);
    - ``1/3`` com ``33.34`` é recusado (erro 0,00666 > 0,005), porque não é o
      arredondamento correto;
    - ``1/2`` com ``40`` é recusado com folga.

    A tolerância monetária ``DECIMAL_TOLERANCIA`` **não** é reutilizada aqui: os
    domínios são distintos — um mede centavos de patrimônio, o outro mede
    arredondamento de percentual.
    """

    casas = casas_decimais_percentual(value)
    return Decimal("0.5").scaleb(-casas)


__all__ = [
    "CASAS_MINIMAS_PERCENTUAL",
    "CASAS_MONETARIAS",
    "casas_decimais_percentual",
    "formatar_fracao",
    "formatar_monetario",
    "formatar_percentual",
    "percentual_da_fracao",
    "serializar_monetario",
    "serializar_percentual",
    "tolerancia_percentual",
]
