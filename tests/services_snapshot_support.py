"""XLSX sintético mínimo para os testes do retrato de serviços — só dados fictícios."""

from __future__ import annotations

import io
import zipfile

NS = (
    'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
)
PKG_RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
COLS = "ABCDEFGHIJKL"
STD = [
    "Tarefa",
    "Prioridade",
    "Solicitante",
    "Status",
    "Data de início",
    "Data de término",
    "Responsável",
    "Observações",
]
PEOPLE = ["Fulano Exemplo da Silva", "Beltrana Ficticia Souza", "Sicrano Inventado"]


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def row(
    status: str | None,
    *,
    tarefa: str | None = "Escritura de compra",
    obs: str | None = None,
    inicio: object = "45900",
    termino: object = None,
) -> list:
    return [tarefa, "Alta", PEOPLE[0], status, inicio, termino, PEOPLE[1], obs]


class Serial:
    """Número serial de data numa célula com estilo de data (``style`` = índice em cellXfs)."""

    def __init__(self, value: float | str, style: int = 1) -> None:
        self.value, self.style = str(value), style


class Number:
    """Número sem formato de data (estilo 0, General)."""

    def __init__(self, value: float | str) -> None:
        self.value = str(value)


# cellXfs: 0 General · 1 interno 14 (data) · 2 personalizado dd/mm/yyyy · 3 personalizado
# "0.00" · 4 personalizado [h]:mm (tempo decorrido, não é data)
STYLES = (
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<numFmts count="3"><numFmt numFmtId="164" formatCode="dd/mm/yyyy"/>'
    '<numFmt numFmtId="165" formatCode="0.00"/><numFmt numFmtId="166" formatCode="[h]:mm"/>'
    "</numFmts><cellXfs>"
    '<xf numFmtId="0"/><xf numFmtId="14"/><xf numFmtId="164"/><xf numFmtId="165"/>'
    '<xf numFmtId="166"/></cellXfs></styleSheet>'
)


def _cell(ref: str, v: object) -> str:
    if isinstance(v, Serial):
        return f'<c r="{ref}" s="{v.style}"><v>{v.value}</v></c>'
    if isinstance(v, Number):
        return f'<c r="{ref}"><v>{v.value}</v></c>'
    if isinstance(v, bool):
        return f'<c r="{ref}" t="b"><v>{int(v)}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t>{_esc(str(v))}</t></is></c>'


