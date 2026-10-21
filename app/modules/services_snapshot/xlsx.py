"""Leitura mínima de XLSX exportado: abas, tabelas declaradas, células e linhas ocultas.

Só lê o pacote (zip + XML via defusedxml): não salva, não recalcula fórmulas, não segue
links nem executa macros. Do estilo da célula interessa só se o formato numérico é de
data; do workbook, só o sistema de datas (1900 ou 1904). Textos lidos aqui são dados
privados da planilha e nunca saem deste processo, exceto como contagens no relatório.
"""

from __future__ import annotations

import io
import posixpath
import re
import zipfile
from dataclasses import dataclass, field
from xml.etree.ElementTree import Element

M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"

_REF_RE = re.compile(r"^\$?([A-Z]{1,3})\$?(\d+)$")
# Formatos internos de data do OOXML (ECMA-376, 18.8.30); 18–21 e 45–47 são só hora.
_DATE_BUILTIN = frozenset({14, 15, 16, 17, 22, *range(27, 37), *range(50, 59)})
# Literais entre aspas, escapes, seções entre colchetes (cor, locale, tempo decorrido) e
# preenchimentos não definem o tipo do formato.
_FMT_NOISE_RE = re.compile(r'"[^"]*"|\\.|\[[^\]]*\]|[_*].')


class XlsxError(Exception):
    """Pacote ou XML fora do formato esperado. Sem texto da planilha na mensagem."""


def fromstring(data: bytes) -> Element:
    # Import tardio: show e a importação do pacote não dependem do defusedxml.
    from defusedxml.ElementTree import fromstring as safe_fromstring

    return safe_fromstring(data)


def parse_ref(ref: str) -> tuple[int, int]:
    m = _REF_RE.match(ref)
    if not m:
        raise XlsxError("referência de célula não suportada")
    col = 0
    for ch in m.group(1):
        col = col * 26 + ord(ch) - 64
    return int(m.group(2)), col


def parse_range(ref: str) -> tuple[int, int, int, int]:
    a, _, b = ref.partition(":")
    r1, c1 = parse_ref(a)
    r2, c2 = parse_ref(b) if b else (r1, c1)
    return r1, c1, r2, c2


@dataclass
class Cell:
    literal: tuple[str, str] | None = None  # (tipo, valor) de célula sem fórmula
    formula: str | None = None  # texto da fórmula ("" em fórmula compartilhada filha)
    cache: tuple[str, str] | None = None  # resultado gravado; None = ausente
    date_format: bool = False  # estilo declara formato numérico de data

    @property
    def value(self) -> tuple[str, str] | None:
        return self.literal if self.formula is None else self.cache

    def filled(self) -> bool:
        val = self.value
        if val is None:
            return self.formula is not None
        return val[0] != "texto" or bool(val[1].strip())

    def text(self) -> str | None:
        return self.literal[1] if self.literal and self.literal[0] == "texto" else None


@dataclass
class Table:
    ref: str
    header_rows: int
    totals_rows: int
    columns: list[str]


@dataclass
class Sheet:
    name: str
    cells: dict[tuple[int, int], Cell]
    hidden_rows: set[int]
    tables: list[Table] = field(default_factory=list)
    date1904: bool = False  # sistema de datas do workbook

    def rows(self) -> dict[int, dict[int, Cell]]:
        out: dict[int, dict[int, Cell]] = {}
        for (r, c), cell in self.cells.items():
            out.setdefault(r, {})[c] = cell
        return out


def _rels(z: zipfile.ZipFile, part: str) -> dict[str, str]:
    base = posixpath.dirname(part)
    path = posixpath.join(base, "_rels", posixpath.basename(part) + ".rels")
    if path not in z.namelist():
        return {}
    out = {}
    for rel in fromstring(z.read(path)):
        target = rel.get("Target", "")
        out[rel.get("Id", "")] = (
            target.lstrip("/")
            if target.startswith("/")
            else posixpath.normpath(posixpath.join(base, target))
        )
    return out


def _text_of(node: Element) -> str:
    parts = []
    for child in node:
        if child.tag == M + "t":
            parts.append(child.text or "")
        elif child.tag == M + "r":
            t = child.find(M + "t")
            parts.append((t.text or "") if t is not None else "")
    return "".join(parts)


