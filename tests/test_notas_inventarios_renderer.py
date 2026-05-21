"""Testes da renderização Markdown da minuta-base de inventário.

Política dos testes:

- a minuta-base é gerada apenas com placeholders e dados estruturados
  fictícios — qualquer ocorrência de PII real (CPF, RG, nome, matrícula
  real) é considerada falha do teste;
- placeholders obrigatórios da Sprint NOTAS-INVENTARIO-2 devem aparecer
  literalmente;
- comportamento condicional (com meeiro / sem meeiro / alerta de centavos)
  é coberto explicitamente.
"""

from __future__ import annotations

import re
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

from app.modules.notas.inventarios.application.calculator import InventarioCalculator
from app.modules.notas.inventarios.application.renderer import render_minuta_markdown
from app.modules.notas.inventarios.domain.models import (
    BENEFICIARIO_MEEIRO,
    Bem,
    Distribuicao,
    Herdeiro,
    Inventario,
    TipoBem,
)
from app.modules.notas.inventarios.infrastructure.loaders import load_inventario

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = PROJECT_ROOT / "app" / "modules" / "notas" / "inventarios" / "examples"
TEMPLATE = (
    PROJECT_ROOT
    / "app"
    / "modules"
    / "notas"
    / "inventarios"
    / "infrastructure"
    / "templates"
    / "inventario_extrajudicial_padrao.md.j2"
)

PLACEHOLDERS_OBRIGATORIOS = [
    "[QUALIFICAÇÃO DO AUTOR DA HERANÇA]",
    "[CERTIDÃO DE ÓBITO]",
    "[DADOS DO ADVOGADO]",
    "[GUIA ITCMD]",
    "[CERTIDÕES FISCAIS]",
    "[CNIB_HASH]",
    "[CNIB_DATA]",
    "[CNIB_STATUS]",
    "[CPF_AUTOR_HERANCA]",
]

# Padrões de PII real que NUNCA podem aparecer em exemplos ou template.
_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("CPF", re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")),
    ("CNPJ", re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")),
    ("CEP", re.compile(r"\b\d{5}-\d{3}\b")),
    ("Data dd/mm/aaaa", re.compile(r"\b\d{2}/\d{2}/\d{4}\b")),
    ("E-mail", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("Telefone (DDD) 9xxxx-xxxx", re.compile(r"\(\d{2}\)\s*\d{4,5}-\d{4}")),
]


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
                descricao_generica="Imóvel urbano objeto da matrícula [MATRICULA]",
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
                descricao_generica="Saldo bancário em instituição [BANCO]",
                valor=Decimal("400000.00"),
                distribuicao=(
                    Distribuicao(beneficiario=BENEFICIARIO_MEEIRO, percentual=Decimal("50")),
                    Distribuicao(beneficiario="HERDEIRO_1", percentual=Decimal("25")),
                    Distribuicao(beneficiario="HERDEIRO_2", percentual=Decimal("25")),
                ),
            ),
        ),
    )


def _build_inventario_sem_meeiro_com_residuo() -> Inventario:
    """Caso com 3 herdeiros e percentuais 33,33%/33,33%/33,34%.

    Valores escolhidos para forçar resíduo de centavo após arredondamento
    (R$ 100,10 × 33,33% = R$ 33,3633 ≈ R$ 33,36; 3×R$ 33,36 + 0 = R$ 100,08;
    soma distribuída fica abaixo do patrimônio em poucos centavos).
    """

    return Inventario(
        tipo_ato="inventario_extrajudicial",
        possui_meeiro=False,
        percentual_meacao=Decimal("0"),
        patrimonio_total=Decimal("100.10"),
        herdeiros=(
            Herdeiro(id="HERDEIRO_1", percentual_heranca=Decimal("33.33")),
            Herdeiro(id="HERDEIRO_2", percentual_heranca=Decimal("33.33")),
            Herdeiro(id="HERDEIRO_3", percentual_heranca=Decimal("33.34")),
        ),
        bens=(
            Bem(
                id="IMOVEL_1",
                tipo=TipoBem.IMOVEL,
                descricao_generica="Imóvel rural objeto da matrícula [MATRICULA]",
                valor=Decimal("100.10"),
                distribuicao=(
                    Distribuicao(beneficiario="HERDEIRO_1", percentual=Decimal("33.33")),
                    Distribuicao(beneficiario="HERDEIRO_2", percentual=Decimal("33.33")),
                    Distribuicao(beneficiario="HERDEIRO_3", percentual=Decimal("33.34")),
                ),
            ),
        ),
    )


