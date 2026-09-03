"""Modelos de domínio do inventário extrajudicial.

Estruturas puras (dataclasses) — sem dependência de framework, banco ou rede.
Trabalham exclusivamente com `Decimal` em campos monetários e percentuais.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from fractions import Fraction

BENEFICIARIO_MEEIRO = "MEEIRO"


class TipoBem(StrEnum):
    IMOVEL = "imovel"
    VEICULO = "veiculo"
    DINHEIRO = "dinheiro"
    DIREITO = "direito"
    OUTRO = "outro"


@dataclass(frozen=True)
class Herdeiro:
    id: str
    percentual_heranca: Decimal


@dataclass(frozen=True)
class Distribuicao:
    """Participação de um beneficiário em um bem.

    ``fracao_ideal`` é **opcional e sempre explícita**: o sistema não infere
    fração a partir do percentual nem de relação sucessória (ADR-010). Quando
    presente, é apenas uma segunda representação da mesma participação já
    descrita por ``percentual`` — nunca uma informação nova, e nunca insumo de
    cálculo.
    """

    beneficiario: str
    percentual: Decimal
    fracao_ideal: Fraction | None = None


@dataclass(frozen=True)
class Bem:
    id: str
    tipo: TipoBem
    descricao_generica: str
    valor: Decimal
    distribuicao: tuple[Distribuicao, ...]


@dataclass(frozen=True)
class Inventario:
    tipo_ato: str
    possui_meeiro: bool
    percentual_meacao: Decimal
    patrimonio_total: Decimal
    herdeiros: tuple[Herdeiro, ...]
    bens: tuple[Bem, ...]


@dataclass(frozen=True)
class QuinhaoBem:
    """Quanto cada beneficiário recebe de um bem específico.

    ``fracao_ideal`` é transportada da ``Distribuicao`` correspondente sem
    qualquer transformação — o calculador apenas a repassa.
    """

    beneficiario: str
    percentual: Decimal
    valor: Decimal
    fracao_ideal: Fraction | None = None


@dataclass(frozen=True)
class ResumoBem:
    bem_id: str
    tipo: TipoBem
    valor: Decimal
    quinhoes: tuple[QuinhaoBem, ...]


@dataclass(frozen=True)
class ResumoInventario:
    """Saída dos cálculos. Imutável — recalcular gera novo objeto.

    ``divergencia_centavos`` é a diferença entre o patrimônio total e a soma
    de tudo o que foi efetivamente distribuído (meeiro + herdeiros, agregando
    cada bem). É sempre ``>= 0``; valores não-nulos dentro da tolerância
    indicam arredondamento de percentuais (ex.: 33,33%×3). A política de
    tratamento desse resíduo é decidida em sprint futura — ver
    ``docs/modules/notas_inventarios.md`` § 6.
    """

    patrimonio_total: Decimal
    valor_meacao: Decimal
    monte_partilhavel: Decimal
    quinhao_por_herdeiro: dict[str, Decimal] = field(default_factory=dict)
    total_por_beneficiario: dict[str, Decimal] = field(default_factory=dict)
    bens: tuple[ResumoBem, ...] = ()
    divergencia_centavos: Decimal = Decimal("0")
