"""Resumo técnico e minuta-base do inventário em Markdown.

**Dois tipos de saída** vivem aqui:

- :func:`render_resumo_markdown` — *resumo técnico* dos cálculos, usado para
  conferência. Contém placeholders, mas sua linguagem é técnica, não
  cartorária.
- :func:`render_minuta_markdown` — *minuta-base* da Escritura Pública de
  Inventário e Partilha, com texto cartorário (Resolução 35 CNJ, Prov. 46/2020
  CGJ-GO) e marcação explícita de placeholders pessoais. **Não é a minuta
  final** — é um rascunho para o tabelião revisar e completar manualmente.

Nenhum dos dois lê ou escreve PII; o `Inventario` que recebem só carrega ids
locais (``HERDEIRO_1``, ``IMOVEL_1``) e valores. Qualificações reais são
preenchidas manualmente pelo Engegraph na fase posterior do fluxo cartorário.

A política de centavos seguida pela minuta está documentada em
``docs/decisions/ADR-009-inventory-cent-rounding-policy.md`` e em
``docs/modules/notas_inventarios.md`` § 6.
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

_AVISO_MINUTA = (
    "> **MINUTA-BASE — RASCUNHO SUJEITO À REVISÃO HUMANA.** Este documento "
    "foi gerado pelo Cartório System apenas com placeholders e dados "
    "estruturados fictícios. Não contém dados pessoais reais. As qualificações "
    "completas (CPF, RG, endereço, estado civil, regime de bens) são "
    "responsabilidade do Engegraph e devem ser preenchidas manualmente antes "
    "da lavratura. O tabelião é o único responsável pela versão final assinada."
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


def render_minuta_markdown(inv: Inventario, resumo: ResumoInventario) -> str:
    """Gera a minuta-base da escritura pública de inventário e partilha em Markdown.

    Espelha o template
    ``infrastructure/templates/inventario_extrajudicial_padrao.md.j2`` — fonte
    canônica da estrutura textual. A renderização é feita em Python puro (sem
    Jinja2) para não introduzir dependência. Placeholders pessoais usam o
    formato ``[QUALIFICAÇÃO DO …]`` ou ``[DADO]`` e devem ser substituídos
    manualmente pelo tabelião com auxílio do Engegraph.

    O documento **não** é a minuta final assinada. É um rascunho que carrega:

    - texto fixo das cláusulas (§§ 14, 15, 17, 18, 19, 20);
    - placeholders explícitos para qualificações;
    - cálculos determinísticos (patrimônio, meação, quinhões);
    - alerta técnico de centavos quando aplicável (ADR-009);
    - bloco final "Campo de revisão humana" para o tabelião carimbar a revisão.
    """

    lines: list[str] = []
    n_herdeiros = len(inv.herdeiros)

    # Cabeçalho
    lines.append(
        "# ESCRITURA PÚBLICA DE INVENTÁRIO E PARTILHA DOS BENS DEIXADOS "
        "PELO ESPÓLIO DE [QUALIFICAÇÃO DO AUTOR DA HERANÇA]"
    )
    lines.append("")
    lines.append(_AVISO_MINUTA)
    lines.append("")
    lines.append(
        "SAIBAM quantos esta Escritura Pública de Inventário e Partilha virem, "
        "que aos [DATA_LAVRATURA], nesta Cidade de [CIDADE_SERVENTIA], Comarca "
        "de [COMARCA], Estado de [UF], em Cartório, perante mim, "
        "[QUALIFICAÇÃO DA TABELIÃ], compareceram partes entre si justas e "
        "contratadas, a saber:"
    )
    lines.append("")

    # § 1. Qualificação das partes
    lines.append("## 1. DA QUALIFICAÇÃO DAS PARTES")
    lines.append("")
    lines.append("### 1.1. COMO HERDEIROS DESCENDENTES")
    lines.append("")
    for h in inv.herdeiros:
        lines.append(f"- [QUALIFICAÇÃO DO {h.id}]")
    lines.append("")
    if inv.possui_meeiro:
        lines.append("### 1.2. COMO MEEIRO(A)")
        lines.append("")
        lines.append("- [QUALIFICAÇÃO DO MEEIRO]")
        lines.append("")
        lines.append("### 1.3. COMO ADVOGADO")
    else:
        lines.append("### 1.2. COMO ADVOGADO")
    lines.append("")
    lines.append("[QUALIFICAÇÃO DO ADVOGADO]")
    lines.append("")

    # § 2. Autor da herança
    lines.append("## 2. DO AUTOR DA HERANÇA")
    lines.append("")
    lines.append("[QUALIFICAÇÃO DO AUTOR DA HERANÇA]")
    lines.append("")

    # § 3. Falecimento
    lines.append("## 3. DO FALECIMENTO")
    lines.append("")
    lines.append("[CERTIDÃO DE ÓBITO]")
    lines.append("")

    # § 4. Inexistência de testamento
    lines.append("## 4. DA INEXISTÊNCIA DE TESTAMENTO")
    lines.append("")
    lines.append(
        "Consulta ao Registro Central de Testamento Online emitida em "
        "[CENSEC_DATA], pelo Colégio Notarial do Brasil, conforme Provimento "
        "CNJ 56/2016, onde NÃO CONSTA a lavratura de testamento público, "
        "aprovação de testamento cerrado ou revogação de testamento em nome "
        'do "de cujus".'
    )
    lines.append("")

    # § 5. Herdeiros
    lines.append("## 5. DOS HERDEIROS")
    lines.append("")
    lines.append(
        f"O falecido deixou {n_herdeiros} ({_numero_por_extenso(n_herdeiros)}) "
        "herdeiro(s) descendente(s), a saber:"
    )
    lines.append("")
    for h in inv.herdeiros:
        lines.append(f"- [QUALIFICAÇÃO DO {h.id}]")
    lines.append("")

    # § 6. Inventariante
    lines.append("## 6. DO INVENTARIANTE")
    lines.append("")
    lines.append(
        "Os herdeiros, neste ato, nomeiam como inventariante o herdeiro "
        "[QUALIFICAÇÃO DO INVENTARIANTE], nos termos dos artigos 617 e 618 "
        "do Código de Processo Civil em vigor."
    )
    lines.append("")

    # § 7. Bens
    lines.append("## 7. DOS BENS")
    lines.append("")
    lines.append('O "de cujus" possuía na ocasião da abertura da sucessão os seguintes bens:')
    lines.append("")
    for idx, bem in enumerate(inv.bens, start=1):
        lines.append(f"### 7.{idx}. {bem.tipo.value.upper()} — {bem.id}")
        lines.append("")
        lines.append(bem.descricao_generica or f"[DESCRIÇÃO COMPLETA DO BEM {bem.id}]")
        lines.append("")
        lines.append(f"Valor avaliado: **{_fmt_money(bem.valor)}**.")
        lines.append("")
        lines.append(f"Procedência: [PROCEDÊNCIA_{bem.id}].")
        lines.append("")
        lines.append(f"Matrícula / identificação registral: [MATRÍCULA DO IMÓVEL {bem.id}].")
        lines.append("")

    # § 8. Débitos (placeholder — cálculo avançado fica para sprint futura)
    lines.append("## 8. DOS DÉBITOS DO AUTOR DA HERANÇA")
    lines.append("")
    lines.append(
        "[DECLARAÇÃO DE DÉBITOS — preencher manualmente. Por padrão, declarar "
        "inexistência de débitos. Esta sprint NÃO calcula débitos: caso "
        "existam, o tabelião deve descrever e abater do monte partilhável "
        "antes da assinatura.]"
    )
    lines.append("")

    # § 9. Outras obrigações
    lines.append("## 9. OUTRAS OBRIGAÇÕES DO AUTOR DA HERANÇA")
    lines.append("")
    lines.append(
        "[DECLARAÇÃO DE OUTRAS OBRIGAÇÕES — preencher manualmente. Por "
        "padrão, declarar inexistência.]"
    )
    lines.append("")

    # § 10. Patrimônio (com 10.1 meação se houver, e 10.2 herança)
    lines.append("## 10. DO PATRIMÔNIO")
    lines.append("")
    lines.append(f"Patrimônio total: **{_fmt_money(resumo.patrimonio_total)}**.")
    lines.append("")
    lines.append(f"Monte partilhável: **{_fmt_money(resumo.monte_partilhavel)}**.")
    lines.append("")

    if inv.possui_meeiro:
        lines.append("### 10.1. DA MEAÇÃO")
        lines.append("")
        lines.append(
            "Caberá ao(à) meeiro(a) [QUALIFICAÇÃO DO MEEIRO], como pagamento "
            f"de sua meação, o valor de **{_fmt_money(resumo.valor_meacao)}**, "
            f"correspondente a {_fmt_pct(inv.percentual_meacao)} dos bens."
        )
        lines.append("")
        lines.append("### 10.2. DA HERANÇA")
    else:
        lines.append("> Não há meação a apurar — autor da herança sem meeiro(a).")
        lines.append("")
        lines.append("### 10.1. DA HERANÇA")
    lines.append("")
    for idx, h in enumerate(inv.herdeiros, start=1):
        quinhao = resumo.quinhao_por_herdeiro.get(h.id, Decimal("0"))
        lines.append(
            f"{idx}. [QUALIFICAÇÃO DO {h.id}] — quinhão hereditário: "
            f"**{_fmt_money(quinhao)}** ({_fmt_pct(h.percentual_heranca)})."
        )
    lines.append("")

    # § 11. Plano de partilha
    lines.append("## 11. DA PARTILHA")
    lines.append("")
    lines.append(
        "Os bens descritos em § 7 são partilhados conforme o quadro abaixo. "
        "Os percentuais e valores espelham a distribuição declarada na entrada "
        "estruturada e os cálculos do sistema; eventual reescrita de partilha "
        "bem a bem é responsabilidade do tabelião antes da assinatura."
    )
    lines.append("")
    for idx, bem in enumerate(inv.bens, start=1):
        lines.append(f"### 11.{idx}. {bem.id}")
        lines.append("")
        lines.append("| Beneficiário | % do bem | Valor |")
        lines.append("|--------------|----------|-------|")
        resumo_bem = next((r for r in resumo.bens if r.bem_id == bem.id), None)
        if resumo_bem is not None:
            for q in resumo_bem.quinhoes:
                rotulo = (
                    "[QUALIFICAÇÃO DO MEEIRO]"
                    if q.beneficiario == BENEFICIARIO_MEEIRO
                    else f"[QUALIFICAÇÃO DO {q.beneficiario}]"
                )
                lines.append(
                    f"| `{q.beneficiario}` — {rotulo} | "
                    f"{_fmt_pct(q.percentual)} | {_fmt_money(q.valor)} |"
                )
        lines.append("")

    # § 12. Certidões
    lines.append("## 12. DAS CERTIDÕES E DOCUMENTOS APRESENTADOS")
    lines.append("")
    lines.append("Foram apresentadas as seguintes certidões e documentos:")
    lines.append("")
    lines.append("- [CERTIDÕES FISCAIS] — Certidão Negativa de Débitos Inscritos em Dívida Ativa.")
    lines.append("- Certidões Negativas de Débitos Trabalhistas.")
    lines.append("- Certidão Negativa de Ações Cíveis.")
    lines.append(
        "- Certidão Negativa de Débitos Relativos aos Tributos Federais e à Dívida Ativa da União."
    )
    lines.append("")

    # § 13. CNIB
    lines.append("## 13. DA CONSULTA DE INDISPONIBILIDADE DE BENS")
    lines.append("")
    lines.append(
        "[CNIB] — Código HASH: [CNIB_HASH]; data: [CNIB_DATA]; "
        "STATUS: [CNIB_STATUS]; motivo: [CNIB_MOTIVO]."
    )
    lines.append("")

    # § 14. Declarações das partes
    lines.append("## 14. DAS DECLARAÇÕES DAS PARTES")
    lines.append("")
    lines.append(
        "As partes declaram que os bens partilhados encontram-se livres e "
        "desembaraçados de quaisquer ônus, dívidas ou tributos, e que não "
        "existem feitos ajuizados fundados em ações reais, pessoais ou "
        "reipersecutórias que afetem os bens e direitos ora partilhados."
    )
    lines.append("")

    # § 15. Declaração do advogado
    lines.append("## 15. DECLARAÇÃO DO ADVOGADO")
    lines.append("")
    lines.append(
        "[DADOS DO ADVOGADO] / [QUALIFICAÇÃO DO ADVOGADO] declara que "
        "prestou assistência jurídica e acompanhou a lavratura desta "
        "escritura pública, na qualidade de advogado das partes."
    )
    lines.append("")

    # § 16. ITCMD
    lines.append("## 16. DO ITCMD")
    lines.append("")
    lines.append(
        "Demonstrativo de Cálculo do ITCD Causa Mortis nº [GUIA ITCMD] / "
        "[ITCMD_SPL_N], referente ao ESPÓLIO, emitido pela Secretaria de "
        "Estado da Economia."
    )
    lines.append("")

    # § 17. Outras declarações
    lines.append("## 17. OUTRAS DECLARAÇÕES")
    lines.append("")
    lines.append("Texto padrão do Provimento 46/2020 CGJ-GO c/c Decreto 93.240/86, art. 1º, § 3º.")
    lines.append("")

    # § 18. Declarações finais
    lines.append("## 18. DECLARAÇÕES FINAIS")
    lines.append("")
    lines.append("Texto padrão da Resolução 35 CNJ, art. 3º.")
    lines.append("")

    # § 19. Únicos herdeiros
    lines.append("## 19. DA DECLARAÇÃO DE ÚNICOS HERDEIROS")
    lines.append("")
    lines.append("Texto padrão do art. 21 da Resolução 35 CNJ.")
    lines.append("")

    # § 20. LGPD
    lines.append("## 20. TRATAMENTO DE DADOS PESSOAIS — LGPD")
    lines.append("")
    lines.append("Cláusula padrão (Lei 13.709/2018; Provimento CNJ 134/2022; CNPFE/2023 TJ-GO).")
    lines.append("")

    # Encerramento
    lines.append("---")
    lines.append("")
    lines.append("## ENCERRAMENTO")
    lines.append("")
    lines.append("EMITIDA A DOI conforme Instrução Normativa SRFB nº 1.112/2010.")
    lines.append("")
    lines.append("Emolumentos: R$ [EMOLUMENTOS]. Taxa Judiciária: R$ [TAXA_JUDICIARIA].")
    lines.append("")

    # Alerta de centavos — política ADR-009
    if resumo.divergencia_centavos > Decimal("0"):
        lines.append("---")
        lines.append("")
        lines.append("## ⚠ AVISO TÉCNICO — DIVERGÊNCIA DE CENTAVOS")
        lines.append("")
        lines.append(
            f"> Foi detectada divergência de **{_fmt_money(resumo.divergencia_centavos)}** "
            "entre o patrimônio total e a soma efetivamente distribuída."
        )
        lines.append(
            "> Este resíduo decorre do arredondamento dos percentuais a 2 "
            "casas decimais (ex.: 33,33% × 3 = 99,99%)."
        )
        lines.append(
            "> Conforme política da ADR-009, o sistema **não corrige centavos "
            "silenciosamente**. O tabelião deve revisar a partilha bem a bem "
            "e, se necessário, reescrever a distribuição manualmente antes da "
            "assinatura."
        )
        lines.append("")

    # Campo de revisão humana
    lines.append("---")
    lines.append("")
    lines.append("## CAMPO DE REVISÃO HUMANA")
    lines.append("")
    lines.append(
        "Esta minuta-base foi produzida pelo Cartório System sem dados "
        "pessoais reais e exige revisão completa antes da lavratura. O "
        "tabelião responsável deve preencher os placeholders, conferir os "
        "valores apurados e, se necessário, reescrever a partilha."
    )
    lines.append("")
    lines.append("| Etapa | Responsável | Data | Observação |")
    lines.append("|-------|-------------|------|------------|")
    lines.append(
        "| Revisão de qualificações (Engegraph) | [PREENCHER] | [PREENCHER] | [PREENCHER] |"
    )
    lines.append("| Conferência de valores e cálculos | [PREENCHER] | [PREENCHER] | [PREENCHER] |")
    lines.append("| Validação fiscal (ITCMD/DOI) | [PREENCHER] | [PREENCHER] | [PREENCHER] |")
    lines.append("| Aprovação final do tabelião | [PREENCHER] | [PREENCHER] | [PREENCHER] |")
    lines.append("")

    return "\n".join(lines) + "\n"


_NUMEROS_POR_EXTENSO = {
    1: "um",
    2: "dois",
    3: "três",
    4: "quatro",
    5: "cinco",
    6: "seis",
    7: "sete",
    8: "oito",
    9: "nove",
    10: "dez",
}


def _numero_por_extenso(n: int) -> str:
    return _NUMEROS_POR_EXTENSO.get(n, str(n))


__all__ = ["render_minuta_markdown", "render_resumo_markdown"]