def _render(inv: Inventario) -> str:
    resumo = InventarioCalculator().compute(inv)
    return render_minuta_markdown(inv, resumo)


# ---------------------------------------------------------------------------
# Renderização com meeiro
# ---------------------------------------------------------------------------


def test_minuta_com_meeiro_contem_secao_de_meacao() -> None:
    md = _render(_build_inventario_com_meeiro())
    assert "## 10. DO PATRIMÔNIO" in md
    assert "### 10.1. DA MEAÇÃO" in md
    assert "[QUALIFICAÇÃO DO MEEIRO]" in md
    assert "Caberá ao(à) meeiro(a)" in md


def test_minuta_com_meeiro_lista_qualificacao_meeiro_em_secao_1() -> None:
    md = _render(_build_inventario_com_meeiro())
    assert "### 1.2. COMO MEEIRO(A)" in md
    assert "- [QUALIFICAÇÃO DO MEEIRO]" in md


def test_minuta_com_meeiro_inclui_quinhao_de_meeiro_em_alineas() -> None:
    """§ 11 com meeiro: subitem 11.1 é o quinhão do meeiro, em alíneas."""

    md = _render(_build_inventario_com_meeiro())
    assert "## 11. DA PARTILHA DO AUTOR DA HERANÇA" in md
    # subitem 11.1 reservado ao meeiro quando houver
    assert "### 11.1. Quinhão do(a) meeiro(a)" in md
    # cabeçalho cartorário do meeiro
    assert "Caberá ao(à) meeiro(a) [QUALIFICAÇÃO DO MEEIRO]" in md
    # alíneas com a participação em cada bem
    assert "a) 50,00% do bem descrito e caracterizado no item 7.1" in md
    assert "b) 50,00% do bem descrito e caracterizado no item 7.2" in md


# ---------------------------------------------------------------------------
# Renderização sem meeiro
# ---------------------------------------------------------------------------


def test_minuta_sem_meeiro_nao_contem_secao_10_1_meacao() -> None:
    md = _render(_build_inventario_sem_meeiro_com_residuo())
    assert "### 10.1. DA MEAÇÃO" not in md
    assert "Caberá ao(à) meeiro(a)" not in md
    # E não lista MEEIRO na qualificação das partes.
    assert "### 1.2. COMO MEEIRO(A)" not in md


def test_minuta_sem_meeiro_explicita_inexistencia_de_meacao() -> None:
    md = _render(_build_inventario_sem_meeiro_com_residuo())
    assert "Não há meação a apurar" in md


def test_minuta_sem_meeiro_nao_referencia_meeiro_em_partilha() -> None:
    md = _render(_build_inventario_sem_meeiro_com_residuo())
    # nenhuma linha da tabela de partilha pode mencionar MEEIRO como beneficiário
    # (o aviso de "não há meação" pode mencionar a palavra meeiro, então
    # checamos a forma `MEEIRO` em backticks que aparece nas tabelas).
    assert "`MEEIRO`" not in md


# ---------------------------------------------------------------------------
# Estrutura mínima e placeholders obrigatórios
# ---------------------------------------------------------------------------


