"""Exportador ODT da minuta-base de inventário.

A **fonte canônica** da minuta continua sendo o Markdown produzido por
:func:`app.modules.notas.inventarios.application.renderer.render_minuta_markdown`.
O ``.odt`` é um **artefato derivado**, gerado a partir desse Markdown para
permitir conferência prática no LibreOffice Writer — ele nunca volta para o
pipeline como fonte de verdade.

Implementação propositalmente mínima e sem dependência externa: um arquivo
OpenDocument Text é apenas um ZIP com uma estrutura conhecida, montado aqui
com a biblioteca padrão (``zipfile`` + ``xml.sax.saxutils``).

Estrutura do pacote ODF gerada:

- ``mimetype``               — primeiro item do ZIP, **sem compressão**;
- ``content.xml``            — o texto da minuta;
- ``styles.xml``             — estrutura de estilos mínima;
- ``meta.xml``               — metadados (sem datas, para manter determinismo);
- ``META-INF/manifest.xml``  — manifesto do pacote.

O conversor Markdown→ODT cobre apenas o subconjunto que a minuta usa
(títulos, parágrafos, citações, listas, alíneas, tabela do campo de revisão
humana). Não é um conversor Markdown completo — *conteúdo preservado e
arquivo editável* tem prioridade sobre formatação perfeita.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ODT_MIMETYPE = "application/vnd.oasis.opendocument.text"

# Data fixa para todas as entradas do ZIP. ODF/ZIP não aceita anos < 1980;
# fixar a data elimina o timestamp variável e torna o .odt determinístico.
_FIXED_DATE = (1980, 1, 1, 0, 0, 0)

_NS_OFFICE = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
_NS_TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
_NS_MANIFEST = "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
_NS_META = "urn:oasis:names:tc:opendocument:xmlns:meta:1.0"

_SEPARADORA_TABELA = re.compile(r"^:?-+:?$")
_INLINE_LIMPAR = ("**", "`")


def _limpar_inline(texto: str) -> str:
    """Remove marcadores de ênfase Markdown (``**``, crase), preservando o
    conteúdo — em especial os placeholders entre colchetes."""

    for marcador in _INLINE_LIMPAR:
        texto = texto.replace(marcador, "")
    return texto


def _p(texto: str) -> str:
    return f'<text:p text:style-name="Standard">{escape(_limpar_inline(texto))}</text:p>'


def _p_vazio() -> str:
    return '<text:p text:style-name="Standard"/>'


def _h(texto: str, nivel: int) -> str:
    conteudo = escape(_limpar_inline(texto))
    return f'<text:h text:outline-level="{nivel}">{conteudo}</text:h>'


def _linha_de_tabela(celulas: list[str]) -> str:
    partes = [escape(_limpar_inline(c.strip())) for c in celulas]
    return f'<text:p text:style-name="Standard">{"<text:tab/>".join(partes)}</text:p>'


def _markdown_para_blocos(markdown: str) -> list[str]:
    """Converte o Markdown da minuta em uma lista de elementos ODF (strings XML)."""

    blocos: list[str] = []
    for linha_bruta in markdown.splitlines():
        linha = linha_bruta.rstrip("\r")
        despojada = linha.strip()

        if not despojada:
            continue

        if despojada == "---":
            blocos.append(_p_vazio())
            continue

        if linha.startswith("### "):
            blocos.append(_h(linha[4:], 3))
            continue
        if linha.startswith("## "):
            blocos.append(_h(linha[3:], 2))
            continue
        if linha.startswith("# "):
            blocos.append(_h(linha[2:], 1))
            continue

        if despojada.startswith("|") and despojada.endswith("|"):
            celulas = [c for c in despojada.strip("|").split("|")]
            if all(_SEPARADORA_TABELA.match(c.strip()) for c in celulas):
                continue
            blocos.append(_linha_de_tabela(celulas))
            continue

        if despojada.startswith(">"):
            blocos.append(_p(despojada[1:].strip()))
            continue

        if despojada.startswith("- "):
            blocos.append(_p(despojada[2:].strip()))
            continue

        blocos.append(_p(despojada))

    return blocos


def markdown_to_content_xml(markdown: str) -> str:
    """Monta o ``content.xml`` completo a partir do Markdown da minuta."""

    corpo = "".join(_markdown_para_blocos(markdown))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<office:document-content xmlns:office="{_NS_OFFICE}" '
        f'xmlns:text="{_NS_TEXT}" office:version="1.2">'
        "<office:body><office:text>"
        f"{corpo}"
        "</office:text></office:body>"
        "</office:document-content>"
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<office:document-styles xmlns:office="{_NS_OFFICE}" '
        f'xmlns:text="{_NS_TEXT}" office:version="1.2">'
        "<office:styles/>"
        "<office:automatic-styles/>"
        "<office:master-styles/>"
        "</office:document-styles>"
    )


def _meta_xml() -> str:
    # Sem datas: o exportador é determinístico de propósito.
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<office:document-meta xmlns:office="{_NS_OFFICE}" '
        f'xmlns:meta="{_NS_META}" office:version="1.2">'
        "<office:meta>"
        "<meta:generator>Cartorio System - inventarios ODT exporter</meta:generator>"
        "</office:meta>"
        "</office:document-meta>"
    )


def _manifest_xml() -> str:
    entradas = [
        ("/", ODT_MIMETYPE),
        ("content.xml", "text/xml"),
        ("styles.xml", "text/xml"),
        ("meta.xml", "text/xml"),
    ]
    linhas = "".join(
        f'<manifest:file-entry manifest:full-path="{caminho}" manifest:media-type="{media}"/>'
        for caminho, media in entradas
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<manifest:manifest xmlns:manifest="{_NS_MANIFEST}" manifest:version="1.2">'
        f"{linhas}"
        "</manifest:manifest>"
    )


def export_inventario_odt(markdown: str, destino: str | Path) -> Path:
    """Grava ``destino`` como um pacote OpenDocument Text derivado de ``markdown``.

    O ``mimetype`` é gravado como primeira entrada do ZIP e sem compressão,
    conforme exige a especificação ODF. As demais entradas usam DEFLATE com
    data fixa, tornando o arquivo byte-determinístico para a mesma entrada.
    """

    caminho = Path(destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    content_xml = markdown_to_content_xml(markdown)

    with zipfile.ZipFile(caminho, "w") as zf:
        mimetype_info = zipfile.ZipInfo("mimetype", date_time=_FIXED_DATE)
        mimetype_info.compress_type = zipfile.ZIP_STORED
        zf.writestr(mimetype_info, ODT_MIMETYPE)

        demais: list[tuple[str, str]] = [
            ("content.xml", content_xml),
            ("styles.xml", _styles_xml()),
            ("meta.xml", _meta_xml()),
            ("META-INF/manifest.xml", _manifest_xml()),
        ]
        for nome, conteudo in demais:
            info = zipfile.ZipInfo(nome, date_time=_FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, conteudo)

    return caminho


__all__ = ["ODT_MIMETYPE", "export_inventario_odt", "markdown_to_content_xml"]