def _value(c: Element, sst: list[str]) -> tuple[str, str] | None:
    inline = c.find(M + "is")
    if inline is not None:
        return ("texto", _text_of(inline))
    v = c.find(M + "v")
    if v is None:
        return None
    raw = v.text or ""
    t = c.get("t", "n")
    if t == "s":
        idx = int(raw) if raw.isdigit() else -1
        if not 0 <= idx < len(sst):
            raise XlsxError("índice de shared string inválido")
        return ("texto", sst[idx])
    return {"str": ("texto", raw), "b": ("booleano", raw), "e": ("erro", raw)}.get(
        t, ("numero", raw)
    )


def is_date_format(code: str) -> bool:
    section = _FMT_NOISE_RE.sub("", code).split(";")[0].lower()
    return "d" in section or "y" in section


def _date_styles(z: zipfile.ZipFile, names: set[str]) -> frozenset[int]:
    """Índices de ``cellXfs`` cujo formato numérico é de data."""
    if "xl/styles.xml" not in names:
        return frozenset()
    root = fromstring(z.read("xl/styles.xml"))
    custom = {}
    fmts = root.find(M + "numFmts")
    for fmt in fmts if fmts is not None else []:
        custom[int(fmt.get("numFmtId", "-1"))] = fmt.get("formatCode", "")
    out = set()
    xfs = root.find(M + "cellXfs")
    for i, xf in enumerate(xfs if xfs is not None else []):
        fmt_id = int(xf.get("numFmtId", "0"))
        code = custom.get(fmt_id)
        if is_date_format(code) if code is not None else fmt_id in _DATE_BUILTIN:
            out.add(i)
    return frozenset(out)


def _sheet(
    z: zipfile.ZipFile,
    part: str,
    name: str,
    sst: list[str],
    date_styles: frozenset[int],
    date1904: bool,
) -> Sheet:
    root = fromstring(z.read(part))
    cells: dict[tuple[int, int], Cell] = {}
    hidden: set[int] = set()
    data = root.find(M + "sheetData")
    last_row = 0
    for row in data if data is not None else []:
        r = int(row.get("r") or last_row + 1)
        last_row = r
        if row.get("hidden") in ("1", "true"):
            hidden.add(r)
        last_col = 0
        for c in row:
            ref = c.get("r")
            rr, col = parse_ref(ref) if ref else (r, last_col + 1)
            last_col = col
            f = c.find(M + "f")
            value = _value(c, sst)
            cell = Cell(formula=f.text or "", cache=value) if f is not None else Cell(literal=value)
            cell.date_format = int(c.get("s") or 0) in date_styles
            if cell.literal is not None or cell.formula is not None:
                cells[(rr, col)] = cell
    rels = _rels(z, part)
    tables = []
    parts = root.find(M + "tableParts")
    for tp in parts if parts is not None else []:
        tr = fromstring(z.read(rels[tp.get(R_ID, "")]))
        tables.append(
            Table(
                ref=tr.get("ref", ""),
                header_rows=int(tr.get("headerRowCount", "1")),
                totals_rows=int(tr.get("totalsRowCount", "0")),
                columns=[tc.get("name", "") for tc in tr.iter(M + "tableColumn")],
            )
        )
    return Sheet(name=name, cells=cells, hidden_rows=hidden, tables=tables, date1904=date1904)


def parse_workbook(content: bytes) -> list[Sheet]:
    """Abas na ordem do arquivo. Qualquer desvio de formato vira XlsxError."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            names = set(z.namelist())
            sst = []
            if "xl/sharedStrings.xml" in names:
                sst = [_text_of(si) for si in fromstring(z.read("xl/sharedStrings.xml"))]
            date_styles = _date_styles(z, names)
            wb = fromstring(z.read("xl/workbook.xml"))
            pr = wb.find(M + "workbookPr")
            date1904 = pr is not None and pr.get("date1904") in ("1", "true")
            rels = _rels(z, "xl/workbook.xml")
            sheets_el = wb.find(M + "sheets")
            return [
                _sheet(z, rels[s.get(R_ID, "")], s.get("name", ""), sst, date_styles, date1904)
                for s in (sheets_el if sheets_el is not None else [])
            ]
    except XlsxError:
        raise
    except Exception:  # zip/XML corrompido, parte ausente, entidade recusada pelo defusedxml
        raise XlsxError("pacote XLSX ilegível ou fora do formato esperado") from None