def test_minuta_contem_todas_as_secoes_de_1_a_20() -> None:
    md = _render(_build_inventario_com_meeiro())
    titulos = [
        "## 1. DA QUALIFICAÇÃO DAS PARTES",
        "## 2. DO AUTOR DA HERANÇA",
        "## 3. DO FALECIMENTO",
        "## 4. DA INEXISTÊNCIA DE TESTAMENTO",
        "## 5. DOS HERDEIROS",
        "## 6. DO INVENTARIANTE",
        "## 7. DOS BENS",
        "## 8. DOS DÉBITOS DO AUTOR DA HERANÇA",
        "## 9. OUTRAS OBRIGAÇÕES DO AUTOR DA HERANÇA",
        "## 10. DO PATRIMÔNIO DO AUTOR DA HERANÇA",
        "## 11. DA PARTILHA DO AUTOR DA HERANÇA",
        "## 12. DAS CERTIDÕES E DOCUMENTOS APRESENTADOS",
        "## 13. DA CONSULTA DE INDISPONIBILIDADE DE BENS",
        "## 14. DAS DECLARAÇÕES DAS PARTES",
        "## 15. DECLARAÇÃO DO ADVOGADO",
        '## 16. DO IMPOSTO SOBRE A TRANSMISSÃO "CAUSA MORTIS" E DOAÇÃO — ITCMD',
        "## 17. OUTRAS DECLARAÇÕES",
        "## 18. DECLARAÇÕES FINAIS",
        "## 19. DA DECLARAÇÃO DE ÚNICOS HERDEIROS",
        "## 20. TRATAMENTO DE DADOS PESSOAIS — LGPD",
        "## ENCERRAMENTO",
        "## CAMPO DE REVISÃO HUMANA",
    ]
    for titulo in titulos:
        assert titulo in md, f"título ausente: {titulo!r}"


def test_minuta_traz_aviso_de_rascunho_humano() -> None:
    md = _render(_build_inventario_com_meeiro())
    assert "MINUTA-BASE — RASCUNHO SUJEITO À REVISÃO HUMANA" in md


def test_minuta_contem_placeholders_obrigatorios() -> None:
    md = _render(_build_inventario_com_meeiro())
    for placeholder in PLACEHOLDERS_OBRIGATORIOS:
        assert placeholder in md, f"placeholder ausente: {placeholder!r}"


def test_minuta_referencia_cada_herdeiro_por_id() -> None:
    md = _render(_build_inventario_com_meeiro())
    assert "[QUALIFICAÇÃO DO HERDEIRO_1]" in md
    assert "[QUALIFICAÇÃO DO HERDEIRO_2]" in md


def test_minuta_referencia_matricula_por_bem_imovel() -> None:
    """Procedência detalhada com matrícula só é renderizada para tipo imóvel.

    Bens não-imóveis (dinheiro, veículo, direito, outro) usam o bloco
    genérico "Procedência / identificação". Ver § 7 do
    `render_minuta_markdown`.
    """

    md = _render(_build_inventario_com_meeiro())
    assert "[MATRÍCULA DO IMÓVEL IMOVEL_1]" in md
    # SALDO_1 é dinheiro — não deve receber o bloco de matrícula registral.
    assert "[MATRÍCULA DO IMÓVEL SALDO_1]" not in md
    assert "[PROCEDÊNCIA_SALDO_1]" in md


def test_minuta_inclui_campo_de_revisao_humana_em_tabela() -> None:
    md = _render(_build_inventario_com_meeiro())
    assert "## CAMPO DE REVISÃO HUMANA" in md
    assert "Aprovação final do tabelião" in md
    assert "| Etapa | Responsável | Data | Observação |" in md


# ---------------------------------------------------------------------------
# Anti-PII em exemplos versionados e no template
# ---------------------------------------------------------------------------


def _assert_sem_pii(texto: str, origem: str) -> None:
    for nome, pattern in _PII_PATTERNS:
        match = pattern.search(texto)
        assert match is None, (
            f"PII suspeita ({nome}) em {origem}: {match.group() if match else ''!r}"
        )


def test_exemplo_inventario_simples_nao_contem_pii() -> None:
    texto = (EXAMPLES / "inventario_simples.yaml").read_text(encoding="utf-8")
    _assert_sem_pii(texto, "examples/inventario_simples.yaml")


def test_exemplo_inventario_sem_meeiro_nao_contem_pii() -> None:
    texto = (EXAMPLES / "inventario_sem_meeiro.yaml").read_text(encoding="utf-8")
    _assert_sem_pii(texto, "examples/inventario_sem_meeiro.yaml")


