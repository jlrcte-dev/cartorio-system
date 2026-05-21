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

    Esta função é a **fonte executável** da minuta-base — o template
    ``infrastructure/templates/inventario_extrajudicial_padrao.md.j2`` é
    mantido apenas como espelho textual para referência humana e auditoria,
    sem ser interpretado em runtime. A renderização é feita em Python puro
    para não introduzir dependência de Jinja2.

    A redação aproxima-se do modelo padrão da serventia (Cartório Costa
    Teixeira) — Resolução 35/2007 CNJ, Provimento 46/2020 CGJ-GO, Provimento
    134/2022 CNJ, IN SRFB 1.112/2010 — mas **nada substitui a revisão do
    tabelião**. Placeholders pessoais usam o formato ``[QUALIFICAÇÃO DO …]``
    ou ``[DADO]``; a substituição é responsabilidade do Engegraph + revisão
    humana antes da lavratura.

    O documento carrega:

    - cabeçalho + aviso explícito de "minuta-base";
    - texto fixo das cláusulas conforme legislação aplicável (Resolução 35
      CNJ, Provimentos 46/2020 e 134/2022 e Decreto 93.240/86);
    - placeholders explícitos para qualificações e dados externos;
    - cálculos determinísticos (patrimônio, meação, quinhões);
    - alerta técnico de centavos quando aplicável (ADR-009);
    - bloco final "Campo de revisão humana" com checklist mínimo.
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
    lines.append(
        "Reconhecidos como os próprios por meio dos documentos apresentados, "
        "do que dou fé. Declaram não serem pessoas politicamente expostas, no "
        "conceito e elenco da Resolução COAF nº 29, de 7 de dezembro de 2017."
    )
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
    lines.append(
        "Pelos outorgantes e reciprocamente outorgados, devidamente "
        "acompanhados por seu advogado, a seguir, foi-me requerido seja feito "
        "o inventário dos bens deixados por falecimento de "
        "[QUALIFICAÇÃO DO AUTOR DA HERANÇA], e declararam o seguinte:"
    )
    lines.append("")

    # § 2. Autor da herança
    lines.append("## 2. DO AUTOR DA HERANÇA")
    lines.append("")
    lines.append(
        "[QUALIFICAÇÃO DO AUTOR DA HERANÇA] — preencher pelo Engegraph com "
        "nome civil completo, nacionalidade, profissão, data e local de "
        "nascimento, filiação, número de RG, CPF, estado civil ao tempo do "
        "óbito e regime de bens (este último determina se há meeiro(a))."
    )
    lines.append("")

    # § 3. Falecimento
    lines.append("## 3. DO FALECIMENTO")
    lines.append("")
    lines.append(
        "[CERTIDÃO DE ÓBITO] — preencher pelo Engegraph com data e hora do "
        "óbito, cidade/UF, idade do falecido e dados da Certidão de Óbito "
        "(Cartório de Registro Civil das Pessoas Naturais, livro, folhas, "
        "termo e data da lavratura)."
    )
    lines.append("")

    # § 4. Inexistência de testamento
    lines.append("## 4. DA INEXISTÊNCIA DE TESTAMENTO")
    lines.append("")
    lines.append(
        'O "de cujus" não deixou testamento, tendo sido apresentada a '
        "Consulta ao Registro Central de Testamento Online emitida em "
        "[CENSEC_DATA], pelo Colégio Notarial do Brasil, conforme determinação "
        "do Provimento nº 56/2016 do Conselho Nacional de Justiça, onde NÃO "
        "CONSTA a lavratura de testamento público, aprovação de testamento "
        'cerrado ou revogação de testamento em nome do "de cujus".'
    )
    lines.append("")

    # § 5. Herdeiros
    lines.append("## 5. DOS HERDEIROS")
    lines.append("")
    lines.append(
        f"O falecido deixou {n_herdeiros} ({_numero_por_extenso(n_herdeiros)}) "
        "herdeiro(s) descendente(s), acima qualificado(s), a saber:"
    )
    lines.append("")
    for h in inv.herdeiros:
        lines.append(f"- [QUALIFICAÇÃO DO {h.id}]")
    lines.append("")

    # § 6. Inventariante
    lines.append("## 6. DO INVENTARIANTE")
    lines.append("")
    lines.append(
        "Os herdeiros descendentes, neste ato, nomeiam como inventariante do "
        '"de cujus" o herdeiro descendente [QUALIFICAÇÃO DO INVENTARIANTE], '
        "já qualificado, nos termos dos artigos 617 e 618 do Código de "
        "Processo Civil em vigor, conferindo-lhe todos os poderes que se "
        "fizerem necessários para representar o espólio, ativa e "
        "passivamente, judicial ou extrajudicialmente, nomear advogado e "
        "praticar todos os atos que se fizerem necessários à defesa do "
        "espólio e ao cumprimento de suas eventuais obrigações formais."
    )
    lines.append("")
    lines.append(
        "O nomeado inventariante declara, neste ato, que aceita este encargo, "
        "prestando compromisso de cumprir eficazmente seu mister, e declara "
        "estar ciente da responsabilidade civil e criminal pela declaração "
        "de bens e herdeiros e pela veracidade de todos os termos aqui "
        "relatados."
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
        if bem.tipo.value == "imovel":
            lines.append(
                f"Procedência: matrícula nº [MATRÍCULA DO IMÓVEL {bem.id}], do "
                "Registro Imobiliário de [CIDADE_RI], Comarca de [COMARCA_RI], "
                "Estado de [UF_RI], conforme Certidão de Inteiro Teor emitida em "
                f"[DATA_CIT_{bem.id}], selo digital nº [SELO_DIGITAL_{bem.id}]."
            )
            lines.append("")
            lines.append(
                f'DA PROCEDÊNCIA DA AQUISIÇÃO: o imóvel foi adquirido pelo "de '
                f'cujus" nos termos de [TÍTULO AQUISITIVO {bem.id}]. A Repartição '
                f"Pública Competente é [REPARTIÇÃO_{bem.id}] (SEFAZ ou Prefeitura), "
                f"que lhe atribuiu o valor de **{_fmt_money(bem.valor)}**, "
                "correspondendo à herança."
            )
        else:
            lines.append(
                f"Procedência / identificação: [PROCEDÊNCIA_{bem.id}] — "
                "preencher pelo Engegraph com dados específicos do bem "
                "(instituição financeira, placa do veículo, número de "
                "registro, contrato, etc.)."
            )
        lines.append("")

    # § 8. Débitos (placeholder — cálculo avançado fica para sprint futura)
    lines.append("## 8. DOS DÉBITOS DO AUTOR DA HERANÇA")
    lines.append("")
    lines.append(
        'Declaram os herdeiros descendentes que o "de cujus" não possuía '
        "débitos na ocasião da abertura da sucessão, assumindo quaisquer "
        "responsabilidades acerca desta declaração."
    )
    lines.append("")
    lines.append(
        "> Caso existam débitos, o tabelião deve substituir o parágrafo "
        "acima por descrição detalhada (credor, valor, vencimento) e abater "
        "do monte partilhável antes da assinatura. Esta minuta-base **NÃO** "
        "calcula débitos automaticamente."
    )
    lines.append("")

    # § 9. Outras obrigações
    lines.append("## 9. OUTRAS OBRIGAÇÕES DO AUTOR DA HERANÇA")
    lines.append("")
    lines.append(
        'Declaram os herdeiros descendentes que o "de cujus" não possuía '
        "outras obrigações a serem satisfeitas pelo mesmo na ocasião da "
        "abertura da sucessão, assumindo quaisquer responsabilidades acerca "
        "desta declaração."
    )
    lines.append("")

    # § 10. Patrimônio (com 10.1 meação se houver, e 10.2 herança)
    lines.append("## 10. DO PATRIMÔNIO DO AUTOR DA HERANÇA")
    lines.append("")
    itens_7 = ", ".join(f"7.{i}" for i in range(1, len(inv.bens) + 1))
    if inv.possui_meeiro:
        lines.append(
            "O patrimônio total do autor da herança, representado pelos bens "
            f"descritos nos itens {itens_7}, avaliados pela repartição pública "
            f"competente em **{_fmt_money(resumo.patrimonio_total)}**, "
            f"corresponde a **{_fmt_money(resumo.valor_meacao)}** à meação e "
            f"**{_fmt_money(resumo.monte_partilhavel)}** à herança."
        )
    else:
        lines.append(
            "O patrimônio total do autor da herança, representado pelos bens "
            f"descritos nos itens {itens_7}, avaliados pela repartição pública "
            f"competente em **{_fmt_money(resumo.patrimonio_total)}**, "
            "corresponde integralmente à herança, não havendo meação a "
            f"apurar — monte partilhável de **{_fmt_money(resumo.monte_partilhavel)}**."
        )
    lines.append("")

    if inv.possui_meeiro:
        lines.append("### 10.1. DA MEAÇÃO")
        lines.append("")
        lines.append(
            "Caberá ao(à) meeiro(a) [QUALIFICAÇÃO DO MEEIRO], como pagamento "
            f"de sua meação, o valor de **{_fmt_money(resumo.valor_meacao)}**, "
            f"correspondente a {_fmt_pct(inv.percentual_meacao)} dos bens "
            f"descritos e caracterizados nos itens {itens_7}."
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
        subitem = f"10.2.{idx}" if inv.possui_meeiro else f"10.1.{idx}"
        lines.append(
            f"**{subitem}.** O(A) herdeiro(a) descendente "
            f"[QUALIFICAÇÃO DO {h.id}], acima qualificado(a), recebe como "
            "pagamento de seu quinhão hereditário, o que lhe é de direito, "
            f"qual seja, o valor de **{_fmt_money(quinhao)}**, correspondente "
            f"a {_fmt_pct(h.percentual_heranca)} dos bens descritos e "
            f"caracterizados nos itens {itens_7}."
        )
        lines.append("")

    # § 11. Plano de partilha — apenas alíneas, conforme padrão da serventia.
    # Quadros/tabelas ficam restritos ao resumo técnico (inventario_resumo.md)
    # e ao JSON de validação; a minuta cartorária preserva a prosa em alíneas.
    lines.append("## 11. DA PARTILHA DO AUTOR DA HERANÇA")
    lines.append("")
    lines.append(
        "Por todo o exposto, ficará a partilha da seguinte forma. Os "
        "percentuais e valores são determinísticos a partir da entrada "
        "estruturada; eventual reescrita bem a bem é responsabilidade do "
        "tabelião antes da assinatura."
    )
    lines.append("")
    subitem_idx = 0
    if inv.possui_meeiro:
        subitem_idx += 1
        lines.append(f"### 11.{subitem_idx}. Quinhão do(a) meeiro(a)")
        lines.append("")
        lines.append(
            "**Caberá ao(à) meeiro(a) [QUALIFICAÇÃO DO MEEIRO], como pagamento "
            "de sua meação, o seguinte:**"
        )
        lines.append("")
        _append_descricao_por_beneficiario(lines, inv, resumo, BENEFICIARIO_MEEIRO)
        lines.append("")
    for h in inv.herdeiros:
        subitem_idx += 1
        lines.append(f"### 11.{subitem_idx}. Quinhão de [QUALIFICAÇÃO DO {h.id}]")
        lines.append("")
        lines.append(
            f"**O(A) herdeiro(a) descendente [QUALIFICAÇÃO DO {h.id}], acima "
            "qualificado(a), recebe como pagamento de sua herança o "
            "seguinte:**"
        )
        lines.append("")
        _append_descricao_por_beneficiario(lines, inv, resumo, h.id)
        lines.append("")

    # § 12. Certidões
    lines.append("## 12. DAS CERTIDÕES E DOCUMENTOS APRESENTADOS")
    lines.append("")
    lines.append(
        'Foram-me apresentadas, em nome do "de cujus" '
        "[QUALIFICAÇÃO DO AUTOR DA HERANÇA], as seguintes certidões e "
        "documentos:"
    )
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
        "Realizada a consulta na base de dados da Central Nacional de "
        "Indisponibilidade de Bens — CNIB, foi verificado o seguinte:"
    )
    lines.append("")
    lines.append("- EM NOME DE: [QUALIFICAÇÃO DO AUTOR DA HERANÇA]")
    lines.append("- CPF/CNPJ: [CPF_AUTOR_HERANCA]")
    lines.append("- Código HASH: [CNIB_HASH]")
    lines.append("- Data: [CNIB_DATA]   Hora: [CNIB_HORA]")
    lines.append("- STATUS: [CNIB_STATUS]")
    lines.append("- Motivo: [CNIB_MOTIVO]")
    lines.append("")

    # § 14. Declarações das partes
    lines.append("## 14. DAS DECLARAÇÕES DAS PARTES")
    lines.append("")
    lines.append("As partes declaram:")
    lines.append("")
    lines.append(
        "**14.1.** Que os bens ora partilhados encontram-se livres e "
        "desembaraçados de quaisquer ônus, dívidas ou tributos de quaisquer "
        "naturezas."
    )
    lines.append("")
    lines.append(
        "**14.2.** Que não existem feitos ajuizados fundados em ações reais, "
        "pessoais ou reipersecutórias que afetem os bens e direitos ora "
        "partilhados."
    )
    lines.append("")

    # § 15. Declaração do advogado
    lines.append("## 15. DECLARAÇÃO DO ADVOGADO")
    lines.append("")
    lines.append(
        "Na posição de advogado comum das partes, [DADOS DO ADVOGADO] / "
        "[QUALIFICAÇÃO DO ADVOGADO] declara que prestou assistência jurídica "
        "e acompanhou a lavratura desta escritura pública de inventário e "
        "partilha de bens e, na qualidade de advogado, assessorou e "
        "aconselhou seus constituintes, tendo conferido a correção do "
        "inventário, da partilha e seus valores, de acordo com a Lei."
    )
    lines.append("")

    # § 16. ITCMD
    lines.append('## 16. DO IMPOSTO SOBRE A TRANSMISSÃO "CAUSA MORTIS" E DOAÇÃO — ITCMD')
    lines.append("")
    lines.append(
        "Pelas partes foi-me apresentado o Demonstrativo de Cálculo do ITCD "
        "Causa Mortis nº [GUIA ITCMD] / [ITCMD_SPL_N], referente ao espólio "
        "de [QUALIFICAÇÃO DO AUTOR DA HERANÇA], emitido pela Secretaria de "
        "Estado da Economia, com data da última alteração em [ITCMD_DATA]."
    )
    lines.append("")

    # § 17. Outras declarações
    lines.append("## 17. OUTRAS DECLARAÇÕES")
    lines.append("")
    lines.append(
        "As partes afirmam, sob responsabilidade civil e criminal, que os "
        "fatos aqui relatados e as declarações feitas são a exata expressão "
        "da verdade. Os herdeiros descendentes, neste ato, declaram a "
        "inexistência de outras ações reais e pessoais reipersecutórias "
        "relativas aos imóveis e de outros ônus reais incidentes sobre os "
        "mesmos, nos termos do artigo 372, inciso VI, do Código de Normas e "
        "Procedimentos do Foro Extrajudicial da Corregedoria Geral de "
        "Justiça do Estado de Goiás (Provimento nº 46/2020) cumulado com o "
        "artigo 1º, parágrafo 3º, do Decreto nº 93.240/86; e ainda, pelo "
        "mesmo, a seguir, foi-me dito que aceita a presente Escritura "
        "Pública de Inventário e Partilha de Bens, tal como se contém e "
        "declaram."
    )
    lines.append("")

    # § 18. Declarações finais
    lines.append("## 18. DECLARAÇÕES FINAIS")
    lines.append("")
    lines.append(
        "Os herdeiros descendentes, pelo presente, autorizam o(a) Oficial(a) "
        "Registrador(a) da Serventia de Registro de Imóveis competente a "
        "proceder todas e quaisquer averbações que se fizerem necessárias "
        "para, posteriormente, efetuar o registro da presente Escritura "
        "Pública de Inventário e Partilha de Bens, consoante dispõem os "
        "artigos 167, inciso II, e 246 da Lei nº 6.015/73 (Lei de Registros "
        "Públicos)."
    )
    lines.append("")
    lines.append(
        "Aos herdeiros descendentes e ao advogado constituído foi dado "
        "conhecimento do disposto no artigo 3º da Resolução nº 35 do "
        'Conselho Nacional de Justiça: "Art. 3º As escrituras públicas de '
        "inventário e partilha, separação e divórcio consensuais não "
        "dependem de homologação judicial e são títulos hábeis para o "
        "registro civil e o registro imobiliário, para a transferência de "
        "bens e direitos, bem como para promoção de todos os atos "
        "necessários à materialização das transferências de bens e "
        "levantamento de valores (DETRAN, Junta Comercial, Registro Civil "
        "de Pessoas Jurídicas, instituições financeiras, companhias "
        'telefônicas, etc.)".'
    )
    lines.append("")

    # § 19. Únicos herdeiros
    lines.append("## 19. DA DECLARAÇÃO DE ÚNICOS HERDEIROS")
    lines.append("")
    lines.append(
        "Pelos herdeiros descendentes, acompanhados de seu advogado "
        "constituído, declaram para os devidos fins e efeitos de direito, "
        "sob pena de responsabilidade civil e criminal, que são os únicos "
        "herdeiros do espólio de [QUALIFICAÇÃO DO AUTOR DA HERANÇA], "
        "consoante dispõe o artigo 21 da Resolução nº 35 do Conselho "
        "Nacional de Justiça (CNJ), de 24 de abril de 2007."
    )
    lines.append("")
    lines.append(
        "Aos herdeiros descendentes e ao advogado constituído foi dado "
        "conhecimento de que a partilha realizada na presente Escritura "
        "Pública foi feita nos termos acordados entre si, e nos termos do "
        "Demonstrativo de Cálculo do ITCD Causa Mortis nº [GUIA ITCMD] / "
        "[ITCMD_SPL_N], referente aos bens deixados pelo espólio de "
        "[QUALIFICAÇÃO DO AUTOR DA HERANÇA], guia esta devidamente "
        "homologada, que me foi apresentada e cuja cópia ficará arquivada "
        "nestas notas, isentando esta Tabeliã de quaisquer responsabilidades "
        "quanto ao plano de partilha, assumindo os herdeiros descendentes e "
        "o advogado constituído toda e qualquer responsabilidade civil, "
        "fiscal e criminal, bem como responsabilidade sob qualquer correção "
        "que venha a ser exigida pelos órgãos competentes — Cartórios de "
        "Registros de Imóveis ou outros — arcando assim com todos os "
        "impostos, custas e emolumentos que porventura vierem a ser cobrados."
    )
    lines.append("")
    lines.append(
        "Os herdeiros declaram, sob pena de responsabilidade civil e "
        'criminal, que o "de cujus" não possuía relacionamento que '
        "configurasse união estável, respondendo, desta forma, pela evicção "
        "de direito em razão da comunicabilidade prevista no artigo 1.725 do "
        "Código Civil Brasileiro em vigor."
    )
    lines.append("")

    # § 20. LGPD
    lines.append("## 20. TRATAMENTO DE DADOS PESSOAIS — LGPD")
    lines.append("")
    lines.append(
        "Em conformidade com a Lei Geral de Proteção de Dados — LGPD (Lei nº "
        "13.709/2018), com o Provimento nº 134/2022 do Conselho Nacional de "
        "Justiça e com o Código de Normas e Procedimentos do Foro "
        "Extrajudicial do Tribunal de Justiça do Estado de Goiás "
        "(CNPFE/2023 TJ-GO), informa-se que os dados pessoais compartilhados "
        "com esta serventia serão tratados de forma a cumprir as obrigações "
        "previstas em leis (Leis nº 6.015/73 e nº 8.935/94) e a atender à "
        "finalidade pública desta serventia."
    )
    lines.append("")
    lines.append(
        "As principais hipóteses que legitimam o tratamento de dados pela "
        "serventia são o cumprimento de obrigação legal e regulatória, a "
        "execução de contrato e a execução de políticas públicas pela "
        "administração pública, nos termos do artigo 7º, incisos II, III e "
        "V, da LGPD. O tratamento é limitado ao mínimo necessário para "
        "cumprir tais finalidades, e a serventia adota medidas de segurança "
        "técnicas e administrativas aptas a proteger os dados pessoais "
        "armazenados, observando os padrões mínimos de tecnologia e "
        "segurança da informação exigidos pelo Provimento nº 74/2018 do CNJ."
    )
    lines.append("")
    lines.append(
        "As partes declaram que concordam com o tratamento e o backup dos "
        "seus dados pessoais para finalidades específicas da LGPD, cientes "
        "de que o presente instrumento poderá ser reproduzido a pedido de "
        "qualquer interessado independentemente de autorização expressa das "
        "partes, bem como demonstração de dados, ambos dentro do limite "
        "legal, por se tratar de instrumento público nos termos do artigo 16 "
        "da Lei nº 6.015/73."
    )
    lines.append("")

    # Encerramento
    lines.append("---")
    lines.append("")
    lines.append("## ENCERRAMENTO")
    lines.append("")
    lines.append(
        "Emitida a DOI — Declaração sobre Operações Imobiliárias, conforme "
        "Instrução Normativa nº 1.112, de 28 de dezembro de 2010, da "
        "Secretaria da Receita Federal do Brasil."
    )
    lines.append("")
    lines.append(
        "E por se acharem assim contratados, pediram-me que lhes fizesse a "
        "presente escritura, que, lida em voz alta, foi por todos aceita, "
        "outorgada e assinada, dispensando-se as testemunhas na forma legal. "
        "Eu, [QUALIFICAÇÃO DA TABELIÃ], a escrevi, subscrevi e assino."
    )
    lines.append("")
    lines.append("Emolumentos: R$ [EMOLUMENTOS]. Taxa Judiciária: R$ [TAXA_JUDICIARIA].")
    lines.append("")
    lines.append("### Assinaturas")
    lines.append("")
    linha_assinatura = "___________________________________"
    for h in inv.herdeiros:
        lines.append(f"{linha_assinatura}  — [QUALIFICAÇÃO DO {h.id}] (Herdeiro(a))")
        lines.append("")
    if inv.possui_meeiro:
        lines.append(f"{linha_assinatura}  — [QUALIFICAÇÃO DO MEEIRO] (Meeiro(a))")
        lines.append("")
    lines.append(f"{linha_assinatura}  — [QUALIFICAÇÃO DO ADVOGADO] (Advogado(a))")
    lines.append("")
    lines.append(f"{linha_assinatura}  — [QUALIFICAÇÃO DA TABELIÃ] (Tabeliã)")
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
        "valores apurados e, se necessário, reescrever a partilha. O "
        "checklist operacional completo está em "
        "`docs/modules/notas_inventarios_checklist.md`."
    )
    lines.append("")
    lines.append("| Etapa | Responsável | Data | Observação |")
    lines.append("|-------|-------------|------|------------|")
    lines.append(
        "| Revisão de qualificações (Engegraph) | [PREENCHER] | [PREENCHER] | [PREENCHER] |"
    )
    lines.append("| Conferência de valores e cálculos | [PREENCHER] | [PREENCHER] | [PREENCHER] |")
    lines.append("| Validação fiscal (ITCMD/DOI) | [PREENCHER] | [PREENCHER] | [PREENCHER] |")
    lines.append("| Remoção de placeholders pendentes | [PREENCHER] | [PREENCHER] | [PREENCHER] |")
    lines.append("| Aprovação final do tabelião | [PREENCHER] | [PREENCHER] | [PREENCHER] |")
    lines.append("")

    return "\n".join(lines) + "\n"


