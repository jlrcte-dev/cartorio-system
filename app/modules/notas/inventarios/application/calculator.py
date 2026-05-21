"""Cálculo determinístico de patrimônio, meação, monte partilhável e quinhões.

Usa exclusivamente `Decimal` (`ROUND_HALF_EVEN`). Não é responsabilidade do
calculator decidir se a entrada é válida — para isso existe o `InventarioValidator`.
O calculator assume entrada já validada e foca em aritmética exata.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal

from app.modules.notas.inventarios.domain.models import (
    BENEFICIARIO_MEEIRO,
    Bem,
    Inventario,
    QuinhaoBem,
    ResumoBem,
    ResumoInventario,
)

DECIMAL_TOLERANCIA: Decimal = Decimal("0.01")
_DUAS_CASAS: Decimal = Decimal("0.01")
_CEM: Decimal = Decimal("100")
_ZERO: Decimal = Decimal("0")


def quantize_money(value: Decimal) -> Decimal:
    """Arredonda para 2 casas usando banker's rounding."""

    return value.quantize(_DUAS_CASAS, rounding=ROUND_HALF_EVEN)


class InventarioCalculator:
    """Calcula meação, monte partilhável e distribuição bem a bem."""

    def compute(self, inv: Inventario) -> ResumoInventario:
        patrimonio = quantize_money(sum((b.valor for b in inv.bens), _ZERO))

        if inv.possui_meeiro:
            valor_meacao = quantize_money(patrimonio * (inv.percentual_meacao / _CEM))
        else:
            valor_meacao = _ZERO

        monte = quantize_money(patrimonio - valor_meacao)

        quinhao_por_herdeiro: dict[str, Decimal] = {
            h.id: quantize_money(monte * (h.percentual_heranca / _CEM)) for h in inv.herdeiros
        }

        resumo_bens: list[ResumoBem] = []
        total_por_beneficiario: dict[str, Decimal] = {}

        for bem in inv.bens:
            quinhoes = self._quinhoes_do_bem(bem)
            resumo_bens.append(
                ResumoBem(
                    bem_id=bem.id,
                    tipo=bem.tipo,
                    valor=quantize_money(bem.valor),
                    quinhoes=tuple(quinhoes),
                )
            )
            for q in quinhoes:
                total_por_beneficiario[q.beneficiario] = (
                    total_por_beneficiario.get(q.beneficiario, _ZERO) + q.valor
                )

        total_por_beneficiario = {k: quantize_money(v) for k, v in total_por_beneficiario.items()}

        soma_distribuida = quantize_money(sum(total_por_beneficiario.values(), _ZERO))
        divergencia = quantize_money(abs(patrimonio - soma_distribuida))

        return ResumoInventario(
            patrimonio_total=patrimonio,
            valor_meacao=valor_meacao,
            monte_partilhavel=monte,
            quinhao_por_herdeiro=quinhao_por_herdeiro,
            total_por_beneficiario=total_por_beneficiario,
            bens=tuple(resumo_bens),
            divergencia_centavos=divergencia,
        )

    @staticmethod
    def _quinhoes_do_bem(bem: Bem) -> list[QuinhaoBem]:
        quinhoes: list[QuinhaoBem] = []
        for d in bem.distribuicao:
            valor = quantize_money(bem.valor * (d.percentual / _CEM))
            quinhoes.append(
                QuinhaoBem(
                    beneficiario=d.beneficiario,
                    percentual=d.percentual,
                    valor=valor,
                )
            )
        return quinhoes


def patrimonio_a_partir_de_bens(inv: Inventario) -> Decimal:
    """Soma `bens.valor` quantizado, sem cálculos adicionais."""

    return quantize_money(sum((b.valor for b in inv.bens), _ZERO))


__all__ = [
    "BENEFICIARIO_MEEIRO",
    "DECIMAL_TOLERANCIA",
    "InventarioCalculator",
    "patrimonio_a_partir_de_bens",
    "quantize_money",
]