def test_template_padrao_nao_contem_pii() -> None:
    texto = TEMPLATE.read_text(encoding="utf-8")
    _assert_sem_pii(texto, "templates/inventario_extrajudicial_padrao.md.j2")


def test_minuta_renderizada_a_partir_de_exemplo_nao_contem_pii() -> None:
    inv = load_inventario(EXAMPLES / "inventario_simples.yaml")
    md = _render(inv)
    _assert_sem_pii(md, "minuta renderizada a partir de inventario_simples.yaml")


# ---------------------------------------------------------------------------
# Alerta de centavos na minuta
# ---------------------------------------------------------------------------


def test_minuta_inclui_alerta_de_centavos_quando_aplicavel() -> None:
    md = _render(_build_inventario_sem_meeiro_com_residuo())
    assert "AVISO TÉCNICO — DIVERGÊNCIA DE CENTAVOS" in md
    assert "ADR-009" in md


def test_minuta_sem_residuo_nao_inclui_alerta_de_centavos() -> None:
    md = _render(_build_inventario_com_meeiro())
    assert "AVISO TÉCNICO — DIVERGÊNCIA DE CENTAVOS" not in md


# ---------------------------------------------------------------------------
# CLI: --render-minuta e ausência
# ---------------------------------------------------------------------------


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "app.modules.notas.inventarios.interfaces.cli",
            *args,
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_sem_render_minuta_nao_gera_inventario_minuta(tmp_path: Path) -> None:
    out = tmp_path / "saida"
    proc = _run_cli(
        "--input",
        str(EXAMPLES / "inventario_simples.yaml"),
        "--output-dir",
        str(out),
    )
    assert proc.returncode == 0, proc.stderr
    assert (out / "inventario_validacao.json").exists()
    assert (out / "inventario_resumo.md").exists()
    assert not (out / "inventario_minuta.md").exists(), (
        "minuta gerada sem --render-minuta — contrato anterior quebrado"
    )


def test_cli_com_render_minuta_gera_inventario_minuta(tmp_path: Path) -> None:
    out = tmp_path / "saida"
    proc = _run_cli(
        "--input",
        str(EXAMPLES / "inventario_simples.yaml"),
        "--output-dir",
        str(out),
        "--render-minuta",
    )
    assert proc.returncode == 0, proc.stderr
    minuta = out / "inventario_minuta.md"
    assert minuta.exists()
    md = minuta.read_text(encoding="utf-8")
    assert "ESCRITURA PÚBLICA DE INVENTÁRIO E PARTILHA" in md
    assert "[QUALIFICAÇÃO DO HERDEIRO_1]" in md
    _assert_sem_pii(md, "inventario_minuta.md (CLI)")


def test_cli_com_render_minuta_em_caso_sem_meeiro_gera_minuta(tmp_path: Path) -> None:
    out = tmp_path / "saida_sem_meeiro"
    proc = _run_cli(
        "--input",
        str(EXAMPLES / "inventario_sem_meeiro.yaml"),
        "--output-dir",
        str(out),
        "--render-minuta",
    )
    assert proc.returncode == 0, proc.stderr
    md = (out / "inventario_minuta.md").read_text(encoding="utf-8")
    assert "Não há meação a apurar" in md
    # exemplo escolhido para que NÃO haja divergência (200000/100000 dividem
    # exatos por 33,33/33,33/33,34) — o caso com alerta é coberto no teste
    # `test_minuta_inclui_alerta_de_centavos_quando_aplicavel`.
    assert "AVISO TÉCNICO — DIVERGÊNCIA DE CENTAVOS" not in md


# ---------------------------------------------------------------------------
# Reforço cartorário introduzido na Sprint NOTAS-INVENTARIO-3
# ---------------------------------------------------------------------------


def test_minuta_inclui_declaracao_pep_em_secao_1() -> None:
    """Declaração de pessoa politicamente exposta (Resolução COAF 29/2017)."""

    md = _render(_build_inventario_com_meeiro())
    assert "Resolução COAF nº 29" in md
    assert "politicamente expostas" in md