def _append_descricao_por_beneficiario(
    lines: list[str],
    inv: Inventario,
    resumo: ResumoInventario,
    beneficiario: str,
) -> None:
    """Anexa, no estilo cartorário com letras (a, b, c…), a participação de
    ``beneficiario`` em cada bem.

    Quando o beneficiário não tem participação em nenhum bem, a função emite
    uma linha explícita; quando há participação em pelo menos um bem,
    apenas os bens com percentual > 0 são enumerados.
    """

    letras = "abcdefghijklmnopqrstuvwxyz"
    linhas_bem: list[str] = []
    for bem_idx, bem in enumerate(inv.bens, start=1):
        resumo_bem = next((r for r in resumo.bens if r.bem_id == bem.id), None)
        if resumo_bem is None:
            continue
        quinhao = next(
            (q for q in resumo_bem.quinhoes if q.beneficiario == beneficiario),
            None,
        )
        if quinhao is None or quinhao.percentual <= Decimal("0"):
            continue
        letra = letras[len(linhas_bem)] if len(linhas_bem) < len(letras) else "?"
        linhas_bem.append(
            f"  {letra}) {_fmt_pct(quinhao.percentual)} do bem descrito e "
            f"caracterizado no item 7.{bem_idx} ({bem.id}), avaliado em "
            f"{_fmt_money(bem.valor)}, correspondendo a {_fmt_money(quinhao.valor)};"
        )
    if linhas_bem:
        lines.extend(linhas_bem)
    else:
        lines.append("  — sem participação em bens nesta partilha;")


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
