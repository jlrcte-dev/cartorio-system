"""XLSX sintético do demonstrativo diário de caixa — layout do modelo, dados 100% fictícios.

Posições espelham o modelo calibrado (rótulos estruturais apenas): dinheiro em B–D,
verificação em F–H, PIX em B–C e protesto em E–J a partir da mesma linha, maquininha
abaixo do total do PIX. ``pix_extra`` insere linhas no PIX e desloca a maquininha.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from datetime import date

NS = (
    'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
)
PKG_RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
STYLES = (
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<cellXfs><xf numFmtId="0"/><xf numFmtId="14"/></cellXfs></styleSheet>'
)
PEOPLE = ["Fulano Exemplo da Silva", "Beltrana Ficticia Souza"]
PROTOCOL = "PROTO-FICTICIO-98765"
DESCRIPTIONS = [
    "Recebimento ato exemplo",
    "Pagamento fornecedor ficticio",
    "Recebimento ficticio dois",
]


@dataclass(frozen=True)
class N:
    """Número como gravado no XML (texto exato, sem float)."""

    raw: str


@dataclass(frozen=True)
class F:
    """Fórmula com resultado gravado (``cache``), sem resultado (None) ou erro."""

    text: str
    cache: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class D:
    """Data serial com estilo de data."""

    when: date


@dataclass(frozen=True)
class B:
    value: bool


def serial(when: date) -> str:
    return str((when - date(1899, 12, 30)).days)


def col(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _cell(ref: str, v: object) -> str:
    if isinstance(v, N):
        return f'<c r="{ref}"><v>{v.raw}</v></c>'
    if isinstance(v, D):
        return f'<c r="{ref}" s="1"><v>{serial(v.when)}</v></c>'
    if isinstance(v, B):
        return f'<c r="{ref}" t="b"><v>{int(v.value)}</v></c>'
    if isinstance(v, F):
        if v.error:
            return f'<c r="{ref}" t="e"><f>{_esc(v.text)}</f><v>{v.error}</v></c>'
        cache = f"<v>{v.cache}</v>" if v.cache is not None else ""
        return f'<c r="{ref}"><f>{_esc(v.text)}</f>{cache}</c>'
    return f'<c r="{ref}" t="inlineStr"><is><t>{_esc(str(v))}</t></is></c>'


def day(
    name: str,
    *,
    body: date | None = date(2026, 10, 5),
    caixa_inicial: object = N("100"),
    lanc: list[tuple[str, object, object]] | None = None,
    totais: tuple[object, object] = (F("SUM(C7:C21)", "150.25"), F("SUM(D7:D21)", "30")),
    malote: object = N("20"),
    teorico: object = F("(C4+C22-D22-C23)", "200.25"),
    conferido: object = N("200.25"),
    diferenca: object = F("C26-C24", "0"),
    verif: list[tuple[object, object, object]] | None = None,
    pix: list[tuple[int, str, object]] | None = None,
    pix_extra: int = 0,
    pix_total: object | None = None,
    protesto: list[tuple[str, object, object]] | None = None,
    protesto_totais: tuple[object, object, object] | None = None,
    maq: list[tuple[str, object, object]] | None = None,
    maq_totais: tuple[object, object] | None = None,
    set_cells: dict[tuple[int, int], object] | None = None,
    drop: set[tuple[int, int]] | None = None,
    merges: list[str] | None = None,
) -> dict:
    """Uma aba do modelo. ``pix`` usa linhas ABSOLUTAS (o modelo real começa o total do PIX
    na terceira linha do bloco)."""
    cells: dict[tuple[int, int], object] = {}
    lanc = (
        [
            (DESCRIPTIONS[0], N("50.25"), None),
            (DESCRIPTIONS[1], None, N("30")),
            (DESCRIPTIONS[2], N("100"), None),
        ]
        if lanc is None
        else lanc
    )
    verif = [(N("0.4166"), N("200.25"), PEOPLE[0])] if verif is None else verif
    rows = 9 + pix_extra
    total_row = 31 + rows
    mh = total_row + 4  # cabeçalho da maquininha
    pix = (
        [(33, "PIX recebido ficticio", N("80")), (34, "TED ficticia", N("20"))]
        if pix is None
        else pix
    )
    pix_total = F(f"SUM(C33:C{total_row - 1})", "100") if pix_total is None else pix_total
    protesto = [(f"Protocolo nº {PROTOCOL}", N("500"), N("450"))] if protesto is None else protesto
    protesto_totais = (
        (
            F(f"SUM(H31:H{total_row - 1})", "500"),
            F(f"SUM(I31:I{total_row - 1})", "450"),
            F(f"SUM(J31:J{total_row - 1})", "50"),
        )
        if protesto_totais is None
        else protesto_totais
    )
    maq = [("Pagamento cartao ficticio", N("97.5"), N("100"))] if maq is None else maq
    maq_totais = (
        (F(f"SUM(C{mh + 1}:C{mh + 5})", "97.5"), F(f"SUM(D{mh + 1}:D{mh + 5})", "100"))
        if maq_totais is None
        else maq_totais
    )

    cells[(2, 2)] = "Movimentação do caixa dia"
    if body is not None:
        cells[(2, 3)] = D(body)
    cells[(2, 6)] = "Verificação do Caixa"
    cells[(3, 6)], cells[(3, 7)], cells[(3, 8)] = "Horário", "Valor", "Conferido"
    for i, (h, v, who) in enumerate(verif):
        for c, x in ((6, h), (7, v), (8, who)):
            if x is not None:
                cells[(4 + i, c)] = x
    cells[(4, 2)], cells[(4, 3)] = "Caixa inicial", caixa_inicial
    cells[(6, 2)], cells[(6, 3)] = "Descrição", "Valor total"
    cells[(7, 3)], cells[(7, 4)] = "Entrada", "Saída"
    for i, (desc, e, s) in enumerate(lanc):
        r = 8 + i
        cells[(r, 2)] = desc
        if e is not None:
            cells[(r, 3)] = e
        if s is not None:
            cells[(r, 4)] = s
    cells[(22, 3)], cells[(22, 4)] = totais
    cells[(23, 2)], cells[(23, 3)] = "Retirada para Malote", malote
    cells[(24, 2)], cells[(24, 3)] = "Saldo (Caixa Inicial + Entrada – Saída)", teorico
    cells[(26, 2)] = "Saldo do dia EM DINHEIRO no Caixa"
    if conferido is not None:
        cells[(26, 3)] = conferido
    cells[(28, 2)], cells[(28, 3)] = "Diferença", diferenca
    cells[(30, 2)], cells[(30, 3)] = "Transferências / PIX", "Valor total"
    cells[(30, 5)] = "Protesto - bloco ficticio"
    cells[(30, 8)], cells[(30, 9)], cells[(30, 10)] = "Valor total", "Repasse", "Emolumentos"
    for r, desc, v in pix:
        cells[(r, 2)], cells[(r, 3)] = desc, v
    for i, (desc, rec, rep) in enumerate(protesto):
        r = 31 + i
        cells[(r, 5)] = desc
        if rec is not None:
            cells[(r, 8)] = rec
        if rep is not None:
            cells[(r, 9)] = rep
        cells[(r, 10)] = F(f"H{r}-I{r}", "50")
    cells[(total_row, 2)], cells[(total_row, 3)] = "Total", pix_total
    cells[(total_row, 5)] = "Total"
    cells[(total_row, 8)], cells[(total_row, 9)], cells[(total_row, 10)] = protesto_totais
    cells[(mh, 2)] = "Pago pela maquininha"
    cells[(mh, 3)], cells[(mh, 4)], cells[(mh, 5)] = "Valor a receber", "Valor cobrado", "Tipo"
    for i, (desc, rec, cob) in enumerate(maq):
        r = mh + 1 + i
        cells[(r, 2)] = desc
        if rec is not None:
            cells[(r, 3)] = rec
        if cob is not None:
            cells[(r, 4)] = cob
    cells[(mh + 6, 2)] = "Total em transferências"
    cells[(mh + 6, 3)], cells[(mh + 6, 4)] = maq_totais
    for pos in drop or ():
        cells.pop(pos, None)
    cells.update(set_cells or {})
    base_merges = [
        "C2:D2",
        "F2:H2",
        "C4:D4",
        "B6:B7",
        "C6:D6",
        "C23:D23",
        "C24:D24",
        "E30:G30",
        f"E{total_row}:G{total_row}",
    ]
    return {
        "name": name,
        "cells": cells,
        "merges": base_merges if merges is None else merges,
        "total_row": total_row,
        "maq_header": mh,
    }


def xlsx_bytes(sheets: list[dict]) -> bytes:
    m: dict[str, str] = {"[Content_Types].xml": "<Types/>", "xl/styles.xml": STYLES}
    wb_sheets, wb_rels = [], []
    for i, sh in enumerate(sheets, 1):
        wb_sheets.append(f'<sheet name="{_esc(sh["name"])}" sheetId="{i}" r:id="rId{i}"/>')
        wb_rels.append(
            f'<Relationship Id="rId{i}" Type="x/worksheet" Target="worksheets/sheet{i}.xml"/>'
        )
        by_row: dict[int, list[tuple[int, object]]] = {}
        for (r, c), v in sh["cells"].items():
            by_row.setdefault(r, []).append((c, v))
        xml_rows = "".join(
            f'<row r="{r}">'
            + "".join(_cell(f"{col(c)}{r}", v) for c, v in sorted(items))
            + "</row>"
            for r, items in sorted(by_row.items())
        )
        merges = "".join(f'<mergeCell ref="{ref}"/>' for ref in sh["merges"])
        mc = (
            f'<mergeCells count="{len(sh["merges"])}">{merges}</mergeCells>' if sh["merges"] else ""
        )
        m[f"xl/worksheets/sheet{i}.xml"] = (
            f"<worksheet {NS}><sheetData>{xml_rows}</sheetData>{mc}</worksheet>"
        )
    m["xl/workbook.xml"] = f"<workbook {NS}><sheets>{''.join(wb_sheets)}</sheets></workbook>"
    m["xl/_rels/workbook.xml.rels"] = (
        f'<Relationships xmlns="{PKG_RELS}">{"".join(wb_rels)}</Relationships>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, xml in m.items():
            z.writestr(name, xml)
    return buf.getvalue()