def test_minuta_inclui_frase_de_transicao_para_autor_da_heranca() -> None:
    md = _render(_build_inventario_com_meeiro())
    assert "Pelos outorgantes e reciprocamente outorgados" in md
    assert "foi-me requerido seja feito o inventário" in md


def test_minuta_secao_2_orienta_engegraph_a_preencher_qualificacao() -> None:
    """§ 2 deve listar os campos esperados do Engegraph (RG, CPF, regime)."""

    md = _render(_build_inventario_com_meeiro())
    assert "preencher pelo Engegraph com nome civil completo" in md
    assert "estado civil ao tempo do óbito" in md
    assert "regime de bens" in md


def test_minuta_secao_3_orienta_engegraph_a_preencher_certidao_de_obito() -> None:
    md = _render(_build_inventario_com_meeiro())
    assert "data e hora do óbito" in md
    assert "Cartório de Registro Civil das Pessoas Naturais" in md


def test_minuta_secao_6_inventariante_inclui_poderes_e_aceite() -> None:
    md = _render(_build_inventario_com_meeiro())
    assert "conferindo-lhe todos os poderes" in md
    assert "representar o espólio, ativa e passivamente" in md
    assert "aceita este encargo" in md
    assert "responsabilidade civil e criminal" in md


def test_minuta_imovel_inclui_procedencia_detalhada() -> None:
    """§ 7 para bens do tipo imóvel deve detalhar matrícula, RI e título."""

    md = _render(_build_inventario_com_meeiro())
    assert "Registro Imobiliário de [CIDADE_RI]" in md
    assert "Certidão de Inteiro Teor" in md
    assert "DA PROCEDÊNCIA DA AQUISIÇÃO" in md
    assert "[TÍTULO AQUISITIVO IMOVEL_1]" in md
    assert "Repartição Pública Competente" in md


def test_minuta_bem_nao_imovel_usa_bloco_generico_de_procedencia() -> None:
    """SALDO_1 é dinheiro — deve receber bloco genérico, não o de imóvel."""

    md = _render(_build_inventario_com_meeiro())
    # cabeçalho de "DA PROCEDÊNCIA DA AQUISIÇÃO" aparece só para o imóvel;
    # o bloco genérico aparece em SALDO_1.
    assert "[PROCEDÊNCIA_SALDO_1]" in md
    # garante que o bloco completo de imóvel NÃO contamina o bloco do saldo.
    assert "[SELO_DIGITAL_SALDO_1]" not in md
    assert "[TÍTULO AQUISITIVO SALDO_1]" not in md


def test_minuta_secao_10_traz_redacao_cartoraria() -> None:
    md = _render(_build_inventario_com_meeiro())
    assert "O patrimônio total do autor da herança" in md
    assert "avaliados pela repartição pública competente" in md
    # § 10.2.x para cada herdeiro
    assert "**10.2.1.**" in md
    assert "**10.2.2.**" in md


def test_minuta_secao_10_sem_meeiro_usa_numeracao_10_1_x() -> None:
    md = _render(_build_inventario_sem_meeiro_com_residuo())
    # sem meeiro, herdeiros aparecem em 10.1.x (não 10.2.x).
    assert "**10.1.1.**" in md
    assert "**10.1.2.**" in md
    assert "**10.1.3.**" in md
    assert "**10.2.1.**" not in md


def test_minuta_secao_11_usa_apenas_alineas_sem_tabela() -> None:
    """§ 11 usa apenas alíneas (a, b, c…), sem quadro/tabela.

    Política da Sprint NOTAS-INVENTARIO-3-FINAL: o modelo padrão da serventia
    é cartorário em alíneas; tabelas tabulares **não** aparecem na minuta.
    Quadros vivem em `inventario_resumo.md` (resumo técnico) e no JSON de
    validação.
    """

    md = _render(_build_inventario_com_meeiro())
    # alíneas presentes (mínimo a) e b) — exemplo tem 2 bens)
    assert "a) 50,00% do bem descrito" in md
    assert "b) 50,00% do bem descrito" in md
    # cada herdeiro aparece como bloco em prosa
    assert "recebe como pagamento de sua herança o seguinte" in md
    # subitem 11.x para cada parte, em prosa cartorária
    assert "### 11.2. Quinhão de [QUALIFICAÇÃO DO HERDEIRO_1]" in md
    assert "### 11.3. Quinhão de [QUALIFICAÇÃO DO HERDEIRO_2]" in md


