"""Resumo técnico do inventário em Markdown.

**Escopo:** este módulo gera apenas um *resumo técnico* — não a minuta. O
documento produzido serve para conferência rápida dos cálculos (patrimônio,
meação, quinhões, distribuição por bem) e nunca contém dados pessoais reais.

A renderização da minuta completa (texto cartorário do §§ 1 a 20 com
placeholders interpolados) fica para sprint futura — ver
``infrastructure/templates/inventario_extrajudicial_padrao.md.j2`` e
``docs/modules/notas_inventarios.md`` § 4.
"""

from __future__ import annotations

from decimal import Decimal

from app.modules.notas.inventarios.domain.models import (
    BENEFICIARIO_MEEIRO,
    Inventario,
    ResumoInventario,
)

_AVISO = (
    "> **RESUMO TÉCNICO — NÃO É A MINUTA.** Documento sem dados pessoais "
    "reais, usado apenas para conferência dos cálculos."
)


def _fmt_money(value: Decimal) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_pct(value: Decimal) -> str:
    return f"{value:.2f}%".replace(".", ",")


def render_resumo_markdown(inv: Inventario, resumo: ResumoInventario) -> str:
    """Gera o resumo técnico em Markdown. Não renderiza a minuta completa."""

    lines: list[str] = []
    lines.append("# Resumo técnico do inventário extrajudicial")
    lines.append("")
    lines.append(_AVISO)
    lines.append("")
    lines.append("## 1. Identificação do ato")
    lines.append("")
    lines.append(f"- Tipo de ato: `{inv.tipo_ato}`")
    lines.append("- Cidade/Comarca: [CONFIGURAR_SERVENTIA]")
    lines.append("- Tabeliã: [CONFIGURAR_SERVENTIA]")
    lines.append("- Autor da herança: [QUALIFICAÇÃO DO AUTOR DA HERANÇA]")
    if inv.possui_meeiro:
        lines.append("- Meeiro(a): [QUALIFICAÇÃO DO MEEIRO]")
    else:
        lines.append("- Meeiro(a): não há.")
    lines.append("")

    lines.append("## 2. Patrimônio")
    lines.append("")
    lines.append(f"- Patrimônio total: **{_fmt_money(resumo.patrimonio_total)}**")
    if inv.possui_meeiro:
        lines.append(
            f"- Meação ({_fmt_pct(inv.percentual_meacao)}): **{_fmt_money(resumo.valor_meacao)}**"
        )
    lines.append(f"- Monte partilhável: **{_fmt_money(resumo.monte_partilhavel)}**")
    lines.append("")

    lines.append("## 3. Herdeiros e quinhões")
    lines.append("")
    lines.append("| Herdeiro | % herança | Valor do quinhão |")
    lines.append("|----------|-----------|------------------|")
    for h in inv.herdeiros:
        quinhao = resumo.quinhao_por_herdeiro.get(h.id, Decimal("0"))
        lines.append(
            f"| `{h.id}` ([QUALIFICAÇÃO DO {h.id}]) | "
            f"{_fmt_pct(h.percentual_heranca)} | {_fmt_money(quinhao)} |"
        )
    lines.append("")

    lines.append("## 4. Bens, direitos e valores")
    lines.append("")
    for bem in inv.bens:
        lines.append(f"### {bem.id} — {bem.tipo.value} — {_fmt_money(bem.valor)}")
        lines.append("")
        lines.append(f"> {bem.descricao_generica}")
        lines.append("")
        lines.append("| Beneficiário | % | Valor |")
        lines.append("|--------------|---|-------|")
        resumo_bem = next((r for r in resumo.bens if r.bem_id == bem.id), None)
        if resumo_bem:
            for q in resumo_bem.quinhoes:
                lines.append(
                    f"| `{q.beneficiario}` | {_fmt_pct(q.percentual)} | {_fmt_money(q.valor)} |"
                )
        lines.append("")

    if resumo.divergencia_centavos > Decimal("0"):
        lines.append("## ⚠ Alerta de centavos")
        lines.append("")
        lines.append(
            f"- Divergência entre patrimônio e soma distribuída: "
            f"**{_fmt_money(resumo.divergencia_centavos)}**."
        )
        lines.append(
            "- Esta sprint **não ajusta centavos automaticamente**. A decisão "
            "sobre ajustar, alertar ou exigir distribuição manual por valor "
            "fica para sprint futura — ver `docs/modules/notas_inventarios.md` § 6."
        )
        lines.append("")

    lines.append("## 5. Conferência por beneficiário")
    lines.append("")
    lines.append("| Beneficiário | Total recebido |")
    lines.append("|--------------|----------------|")
    if inv.possui_meeiro:
        lines.append(
            f"| `{BENEFICIARIO_MEEIRO}` | "
            f"{_fmt_money(resumo.total_por_beneficiario.get(BENEFICIARIO_MEEIRO, Decimal('0')))} |"
        )
    for h in inv.herdeiros:
        lines.append(
            f"| `{h.id}` | {_fmt_money(resumo.total_por_beneficiario.get(h.id, Decimal('0')))} |"
        )
    lines.append("")

    lines.append("## 6. Placeholders pendentes (a preencher manualmente)")
    lines.append("")
    lines.append("- [QUALIFICAÇÃO DO AUTOR DA HERANÇA]")
    if inv.possui_meeiro:
        lines.append("- [QUALIFICAÇÃO DO MEEIRO]")
    for h in inv.herdeiros:
        lines.append(f"- [QUALIFICAÇÃO DO {h.id}]")
    lines.append("- [QUALIFICAÇÃO DO ADVOGADO]")
    lines.append("- [CERTIDAO_OBITO]")
    lines.append("- [CENSEC_DATA]")
    lines.append("- [ITCMD_SPL_N]")
    lines.append("- [CNIB_HASH], [CNIB_DATA], [CNIB_STATUS]")
    lines.append("")

    return "\n".join(lines) + "\n"


__all__ = ["render_resumo_markdown"]
