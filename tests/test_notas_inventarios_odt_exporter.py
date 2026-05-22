"""Testes do exportador ODT da minuta-base de inventário.

O ODT é um **artefato derivado** do Markdown canônico — estes testes
verificam a estrutura interna do pacote OpenDocument, a preservação dos
placeholders e a ausência de PII, além do contrato da CLI com a nova flag
``--export-odt``.
"""

from __future__ import annotations

import re
import subprocess
import sys
import zipfile
from pathlib import Path

from app.modules.notas.inventarios.application.calculator import InventarioCalculator
from app.modules.notas.inventarios.application.renderer import render_minuta_markdown
from app.modules.notas.inventarios.infrastructure.exporters import (
    export_inventario_odt,
    markdown_to_content_xml,
)
from app.modules.notas.inventarios.infrastructure.exporters.odt_exporter import (
    ODT_MIMETYPE,
)
from app.modules.notas.inventarios.infrastructure.loaders import load_inventario

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = PROJECT_ROOT / "app" / "modules" / "notas" / "inventarios" / "examples"

# Padrões de PII real que NUNCA podem aparecer no ODT (espelham o renderer).
_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("CPF", re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")),
    ("CNPJ", re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")),
    ("CEP", re.compile(r"\b\d{5}-\d{3}\b")),
    ("Data dd/mm/aaaa", re.compile(r"\b\d{2}/\d{2}/\d{4}\b")),
    ("E-mail", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("Telefone (DDD) 9xxxx-xxxx", re.compile(r"\(\d{2}\)\s*\d{4,5}-\d{4}")),
]


def _minuta_markdown_exemplo() -> str:
    inv = load_inventario(EXAMPLES / "inventario_simples.yaml")
    resumo = InventarioCalculator().compute(inv)
    return render_minuta_markdown(inv, resumo)


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "app.modules.notas.inventarios.interfaces.cli", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# Estrutura do pacote ODF
# ---------------------------------------------------------------------------


def test_exporter_cria_arquivo_odt(tmp_path: Path) -> None:
    destino = tmp_path / "minuta.odt"
    resultado = export_inventario_odt(_minuta_markdown_exemplo(), destino)
    assert resultado == destino
    assert destino.exists()
    assert destino.stat().st_size > 0


def test_odt_e_zip_valido(tmp_path: Path) -> None:
    destino = tmp_path / "minuta.odt"
    export_inventario_odt(_minuta_markdown_exemplo(), destino)
    assert zipfile.is_zipfile(destino)
    with zipfile.ZipFile(destino) as zf:
        assert zf.testzip() is None


def test_mimetype_e_o_primeiro_arquivo_e_sem_compressao(tmp_path: Path) -> None:
    destino = tmp_path / "minuta.odt"
    export_inventario_odt(_minuta_markdown_exemplo(), destino)
    with zipfile.ZipFile(destino) as zf:
        infos = zf.infolist()
        assert infos[0].filename == "mimetype", "mimetype deve ser a 1ª entrada"
        assert infos[0].compress_type == zipfile.ZIP_STORED, (
            "mimetype deve ser gravado sem compressão"
        )


def test_mimetype_tem_valor_correto(tmp_path: Path) -> None:
    destino = tmp_path / "minuta.odt"
    export_inventario_odt(_minuta_markdown_exemplo(), destino)
    with zipfile.ZipFile(destino) as zf:
        assert zf.read("mimetype").decode("ascii") == ODT_MIMETYPE
        assert ODT_MIMETYPE == "application/vnd.oasis.opendocument.text"


def test_odt_contem_content_xml_e_manifest(tmp_path: Path) -> None:
    destino = tmp_path / "minuta.odt"
    export_inventario_odt(_minuta_markdown_exemplo(), destino)
    with zipfile.ZipFile(destino) as zf:
        nomes = set(zf.namelist())
    assert "content.xml" in nomes
    assert "META-INF/manifest.xml" in nomes
    assert "styles.xml" in nomes
    assert "meta.xml" in nomes


# ---------------------------------------------------------------------------
# Conteúdo do content.xml
# ---------------------------------------------------------------------------


def _content_xml(odt_path: Path) -> str:
    with zipfile.ZipFile(odt_path) as zf:
        return zf.read("content.xml").decode("utf-8")


def test_content_xml_preserva_texto_e_placeholders(tmp_path: Path) -> None:
    destino = tmp_path / "minuta.odt"
    export_inventario_odt(_minuta_markdown_exemplo(), destino)
    content = _content_xml(destino)
    for esperado in [
        "MINUTA-BASE",
        "[QUALIFICAÇÃO DO AUTOR DA HERANÇA]",
        "[QUALIFICAÇÃO DO HERDEIRO_1]",
        "CAMPO DE REVISÃO HUMANA",
    ]:
        assert esperado in content, f"trecho ausente no content.xml: {esperado!r}"


def test_content_xml_usa_estrutura_opendocument(tmp_path: Path) -> None:
    destino = tmp_path / "minuta.odt"
    export_inventario_odt(_minuta_markdown_exemplo(), destino)
    content = _content_xml(destino)
    assert content.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert "<office:document-content" in content
    assert "<office:text>" in content
    # o título do documento (não numerado) segue como cabeçalho ODF;
    # as cláusulas numeradas, não — ver testes de cláusulas corridas abaixo
    assert 'text:outline-level="1"' in content


def test_content_xml_nao_contem_pii(tmp_path: Path) -> None:
    destino = tmp_path / "minuta.odt"
    export_inventario_odt(_minuta_markdown_exemplo(), destino)
    content = _content_xml(destino)
    for nome, padrao in _PII_PATTERNS:
        match = padrao.search(content)
        assert match is None, f"PII suspeita ({nome}) no content.xml: {match.group()!r}"


def test_markdown_to_content_xml_escapa_caracteres_especiais() -> None:
    xml = markdown_to_content_xml("# Título com & e <tag> proibida")
    assert "&amp;" in xml
    assert "&lt;tag&gt;" in xml
    assert "<tag>" not in xml.replace("&lt;tag&gt;", "")


# ---------------------------------------------------------------------------
# Padrão cartorário — cláusulas numeradas em texto corrido (NOTAS-INVENTARIO-5B)
# ---------------------------------------------------------------------------

# Nomes de estilo ODF do padrão cartorário — pinados aqui como contrato:
# qualquer renomeação no exporter precisa ser revista junto com estes testes.
ODT_BODY_STYLE = "CartorioBody"
ODT_CLAUSE_LABEL_STYLE = "ClauseLabel"

# Cláusula numerada: rótulo iniciado por "1.", "1.1.", "10.2." etc.
_CLAUSULA_NUMERADA = re.compile(r"^\d+(?:\.\d+)*\.\s")
# Captura o texto de cada <text:h …>…</text:h> do content.xml.
_HEADING_RE = re.compile(r"<text:h\b[^>]*>(.*?)</text:h>", re.DOTALL)


def _styles_xml(odt_path: Path) -> str:
    with zipfile.ZipFile(odt_path) as zf:
        return zf.read("styles.xml").decode("utf-8")


def _headings(content: str) -> list[str]:
    return _HEADING_RE.findall(content)


def test_clausula_numerada_nao_vira_heading() -> None:
    """`## 2. …` é cláusula numerada — vira parágrafo de corpo, nunca heading."""

    xml = markdown_to_content_xml("## 2. DO AUTOR DA HERANÇA\n\nNome do autor.\n")
    assert "<text:h" not in xml, "cláusula numerada não pode virar cabeçalho ODF"
    assert f'<text:p text:style-name="{ODT_BODY_STYLE}">' in xml
    assert "2. DO AUTOR DA HERANÇA" in xml


def test_clausulas_numeradas_da_minuta_nao_sao_headings(tmp_path: Path) -> None:
    """Nenhum <text:h> do content.xml pode conter uma cláusula numerada."""

    destino = tmp_path / "minuta.odt"
    export_inventario_odt(_minuta_markdown_exemplo(), destino)
    content = _content_xml(destino)
    for heading in _headings(content):
        assert not _CLAUSULA_NUMERADA.match(heading.strip()), (
            f"cláusula numerada renderizada como cabeçalho ODF: {heading!r}"
        )
    # cláusulas conhecidas continuam presentes — apenas não como heading
    for rotulo in ["1. DA QUALIFICAÇÃO", "2. DO AUTOR", "3. DO FALECIMENTO"]:
        assert rotulo in content, f"cláusula ausente no content.xml: {rotulo!r}"


def test_clausula_numerada_e_paragrafo_de_corpo_com_rotulo_destacado(
    tmp_path: Path,
) -> None:
    """A cláusula é um parágrafo de corpo; o rótulo é um span ClauseLabel."""

    destino = tmp_path / "minuta.odt"
    export_inventario_odt(_minuta_markdown_exemplo(), destino)
    content = _content_xml(destino)
    assert (
        f'<text:p text:style-name="{ODT_BODY_STYLE}">'
        f'<text:span text:style-name="{ODT_CLAUSE_LABEL_STYLE}">'
        "1. DA QUALIFICAÇÃO DAS PARTES:</text:span></text:p>"
    ) in content
    # subcláusulas (### N.N.) recebem o mesmo tratamento
    assert (
        f'<text:span text:style-name="{ODT_CLAUSE_LABEL_STYLE}">10.1. DA MEAÇÃO:</text:span>'
    ) in content


def test_rotulo_da_clausula_tem_estilo_negrito_e_sublinhado(tmp_path: Path) -> None:
    """O estilo ClauseLabel define negrito e sublinhado ODF."""

    destino = tmp_path / "minuta.odt"
    export_inventario_odt(_minuta_markdown_exemplo(), destino)
    styles = _styles_xml(destino)
    assert f'style:name="{ODT_CLAUSE_LABEL_STYLE}"' in styles
    assert 'style:family="text"' in styles
    assert 'fo:font-weight="bold"' in styles
    assert 'style:text-underline-style="solid"' in styles


def test_estilo_de_corpo_nao_tem_aparencia_de_titulo(tmp_path: Path) -> None:
    """CartorioBody é parágrafo de corpo — sem outline-level / heading."""

    destino = tmp_path / "minuta.odt"
    export_inventario_odt(_minuta_markdown_exemplo(), destino)
    styles = _styles_xml(destino)
    assert f'style:name="{ODT_BODY_STYLE}"' in styles
    assert 'style:family="paragraph"' in styles
    assert "outline-level" not in styles, "estilo de corpo não pode ter outline-level"
    assert "text:h" not in styles, "estilo de corpo não pode herdar de heading"


def test_conteudo_da_clausula_permanece_texto_normal(tmp_path: Path) -> None:
    """O texto após o rótulo não herda negrito/sublinhado: ClauseLabel só
    aparece dentro do <text:span> do rótulo, nunca em um parágrafo inteiro."""

    destino = tmp_path / "minuta.odt"
    export_inventario_odt(_minuta_markdown_exemplo(), destino)
    content = _content_xml(destino)
    usos = content.count(f'text:style-name="{ODT_CLAUSE_LABEL_STYLE}"')
    spans = content.count(f'<text:span text:style-name="{ODT_CLAUSE_LABEL_STYLE}">')
    assert usos == spans, "ClauseLabel deve ser usado apenas em spans de rótulo"
    assert f'<text:p text:style-name="{ODT_CLAUSE_LABEL_STYLE}"' not in content
    # parágrafos de conteúdo continuam no estilo de corpo padrão
    assert '<text:p text:style-name="Standard">' in content


# ---------------------------------------------------------------------------
# Determinismo
# ---------------------------------------------------------------------------


def test_exportacao_e_deterministica(tmp_path: Path) -> None:
    """Gerar o mesmo Markdown duas vezes produz bytes idênticos.

    Datas fixas no ZIP e ausência de timestamps no meta.xml garantem isso.
    """

    markdown = _minuta_markdown_exemplo()
    a = tmp_path / "a.odt"
    b = tmp_path / "b.odt"
    export_inventario_odt(markdown, a)
    export_inventario_odt(markdown, b)
    assert a.read_bytes() == b.read_bytes()


# ---------------------------------------------------------------------------
# CLI: --export-odt
# ---------------------------------------------------------------------------


def test_cli_export_odt_gera_md_e_odt(tmp_path: Path) -> None:
    out = tmp_path / "saida"
    proc = _run_cli(
        "--input",
        str(EXAMPLES / "inventario_simples.yaml"),
        "--output-dir",
        str(out),
        "--export-odt",
    )
    assert proc.returncode == 0, proc.stderr
    assert (out / "inventario_minuta.md").exists()
    assert (out / "inventario_minuta.odt").exists()
    assert (out / "inventario_validacao.json").exists()
    assert (out / "inventario_resumo.md").exists()


def test_cli_export_odt_nao_exige_render_minuta(tmp_path: Path) -> None:
    """--export-odt sozinho já implica a renderização da minuta Markdown."""

    out = tmp_path / "saida"
    proc = _run_cli(
        "--input",
        str(EXAMPLES / "inventario_sem_meeiro.yaml"),
        "--output-dir",
        str(out),
        "--export-odt",
    )
    assert proc.returncode == 0, proc.stderr
    assert (out / "inventario_minuta.md").exists()
    assert (out / "inventario_minuta.odt").exists()


def test_cli_sem_export_odt_nao_gera_odt(tmp_path: Path) -> None:
    out = tmp_path / "saida"
    proc = _run_cli(
        "--input",
        str(EXAMPLES / "inventario_simples.yaml"),
        "--output-dir",
        str(out),
        "--render-minuta",
    )
    assert proc.returncode == 0, proc.stderr
    assert (out / "inventario_minuta.md").exists()
    assert not (out / "inventario_minuta.odt").exists(), (
        "ODT gerado sem --export-odt — contrato da CLI quebrado"
    )


def test_cli_validacao_falha_nao_gera_odt(tmp_path: Path) -> None:
    """Validação falhando: exit 1, sem Markdown e sem ODT."""

    entrada = tmp_path / "inv_invalido.yaml"
    entrada.write_text(
        "tipo_ato: inventario_extrajudicial\n"
        "possui_meeiro: false\n"
        'percentual_meacao: "0"\n'
        'patrimonio_total: "1000.00"\n'
        "herdeiros:\n"
        "  - id: HERDEIRO_1\n"
        '    percentual_heranca: "40"\n'  # soma 80, inválido
        "  - id: HERDEIRO_2\n"
        '    percentual_heranca: "40"\n'
        "bens:\n"
        "  - id: SALDO_1\n"
        "    tipo: dinheiro\n"
        "    descricao_generica: 'Saldo em [BANCO]'\n"
        '    valor: "1000.00"\n'
        "    distribuicao:\n"
        "      - beneficiario: HERDEIRO_1\n"
        '        percentual: "50"\n'
        "      - beneficiario: HERDEIRO_2\n"
        '        percentual: "50"\n',
        encoding="utf-8",
    )
    out = tmp_path / "saida_invalida"
    proc = _run_cli(
        "--input",
        str(entrada),
        "--output-dir",
        str(out),
        "--export-odt",
    )
    assert proc.returncode == 1, (
        f"esperado exit 1 por validação falhar; veio {proc.returncode}: {proc.stderr!r}"
    )
    assert (out / "inventario_validacao.json").exists()
    assert not (out / "inventario_minuta.md").exists()
    assert not (out / "inventario_minuta.odt").exists(), (
        "ODT gerado apesar de validação falhar — quebra o contrato da CLI"
    )


def test_cli_export_odt_respeita_protecao_de_output_dir() -> None:
    """--output-dir interno bloqueado continua barrado mesmo com --export-odt."""

    bloqueado = PROJECT_ROOT / "app" / "_saida_odt_bloqueada"
    proc = _run_cli(
        "--input",
        str(EXAMPLES / "inventario_simples.yaml"),
        "--output-dir",
        str(bloqueado),
        "--export-odt",
    )
    assert proc.returncode == 2, proc.stderr
    assert "app/" in proc.stderr
    assert not bloqueado.exists(), "CLI não deveria ter criado o diretório bloqueado."