def test_minuta_secao_11_nao_contem_cabecalho_de_tabela() -> None:
    """A minuta cartorária NUNCA pode ter cabeçalho de tabela de partilha."""

    md = _render(_build_inventario_com_meeiro())
    # Cabeçalhos típicos de tabela markdown de partilha removidos:
    assert "| Beneficiário | % do bem | Valor |" not in md
    assert "|--------------|----------|-------|" not in md
    # "Quadro do bem" era o título dos antigos subitens 11.x tabulares;
    # também não pode mais aparecer.
    assert "Quadro do bem" not in md
    # Nenhum subitem 11.x deve começar com "Quadro" — só "Quinhão …".
    assert "### 11.1. Quadro" not in md


def test_minuta_secao_11_sem_meeiro_numera_herdeiros_de_1_em_diante() -> None:
    """Sem meeiro: 11.1 já é o primeiro herdeiro (sem subitem reservado)."""

    md = _render(_build_inventario_sem_meeiro_com_residuo())
    assert "### 11.1. Quinhão de [QUALIFICAÇÃO DO HERDEIRO_1]" in md
    assert "### 11.2. Quinhão de [QUALIFICAÇÃO DO HERDEIRO_2]" in md
    assert "### 11.3. Quinhão de [QUALIFICAÇÃO DO HERDEIRO_3]" in md
    # Não deve aparecer subitem dedicado ao meeiro.
    assert "Quinhão do(a) meeiro(a)" not in md
    # Confirma de novo que não há tabela mesmo sem meeiro.
    assert "| Beneficiário | % do bem | Valor |" not in md


def test_minuta_secao_12_cita_autor_da_heranca() -> None:
    md = _render(_build_inventario_com_meeiro())
    assert ('Foram-me apresentadas, em nome do "de cujus" [QUALIFICAÇÃO DO AUTOR DA HERANÇA]') in md


def test_minuta_secao_13_cnib_inclui_em_nome_de_e_hora() -> None:
    md = _render(_build_inventario_com_meeiro())
    assert "EM NOME DE: [QUALIFICAÇÃO DO AUTOR DA HERANÇA]" in md
    assert "CPF/CNPJ: [CPF_AUTOR_HERANCA]" in md
    assert "[CNIB_HORA]" in md


def test_minuta_secao_14_usa_subitens_14_1_e_14_2() -> None:
    md = _render(_build_inventario_com_meeiro())
    assert "**14.1.**" in md
    assert "**14.2.**" in md


def test_minuta_secao_17_traz_texto_cartorario_completo() -> None:
    """§ 17 deve transcrever Provimento 46/2020 e Decreto 93.240/86."""

    md = _render(_build_inventario_com_meeiro())
    assert "responsabilidade civil e criminal" in md
    assert "artigo 372, inciso VI" in md
    assert "Provimento nº 46/2020" in md
    assert "Decreto nº 93.240/86" in md


def test_minuta_secao_18_transcreve_art_3_resolucao_35_cnj() -> None:
    md = _render(_build_inventario_com_meeiro())
    assert "Oficial(a) Registrador(a) da Serventia" in md
    assert "artigos 167, inciso II, e 246 da Lei nº 6.015/73" in md
    assert "Art. 3º" in md


def test_minuta_secao_19_transcreve_art_21_e_inclui_uniao_estavel() -> None:
    md = _render(_build_inventario_com_meeiro())
    assert "únicos herdeiros do espólio" in md
    assert "artigo 21 da Resolução nº 35" in md
    assert "união estável" in md
    assert "artigo 1.725 do Código Civil" in md