def xlsx_bytes(sheets: list[dict], *, date1904: bool = False) -> bytes:
    """sheets: [{name, headers, rows, hidden: set[índice de linha de dados], styled_empty_rows}]"""
    m: dict[str, str] = {"[Content_Types].xml": "<Types/>", "xl/styles.xml": STYLES}
    wb_sheets, wb_rels = [], []
    for i, sh in enumerate(sheets, 1):
        wb_sheets.append(f'<sheet name="{_esc(sh["name"])}" sheetId="{i}" r:id="rId{i}"/>')
        wb_rels.append(
            f'<Relationship Id="rId{i}" Type="x/worksheet" Target="worksheets/sheet{i}.xml"/>'
        )
        headers, data = sh["headers"], sh["rows"]
        styled = sh.get("styled_empty_rows", 0)
        xml_rows = [
            '<row r="1">'
            + "".join(
                f'<c r="{COLS[j]}1" t="inlineStr"><is><t>{_esc(h)}</t></is></c>'
                for j, h in enumerate(headers)
            )
            + "</row>"
        ]
        for k, values in enumerate(data):
            r = k + 2
            hidden = ' hidden="1"' if k in sh.get("hidden", set()) else ""
            cells = "".join(
                _cell(f"{COLS[j]}{r}", v) for j, v in enumerate(values) if v is not None
            )
            xml_rows.append(f'<row r="{r}"{hidden}>{cells}</row>')
        for k in range(styled):
            r = len(data) + 2 + k
            xml_rows.append(f'<row r="{r}"><c r="A{r}" s="1"/></row>')
        last = f"{COLS[len(headers) - 1]}{1 + len(data) + styled}"
        m[f"xl/worksheets/sheet{i}.xml"] = (
            f"<worksheet {NS}><sheetData>{''.join(xml_rows)}</sheetData>"
            '<tableParts count="1"><tablePart r:id="rIdT"/></tableParts></worksheet>'
        )
        m[f"xl/worksheets/_rels/sheet{i}.xml.rels"] = (
            f'<Relationships xmlns="{PKG_RELS}">'
            f'<Relationship Id="rIdT" Type="x/table" Target="../tables/table{i}.xml"/>'
            "</Relationships>"
        )
        cols = "".join(
            f'<tableColumn id="{j + 1}" name="{_esc(h)}"/>' for j, h in enumerate(headers)
        )
        m[f"xl/tables/table{i}.xml"] = (
            f'<table {NS} id="{i}" name="T{i}" displayName="T{i}" ref="A1:{last}">'
            f'<tableColumns count="{len(headers)}">{cols}</tableColumns></table>'
        )
    pr = '<workbookPr date1904="1"/>' if date1904 else ""
    m["xl/workbook.xml"] = f"<workbook {NS}>{pr}<sheets>{''.join(wb_sheets)}</sheets></workbook>"
    m["xl/_rels/workbook.xml.rels"] = (
        f'<Relationships xmlns="{PKG_RELS}">{"".join(wb_rels)}</Relationships>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, xml in m.items():
            z.writestr(name, xml)
    return buf.getvalue()


def standard_workbook() -> bytes:
    """Duas abas de setores aprovados, com ocultas, ignoradas e status variados."""
    return xlsx_bytes(
        [
            {
                "name": "Escrituras",
                "headers": STD,
                "rows": [row("Concluída"), row("Bloqueada"), row("falta ass"), row(None)],
                "hidden": {0, 1},
                "styled_empty_rows": 2,
            },
            {
                "name": "Registro de Imóveis",
                "headers": ["Status", "PRENOTAÇÃO", *[h for h in STD if h != "Status"]],
                "rows": [
                    ["Cancelada", "1", "Registro", "Alta", PEOPLE[2], "45900", None, None, None]
                ],
            },
        ]
    )


def as_legacy_v10(report: dict) -> dict:
    """Relatório 1.1 rebaixado ao formato 1.0 (sem datas), como gravado antes desta etapa."""
    legacy = {k: v for k, v in report.items() if k != "referencia_temporal"}
    legacy["versao"] = "1.0"
    legacy["agregado"] = {k: v for k, v in report["agregado"].items() if k != "datas"}
    legacy["abas"] = [{k: v for k, v in t.items() if k != "datas"} for t in report["abas"]]
    return legacy


def example_export() -> dict:
    """Exportação sintética determinística: seis setores, aba extra pendente, RI com
    vencimento informado. É a fonte do exemplo do contrato em docs/modules."""
    from datetime import UTC, date, datetime, timedelta

    from app.modules.services_snapshot.atlas_export import build_export
    from app.modules.services_snapshot.report import build_attempt, build_report
    from app.modules.services_snapshot.rules import classify_workbook
    from app.modules.services_snapshot.xlsx import parse_workbook

    ref = date(2026, 10, 20)

    def ago(days: int) -> Serial:
        return Serial((ref - timedelta(days=days) - date(1899, 12, 30)).days)

    ri_headers = [*STD, "Vencimento da Prenotação", "PRENOTAÇÃO"]
    sheets = [
        {
            "name": "Escrituras",
            "headers": STD,
            "rows": [
                row("Concluída", inicio=ago(12), termino=ago(2)),
                row("Concluído", inicio=ago(30)),
                row("falta ass", inicio=ago(3)),
                row("Bloqueada", inicio=ago(90)),
                row(None, inicio=ago(5)),
            ],
        },
        {
            "name": "Registro de Imóveis",
            "headers": ri_headers,
            "rows": [
                [*row("Pendente de protocolo", inicio=ago(9)), ago(-3), "1001"],
                [*row("FALTA DOCS", inicio=ago(40)), ago(2), "1002"],
                [*row("Em execução"), None, "1003"],
                [*row("Concluída", inicio=ago(20), termino=ago(14)), ago(25), "1004"],
                [*row("Cancelada", inicio=ago(15), termino=ago(5)), None, None],
            ],
        },
        {
            "name": "Escrituras - Diversas",
            "headers": STD,
            "rows": [row("Aguardando escritura", inicio=ago(61)), row("Talvez")],
        },
        {
            "name": "Registro Civil",
            "headers": STD,
            "rows": [row("Concluída", inicio=ago(1), termino=ago(0)), row("Não iniciada")],
        },
        {
            "name": "Procurações",
            "headers": STD,
            "rows": [row("Finalização", inicio=ago(16)), row("Cancelado", inicio=ago(8))],
        },
        {
            "name": "Diversos",
            "headers": STD,
            "rows": [row("Falta Pagamento", inicio=ago(31)), row(None)],
        },
        {"name": "Rascunho", "headers": ["Tarefa", "Prioridade"], "rows": [["a", "b"]]},
    ]
    tabs = classify_workbook(parse_workbook(xlsx_bytes(sheets)), ref)
    report = build_report(
        source_alias="servicos_andamento_piloto",
        family="documentos_em_andamento",
        run_id="20261020T150000Z-0a1b2c",
        captured_at="2026-10-20T15:00:05Z",
        drive_modified_time="2026-10-20T14:30:00Z",
        drive_version="7",
        tabs=tabs,
        reference=ref,
        generated_at=datetime(2026, 10, 20, 15, 0, 9, tzinfo=UTC),
    )
    attempt = build_attempt(
        datetime(2026, 10, 20, 15, 0, 0, tzinfo=UTC), True, None, None, report["captura"]["run_id"]
    )
    return build_export(report, attempt, datetime(2026, 10, 20, 15, 5, 0, tzinfo=UTC))
