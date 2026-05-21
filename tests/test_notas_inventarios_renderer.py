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
    "[CNIB]",
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


def test_minuta_com_meeiro_inclui_meeiro_na_distribuicao_dos_bens() -> None:
    md = _render(_build_inventario_com_meeiro())
    assert "## 11. DA PARTILHA" in md
    # cada bem tem uma seção 11.N
    assert "### 11.1. IMOVEL_1" in md
    assert "### 11.2. SALDO_1" in md
    # meeiro aparece como `MEEIRO` na tabela de cada bem
    assert "`MEEIRO`" in md


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
        "## 10. DO PATRIMÔNIO",
        "## 11. DA PARTILHA",
        "## 12. DAS CERTIDÕES E DOCUMENTOS APRESENTADOS",
        "## 13. DA CONSULTA DE INDISPONIBILIDADE DE BENS",
        "## 14. DAS DECLARAÇÕES DAS PARTES",
        "## 15. DECLARAÇÃO DO ADVOGADO",
        "## 16. DO ITCMD",
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


def test_minuta_referencia_matricula_por_bem() -> None:
    md = _render(_build_inventario_com_meeiro())
    assert "[MATRÍCULA DO IMÓVEL IMOVEL_1]" in md
    assert "[MATRÍCULA DO IMÓVEL SALDO_1]" in md


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