def test_minuta_secao_20_lgpd_traz_texto_completo() -> None:
    md = _render(_build_inventario_com_meeiro())
    assert "Lei Geral de Proteção de Dados" in md
    assert "Provimento nº 134/2022" in md
    assert "CNPFE/2023 TJ-GO" in md
    assert "artigo 16 da Lei nº 6.015/73" in md


def test_minuta_encerramento_inclui_texto_e_assinaturas() -> None:
    md = _render(_build_inventario_com_meeiro())
    assert "E por se acharem assim contratados" in md
    assert "dispensando-se as testemunhas" in md
    assert "a escrevi, subscrevi e assino" in md
    # Linhas de assinatura para cada parte
    assert "### Assinaturas" in md
    assert "[QUALIFICAÇÃO DO HERDEIRO_1] (Herdeiro(a))" in md
    assert "[QUALIFICAÇÃO DO HERDEIRO_2] (Herdeiro(a))" in md
    assert "[QUALIFICAÇÃO DO MEEIRO] (Meeiro(a))" in md
    assert "[QUALIFICAÇÃO DO ADVOGADO] (Advogado(a))" in md
    assert "[QUALIFICAÇÃO DA TABELIÃ] (Tabeliã)" in md


def test_minuta_sem_meeiro_nao_inclui_linha_de_assinatura_de_meeiro() -> None:
    md = _render(_build_inventario_sem_meeiro_com_residuo())
    assert "(Meeiro(a))" not in md


def test_minuta_campo_de_revisao_humana_referencia_checklist() -> None:
    md = _render(_build_inventario_com_meeiro())
    assert "docs/modules/notas_inventarios_checklist.md" in md
    # nova etapa adicionada
    assert "Remoção de placeholders pendentes" in md


def test_minuta_template_j2_referencia_renderer_como_fonte_executavel() -> None:
    """O template .j2 deve declarar que NÃO é interpretado em runtime."""

    texto = TEMPLATE.read_text(encoding="utf-8")
    assert "FONTE EXECUTÁVEL" in texto
    assert "renderer.py" in texto


# ---------------------------------------------------------------------------
# CLI: validação falhando → minuta NÃO gerada
# ---------------------------------------------------------------------------


def test_cli_validacao_falha_nao_gera_inventario_minuta(tmp_path: Path) -> None:
    """Entrada inválida (Σ herdeiros ≠ 100): exit 1 e SEM `inventario_minuta.md`.

    A política é explícita: minuta-base só pode ser produzida quando a
    validação passa (CLI § ``--render-minuta``). Esta sprint encerra a
    pendência do contrato definida na NOTAS-INVENTARIO-2.
    """

    entrada = tmp_path / "inv_invalido.yaml"
    entrada.write_text(
        "tipo_ato: inventario_extrajudicial\n"
        "possui_meeiro: false\n"
        "percentual_meacao: 0\n"
        "patrimonio_total: 1000.00\n"
        "herdeiros:\n"
        "  - id: HERDEIRO_1\n"
        "    percentual_heranca: 40\n"  # soma 80, fora da tolerância
        "  - id: HERDEIRO_2\n"
        "    percentual_heranca: 40\n"
        "bens:\n"
        "  - id: SALDO_1\n"
        "    tipo: dinheiro\n"
        "    descricao_generica: 'Saldo bancário em [BANCO]'\n"
        "    valor: 1000.00\n"
        "    distribuicao:\n"
        "      - beneficiario: HERDEIRO_1\n"
        "        percentual: 50\n"
        "      - beneficiario: HERDEIRO_2\n"
        "        percentual: 50\n",
        encoding="utf-8",
    )
    out = tmp_path / "saida_invalida"
    proc = _run_cli(
        "--input",
        str(entrada),
        "--output-dir",
        str(out),
        "--render-minuta",
    )
    assert proc.returncode == 1, (
        f"esperado exit 1 por validação falhar; veio {proc.returncode}: stderr={proc.stderr!r}"
    )
    assert (out / "inventario_validacao.json").exists()
    assert not (out / "inventario_minuta.md").exists(), (
        "minuta gerada apesar de validação falhar — quebra o contrato da CLI"
    )
