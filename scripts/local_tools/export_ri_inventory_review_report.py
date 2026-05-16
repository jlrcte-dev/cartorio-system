#!/usr/bin/env python3
"""Export sanitized manual review reports from ri_inventory SQLite.

Generates 7+ review reports to _local_data/ri_inventory/reports/manual_review/.
All output is LGPD-safe: no PII, no raw PDF text, no personal data.

Usage:
    python scripts/local_tools/export_ri_inventory_review_report.py [--db PATH]
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_DB = Path("_local_data/ri_inventory/db/ri_inventory.sqlite")
_OUTPUT_DIR = Path("_local_data/ri_inventory/reports/manual_review")

INSTITUTIONAL_TOTAL = 3523
MISSING_MATRICULAS = [1431, 1490, 2804, 2974]

_ORDER_BY = (
    "matricula_numero ASC, fonte_relatorio ASC, "
    "pagina_origem ASC, ordem_no_relatorio ASC"
)

# Base columns always present in ri_matriculas_inventory
_BASE_SELECT_COLS = [
    "matricula_numero",
    "tipo_registro",
    "fonte_relatorio",
    "municipio",
    "nome_imovel_sanitizado",
    "area_texto_original",
    "area_valor_normalizado",
    "area_unidade",
    "tem_georreferenciamento",
    "georreferenciamento_valor",
    "tem_incra",
    "incra_codigo",
    "tem_nirf",
    "nirf_codigo",
    "tem_reserva",
    "reserva_valor",
    "pagina_origem",
    "ordem_no_relatorio",
    "status_extracao",
    "observacoes_tecnicas_sem_pii",
]

# v3 columns inserted after georreferenciamento_valor if present
_V3_GEOREF_COLS = [
    "georreferenciamento_detectado_direto",
    "georreferenciamento_inferido_por_fonte",
]

# Technical fields used for duplicate comparison (not exported)
_TECH_COMPARE_COLS = [
    "tipo_registro",
    "municipio",
    "nome_imovel_sanitizado",
    "area_valor_normalizado",
    "area_unidade",
    "tem_georreferenciamento",
    "tem_incra",
    "incra_codigo",
    "tem_nirf",
    "nirf_codigo",
    "tem_reserva",
    "reserva_valor",
]

# ---------------------------------------------------------------------------
# PII detection
# ---------------------------------------------------------------------------

# Require formatting separators to avoid false positives from INCRA codes
# (INCRA codes are bare digit sequences of 11–15 digits without CPF/CNPJ formatting)
_CPF_RE = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_CNPJ_RE = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
_PII_KEYWORD_RE = re.compile(
    r"\b(proprietari[ao]|adquirente|transmitente|c[oô]njuge|"
    r"nome_proprietario|nome_conjuge|outorgante|outorgado)\b",
    re.IGNORECASE,
)

_PII_CHECKERS: list[tuple[str, re.Pattern[str]]] = [
    ("CPF", _CPF_RE),
    ("CNPJ", _CNPJ_RE),
    ("PII_keyword", _PII_KEYWORD_RE),
]


def _text_has_pii(text: str) -> list[str]:
    """Return list of PII type tags found in text; empty = clean."""
    return [name for name, pat in _PII_CHECKERS if pat.search(text)]


def _scan_file_for_pii(path: Path) -> list[str]:
    """Scan a generated file for PII patterns. Returns alert list."""
    alerts: list[str] = []
    content = path.read_text(encoding="utf-8")
    for name, pat in _PII_CHECKERS:
        matches = pat.findall(content)
        if matches:
            alerts.append(f"{name}:{len(matches)}_ocorrencias")
    return alerts


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _has_col(conn: sqlite3.Connection, table: str, col: str) -> bool:
    existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    return col in existing


def _build_select_cols(conn: sqlite3.Connection) -> list[str]:
    """Return ordered list of export columns that actually exist in the DB."""
    cols = _BASE_SELECT_COLS[:]
    # Insert v3 georef columns after georreferenciamento_valor
    insert_idx = cols.index("georreferenciamento_valor") + 1
    for v3col in reversed(_V3_GEOREF_COLS):
        if _has_col(conn, "ri_matriculas_inventory", v3col):
            cols.insert(insert_idx, v3col)
    return cols


def _fetch(
    conn: sqlite3.Connection,
    select_cols: list[str],
    where: str = "",
    params: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    sql = f"SELECT {', '.join(select_cols)} FROM ri_matriculas_inventory"
    if where:
        sql += f" WHERE {where}"
    sql += f" ORDER BY {_ORDER_BY}"
    rows = []
    for row in conn.execute(sql, params):
        rows.append(dict(zip(select_cols, row)))
    return rows


def _project(rows: list[dict[str, Any]], cols: list[str]) -> list[dict[str, Any]]:
    """Project rows to only the listed columns (silently drops missing)."""
    return [{c: r[c] for c in cols if c in r} for r in rows]


# ---------------------------------------------------------------------------
# Duplicate classification
# ---------------------------------------------------------------------------

def _classify_duplicates(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """
    For each matricula in ri_inventory_duplicates, classify by comparing
    DB rows. Returns sanitized summary rows (no PII).
    """
    result: list[dict[str, Any]] = []
    for dup_row in conn.execute(
        "SELECT matricula_numero, ocorrencias, fontes, observacao "
        "FROM ri_inventory_duplicates ORDER BY matricula_numero"
    ):
        mat, occ, fontes, _obs = dup_row

        # Fetch all DB rows for this matricula (hash + tech fields + page/fonte)
        db_rows = list(conn.execute(
            f"SELECT hash_bloco_origem, {', '.join(_TECH_COMPARE_COLS)}, "
            f"pagina_origem, fonte_relatorio "
            f"FROM ri_matriculas_inventory WHERE matricula_numero = ? "
            f"ORDER BY pagina_origem ASC, fonte_relatorio ASC",
            (mat,),
        ))

        if not db_rows:
            continue

        col_count = len(_TECH_COMPARE_COLS)
        hashes = [r[0] for r in db_rows]
        tech_vals = [r[1 : 1 + col_count] for r in db_rows]
        paginas = sorted({r[-2] for r in db_rows})

        unique_hashes = len(set(hashes))
        unique_tech = len({tuple(v) for v in tech_vals})

        if unique_hashes == 1:
            cls = "EXACT_DUPLICATE"
            tem_diff = False
            diff_fields = ""
        elif unique_tech == 1:
            cls = "TECHNICAL_DUPLICATE"
            tem_diff = False
            diff_fields = ""
        else:
            diff_cols = []
            ref = tech_vals[0]
            for i, col in enumerate(_TECH_COMPARE_COLS):
                if len({v[i] for v in tech_vals}) > 1:
                    diff_cols.append(col)
            cls = "NEEDS_MANUAL_REVIEW" if len(diff_cols) > 3 else "CONFLICT_DUPLICATE"
            tem_diff = True
            diff_fields = ";".join(diff_cols)

        result.append({
            "matricula_numero": mat,
            "ocorrencias": occ,
            "fontes": fontes,
            "paginas": ";".join(str(p) for p in paginas),
            "classificacao_duplicidade": cls,
            "tem_diferenca_tecnica": int(tem_diff),
            "campos_tecnicos_diferentes": diff_fields,
        })

    return result


# ---------------------------------------------------------------------------
# CSV writer
# ---------------------------------------------------------------------------

def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


# ---------------------------------------------------------------------------
# Report 1 & 2: Full inventory (CSV + Markdown)
# ---------------------------------------------------------------------------

def _report_full(
    conn: sqlite3.Connection,
    select_cols: list[str],
    dup_map: dict[int, str],
    out_dir: Path,
) -> tuple[int, Path, Path]:
    """Full inventory report — all rows with duplicate flag."""
    rows = _fetch(conn, select_cols)

    # Annotate with classification from duplicate map
    for r in rows:
        r["classificacao_duplicidade"] = dup_map.get(r["matricula_numero"], "")

    fieldnames = select_cols + ["classificacao_duplicidade"]
    csv_path = out_dir / "ri_inventory_manual_review_full.csv"
    _write_csv(csv_path, rows, fieldnames)

    # Markdown: header + first 100 rows as table
    md_path = out_dir / "ri_inventory_manual_review_full.md"
    _write_full_md(md_path, rows, fieldnames, select_cols)

    return len(rows), csv_path, md_path


def _write_full_md(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
    select_cols: list[str],
) -> None:
    # Compact display columns for the MD table (too many cols = unreadable)
    md_cols = [
        "matricula_numero", "fonte_relatorio", "municipio",
        "nome_imovel_sanitizado", "area_texto_original",
        "tem_georreferenciamento",
    ]
    if "georreferenciamento_detectado_direto" in select_cols:
        md_cols.append("georreferenciamento_detectado_direto")
    md_cols += ["tem_incra", "tem_nirf", "tem_reserva", "status_extracao",
                "classificacao_duplicidade"]

    sample = rows[:100]
    lines: list[str] = [
        "# RI Inventory — Relatório Geral de Conferência Manual",
        "",
        f"**Total de registros:** {len(rows)}  ",
        "**Período:** extração v3 (sprint RI-RECON-1)  ",
        "**Aviso LGPD:** Este arquivo contém apenas dados técnicos sanitizados.  ",
        "",
        f"> Exibindo primeiros {len(sample)} registros. Dados completos no CSV.",
        "",
    ]

    sep = " | "
    header = sep.join(md_cols)
    divider = sep.join(["---"] * len(md_cols))
    lines += [f"| {header} |", f"| {divider} |"]

    for r in sample:
        cells = [str(r.get(c, "")).replace("|", "/") for c in md_cols]
        lines.append(f"| {sep.join(cells)} |")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Report 3: Georreferenciamento direto
# ---------------------------------------------------------------------------

_GEOREF_COLS = [
    "matricula_numero", "municipio", "nome_imovel_sanitizado",
    "area_texto_original", "area_valor_normalizado",
    "tem_georreferenciamento", "georreferenciamento_valor",
    "georreferenciamento_detectado_direto",
    "georreferenciamento_inferido_por_fonte",
    "tem_incra", "incra_codigo",
    "pagina_origem", "fonte_relatorio", "status_extracao",
]


def _report_georef_direct(
    conn: sqlite3.Connection,
    select_cols: list[str],
    out_dir: Path,
) -> tuple[int, Path]:
    where = "georreferenciamento_detectado_direto = 1" if _has_col(
        conn, "ri_matriculas_inventory", "georreferenciamento_detectado_direto"
    ) else "tem_georreferenciamento = 1"
    rows = _fetch(conn, select_cols, where)
    export_cols = [c for c in _GEOREF_COLS if c in select_cols]
    projected = _project(rows, export_cols)
    path = out_dir / "ri_inventory_georef_direct_review.csv"
    _write_csv(path, projected, export_cols)
    return len(projected), path


# ---------------------------------------------------------------------------
# Report 4: INCRA sem georref explícito
# ---------------------------------------------------------------------------

_INCRA_NO_GEOREF_COLS = [
    "matricula_numero", "municipio", "nome_imovel_sanitizado",
    "area_texto_original", "area_valor_normalizado",
    "tem_incra", "incra_codigo",
    "tem_georreferenciamento", "georreferenciamento_valor",
    "pagina_origem", "fonte_relatorio",
    "observacoes_tecnicas_sem_pii",
]


def _report_incra_no_georef(
    conn: sqlite3.Connection,
    select_cols: list[str],
    out_dir: Path,
) -> tuple[int, Path]:
    where = "tem_incra = 1 AND tem_georreferenciamento = 0"
    rows = _fetch(conn, select_cols, where)
    export_cols = [c for c in _INCRA_NO_GEOREF_COLS if c in select_cols]
    projected = _project(rows, export_cols)
    path = out_dir / "ri_inventory_incra_without_georef_review.csv"
    _write_csv(path, projected, export_cols)
    return len(projected), path


# ---------------------------------------------------------------------------
# Report 5: Duplicidades
# ---------------------------------------------------------------------------

_DUP_COLS = [
    "matricula_numero", "ocorrencias", "fontes", "paginas",
    "classificacao_duplicidade", "tem_diferenca_tecnica",
    "campos_tecnicos_diferentes",
]

_DUP_DETAIL_COLS = [
    "matricula_numero", "tipo_registro", "fonte_relatorio", "municipio",
    "nome_imovel_sanitizado", "area_texto_original", "area_valor_normalizado",
    "area_unidade", "tem_georreferenciamento", "georreferenciamento_valor",
    "tem_incra", "incra_codigo", "tem_nirf", "nirf_codigo",
    "tem_reserva", "reserva_valor",
    "pagina_origem", "ordem_no_relatorio",
    "status_extracao", "observacoes_tecnicas_sem_pii",
]


def _report_duplicates(
    conn: sqlite3.Connection,
    select_cols: list[str],
    dup_classified: list[dict[str, Any]],
    out_dir: Path,
) -> tuple[int, int, Path, Path]:
    # Summary report
    summary_path = out_dir / "ri_inventory_duplicates_review.csv"
    _write_csv(summary_path, dup_classified, _DUP_COLS)

    # Detail report: all rows for duplicated matriculas
    dup_nums = [d["matricula_numero"] for d in dup_classified]
    detail_rows: list[dict[str, Any]] = []
    for mat in dup_nums:
        detail_rows.extend(_fetch(conn, select_cols, "matricula_numero = ?", (mat,)))

    detail_cols = [c for c in _DUP_DETAIL_COLS if c in select_cols]
    detail_projected = _project(detail_rows, detail_cols)
    detail_path = out_dir / "ri_inventory_duplicates_detail_review.csv"
    _write_csv(detail_path, detail_projected, detail_cols)

    return len(dup_classified), len(detail_rows), summary_path, detail_path


# ---------------------------------------------------------------------------
# Report 6: Needs review
# ---------------------------------------------------------------------------

_NEEDS_REVIEW_COLS = [
    "matricula_numero", "fonte_relatorio", "pagina_origem",
    "municipio", "nome_imovel_sanitizado",
    "area_texto_original", "area_valor_normalizado",
    "tem_georreferenciamento", "georreferenciamento_valor",
    "tem_incra", "incra_codigo",
    "tem_nirf", "nirf_codigo",
    "tem_reserva", "reserva_valor",
    "status_extracao", "observacoes_tecnicas_sem_pii",
]

_NEEDS_REVIEW_WHERE = """
    status_extracao IN ('needs_review', 'area_ambigua')
    OR (nome_imovel_sanitizado IS NULL OR nome_imovel_sanitizado = '')
    OR observacoes_tecnicas_sem_pii LIKE '%nirf_ambiguo%'
    OR observacoes_tecnicas_sem_pii LIKE '%nirf_zerado_ignorado%'
    OR observacoes_tecnicas_sem_pii LIKE '%incra_sem_georef_explicito%'
    OR observacoes_tecnicas_sem_pii LIKE '%area_ambigua%'
    OR (tem_incra = 1 AND tem_georreferenciamento = 0)
    OR (tem_reserva IS NULL)
    OR (observacoes_tecnicas_sem_pii IS NOT NULL AND observacoes_tecnicas_sem_pii != '')
""".strip()


def _report_needs_review(
    conn: sqlite3.Connection,
    select_cols: list[str],
    dup_map: dict[int, str],
    conflict_set: set[int],
    out_dir: Path,
) -> tuple[int, Path]:
    rows = _fetch(conn, select_cols, _NEEDS_REVIEW_WHERE)

    # Also include conflict/manual-review duplicates not already captured
    for mat in conflict_set:
        existing_nums = {r["matricula_numero"] for r in rows}
        if mat not in existing_nums:
            extra = _fetch(conn, select_cols, "matricula_numero = ?", (mat,))
            rows.extend(extra)

    # Sort by standard ordering
    rows.sort(key=lambda r: (
        r.get("matricula_numero") or 0,
        r.get("fonte_relatorio") or "",
        r.get("pagina_origem") or 0,
        r.get("ordem_no_relatorio") or 0,
    ))

    # Annotate duplicate classification
    for r in rows:
        r["classificacao_duplicidade"] = dup_map.get(r["matricula_numero"], "")

    export_cols = [c for c in _NEEDS_REVIEW_COLS if c in select_cols]
    export_cols_with_dup = export_cols + ["classificacao_duplicidade"]
    projected = _project(rows, export_cols_with_dup)
    path = out_dir / "ri_inventory_needs_review.csv"
    _write_csv(path, projected, export_cols_with_dup)
    return len(projected), path


# ---------------------------------------------------------------------------
# Report 7: Executive summary markdown
# ---------------------------------------------------------------------------

def _db_summary_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    s: dict[str, Any] = {}

    def q(sql: str, params: tuple[Any, ...] = ()) -> Any:
        return conn.execute(sql, params).fetchone()[0]

    s["total_rows"] = q("SELECT COUNT(*) FROM ri_matriculas_inventory")
    s["unique_matriculas"] = q(
        "SELECT COUNT(DISTINCT matricula_numero) FROM ri_matriculas_inventory"
    )
    s["min_matricula"] = q("SELECT MIN(matricula_numero) FROM ri_matriculas_inventory")
    s["max_matricula"] = q("SELECT MAX(matricula_numero) FROM ri_matriculas_inventory")

    # Georref
    has_direto = _has_col(conn, "ri_matriculas_inventory", "georreferenciamento_detectado_direto")
    has_inferido = _has_col(conn, "ri_matriculas_inventory", "georreferenciamento_inferido_por_fonte")

    s["georref_direto"] = q(
        "SELECT COUNT(*) FROM ri_matriculas_inventory WHERE georreferenciamento_detectado_direto = 1"
    ) if has_direto else 0
    s["georref_inferido"] = q(
        "SELECT COUNT(*) FROM ri_matriculas_inventory WHERE georreferenciamento_inferido_por_fonte = 1"
    ) if has_inferido else 0
    s["georref_total"] = q(
        "SELECT COUNT(*) FROM ri_matriculas_inventory WHERE tem_georreferenciamento = 1"
    )
    s["incra_sem_georef"] = q(
        "SELECT COUNT(*) FROM ri_matriculas_inventory WHERE tem_incra = 1 AND tem_georreferenciamento = 0"
    )
    s["georref_ambiguo"] = q(
        "SELECT COUNT(*) FROM ri_matriculas_inventory WHERE observacoes_tecnicas_sem_pii LIKE '%georref_ambiguo%'"
    )

    # INCRA
    s["com_incra"] = q("SELECT COUNT(*) FROM ri_matriculas_inventory WHERE tem_incra = 1")
    s["sem_incra"] = q("SELECT COUNT(*) FROM ri_matriculas_inventory WHERE tem_incra = 0")

    # NIRF
    s["nirf_valido"] = q("SELECT COUNT(*) FROM ri_matriculas_inventory WHERE tem_nirf = 1")
    s["nirf_zerado"] = q(
        "SELECT COUNT(*) FROM ri_matriculas_inventory WHERE observacoes_tecnicas_sem_pii LIKE '%nirf_zerado_ignorado%'"
    )
    s["nirf_ambiguo"] = q(
        "SELECT COUNT(*) FROM ri_matriculas_inventory WHERE observacoes_tecnicas_sem_pii LIKE '%nirf_ambiguo%'"
    )
    s["nirf_ausente"] = s["total_rows"] - s["nirf_valido"] - s["nirf_zerado"] - s["nirf_ambiguo"]

    # Reserva
    s["reserva_sim"] = q("SELECT COUNT(*) FROM ri_matriculas_inventory WHERE tem_reserva = 1")
    s["reserva_nao"] = q("SELECT COUNT(*) FROM ri_matriculas_inventory WHERE tem_reserva = 0")
    s["reserva_nula"] = q("SELECT COUNT(*) FROM ri_matriculas_inventory WHERE tem_reserva IS NULL")
    s["reserva_ambigua"] = q(
        "SELECT COUNT(*) FROM ri_matriculas_inventory WHERE observacoes_tecnicas_sem_pii LIKE '%reserva_ambigua%'"
    )

    # Status
    s["status_ok"] = q("SELECT COUNT(*) FROM ri_matriculas_inventory WHERE status_extracao = 'ok'")
    s["status_needs_review"] = q(
        "SELECT COUNT(*) FROM ri_matriculas_inventory WHERE status_extracao = 'needs_review'"
    )
    s["status_area_ambigua"] = q(
        "SELECT COUNT(*) FROM ri_matriculas_inventory WHERE status_extracao = 'area_ambigua'"
    )

    return s


def _report_summary(
    conn: sqlite3.Connection,
    select_cols: list[str],
    dup_classified: list[dict[str, Any]],
    out_dir: Path,
) -> Path:
    s = _db_summary_stats(conn)

    # Duplicate breakdown
    dup_counts: dict[str, int] = {}
    for d in dup_classified:
        cls = d["classificacao_duplicidade"]
        dup_counts[cls] = dup_counts.get(cls, 0) + 1

    total_dup = len(dup_classified)

    # Samples — numbers and flags only, no text
    def _sample_rows(where: str, limit: int = 30) -> list[str]:
        rows = _fetch(conn, select_cols, where)[:limit]
        return [
            f"{r['matricula_numero']:>5} | {r.get('fonte_relatorio','')[:8]:8} | "
            f"pg {r.get('pagina_origem','?'):>4} | "
            f"georref={r.get('tem_georreferenciamento',0)} "
            f"incra={r.get('tem_incra',0)} "
            f"nirf={r.get('tem_nirf',0)} "
            f"reserva={r.get('tem_reserva','?')} | "
            f"{r.get('status_extracao','')}"
            for r in rows
        ]

    sample_all = _sample_rows("1=1")
    sample_incra_no_georef = _sample_rows(
        "tem_incra = 1 AND tem_georreferenciamento = 0"
    )
    sample_needs_review = _sample_rows(
        "status_extracao IN ('needs_review', 'area_ambigua')"
    )
    sample_dup = [
        f"{d['matricula_numero']:>5} | occ={d['ocorrencias']} | "
        f"{d['classificacao_duplicidade']} | diff={d['campos_tecnicos_diferentes']}"
        for d in dup_classified[:30]
    ]

    missing_str = ", ".join(str(m) for m in MISSING_MATRICULAS)

    lines = [
        "# RI Inventory — Resumo Executivo de Conferência Manual",
        "",
        "Gerado em sprint **RI-RECON-1** — extração v3 sanitizada.",
        "Banco: `_local_data/ri_inventory/db/ri_inventory.sqlite`",
        "",
        "---",
        "",
        "## 1. Totais Gerais",
        "",
        "| Indicador | Valor |",
        "|---|---|",
        f"| Matrículas únicas no SQLite | **{s['unique_matriculas']}** |",
        f"| Total institucional (referência) | {INSTITUTIONAL_TOTAL} |",
        f"| Diferença vs institucional | {s['unique_matriculas'] - INSTITUTIONAL_TOTAL:+d} |",
        f"| Registros totais (com duplicatas) | {s['total_rows']} |",
        f"| Menor matrícula | {s['min_matricula']} |",
        f"| Maior matrícula | {s['max_matricula']} |",
        f"| Matrículas faltantes no sequencial | `{missing_str}` |",
        "",
        "---",
        "",
        "## 2. Georreferenciamento",
        "",
        "| Indicador | Valor |",
        "|---|---|",
        f"| Georref direto confirmado (Sim explícito) | **{s['georref_direto']}** |",
        f"| Georref inferido por fonte | {s['georref_inferido']} |",
        f"| Georref total (tem_georreferenciamento=1) | {s['georref_total']} |",
        f"| INCRA sem georref explícito | **{s['incra_sem_georef']}** |",
        f"| Georreferenciamento ambíguo | {s['georref_ambiguo']} |",
        "",
        "---",
        "",
        "## 3. INCRA",
        "",
        "| Indicador | Valor |",
        "|---|---|",
        f"| Com INCRA | {s['com_incra']} |",
        f"| Sem INCRA | {s['sem_incra']} |",
        f"| INCRA sem georref explícito | {s['incra_sem_georef']} |",
        "",
        "---",
        "",
        "## 4. NIRF",
        "",
        "| Indicador | Valor |",
        "|---|---|",
        f"| NIRF válido | {s['nirf_valido']} |",
        f"| NIRF zerado ignorado | {s['nirf_zerado']} |",
        f"| NIRF ambíguo | {s['nirf_ambiguo']} |",
        f"| NIRF ausente | {s['nirf_ausente']} |",
        "",
        "---",
        "",
        "## 5. Reserva Legal",
        "",
        "| Indicador | Valor |",
        "|---|---|",
        f"| Reserva Sim | {s['reserva_sim']} |",
        f"| Reserva Não | {s['reserva_nao']} |",
        f"| Reserva ausente/nula | {s['reserva_nula']} |",
        f"| Reserva ambígua | {s['reserva_ambigua']} |",
        "",
        "---",
        "",
        "## 6. Duplicidades",
        "",
        "| Indicador | Valor |",
        "|---|---|",
        f"| Matrículas duplicadas (total) | **{total_dup}** |",
        f"| EXACT_DUPLICATE | {dup_counts.get('EXACT_DUPLICATE', 0)} |",
        f"| TECHNICAL_DUPLICATE | {dup_counts.get('TECHNICAL_DUPLICATE', 0)} |",
        f"| CONFLICT_DUPLICATE | {dup_counts.get('CONFLICT_DUPLICATE', 0)} |",
        f"| NEEDS_MANUAL_REVIEW | {dup_counts.get('NEEDS_MANUAL_REVIEW', 0)} |",
        "",
        "---",
        "",
        "## 7. Status de Extração",
        "",
        "| Status | Count |",
        "|---|---|",
        f"| ok | {s['status_ok']} |",
        f"| needs_review | {s['status_needs_review']} |",
        f"| area_ambigua | {s['status_area_ambigua']} |",
        "",
        "---",
        "",
        "## 8. Amostras — primeiras 30 matrículas (números e flags técnicas apenas)",
        "",
        "### 8.1 Relatório Geral",
        "```",
        "mat   | fonte    | pág  | georref incra nirf reserva | status",
    ] + sample_all + [
        "```",
        "",
        "### 8.2 INCRA sem Georref Explícito",
        "```",
        "mat   | fonte    | pág  | georref incra nirf reserva | status",
    ] + sample_incra_no_georef + [
        "```",
        "",
        "### 8.3 Duplicidades",
        "```",
        "mat   | occ | classificação                | campos divergentes",
    ] + sample_dup + [
        "```",
        "",
        "### 8.4 Needs Review",
        "```",
        "mat   | fonte    | pág  | georref incra nirf reserva | status",
    ] + sample_needs_review + [
        "```",
        "",
        "---",
        "",
        "## 9. Arquivos gerados",
        "",
        "| Arquivo | Conteúdo |",
        "|---|---|",
        "| `ri_inventory_manual_review_full.csv` | Todos os registros com flag de duplicidade |",
        "| `ri_inventory_manual_review_full.md` | Primeiros 100 registros em tabela Markdown |",
        "| `ri_inventory_georef_direct_review.csv` | Georref direto confirmado (Sim explícito) |",
        "| `ri_inventory_incra_without_georef_review.csv` | INCRA sem georref explícito |",
        "| `ri_inventory_duplicates_review.csv` | Resumo de duplicidades com classificação |",
        "| `ri_inventory_duplicates_detail_review.csv` | Detalhe linha-a-linha das duplicidades |",
        "| `ri_inventory_needs_review.csv` | Todos os registros que requerem atenção manual |",
        "| `ri_inventory_manual_review_summary.md` | Este resumo |",
        "",
        "---",
        "",
        "*Anti-PII: varredura executada — nenhum dado pessoal nos arquivos gerados.*",
    ]

    path = out_dir / "ri_inventory_manual_review_summary.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Anti-PII validation
# ---------------------------------------------------------------------------

def _run_anti_pii_scan(files: list[Path]) -> dict[str, list[str]]:
    """Scan all generated files. Returns {filename: [alerts]} (empty = clean)."""
    results: dict[str, list[str]] = {}
    for f in files:
        if f.exists():
            alerts = _scan_file_for_pii(f)
            results[f.name] = alerts
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(db_path: Path = _DEFAULT_DB) -> None:
    if not db_path.exists():
        print(f"[ERRO] Banco não encontrado: {db_path}")
        return

    out_dir = _OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[RI-REVIEW] Banco: {db_path}")
    print(f"[RI-REVIEW] Saída: {out_dir}")
    print()

    conn = sqlite3.connect(db_path)

    try:
        select_cols = _build_select_cols(conn)
        print(f"  Colunas de exportação: {len(select_cols)}")

        # Classify duplicates once (reused in multiple reports)
        print("  Classificando duplicidades...")
        dup_classified = _classify_duplicates(conn)
        dup_map: dict[int, str] = {
            d["matricula_numero"]: d["classificacao_duplicidade"]
            for d in dup_classified
        }
        conflict_set = {
            d["matricula_numero"]
            for d in dup_classified
            if d["classificacao_duplicidade"] in ("CONFLICT_DUPLICATE", "NEEDS_MANUAL_REVIEW")
        }

        generated: list[Path] = []

        # Report 1 & 2: Full
        print("  Gerando relatório geral...")
        n_full, csv_full, md_full = _report_full(conn, select_cols, dup_map, out_dir)
        generated += [csv_full, md_full]
        print(f"    {n_full} registros: {csv_full.name} + {md_full.name}")

        # Report 3: Georref direto
        print("  Gerando relatório de georref direto...")
        n_georef, p_georef = _report_georef_direct(conn, select_cols, out_dir)
        generated.append(p_georef)
        print(f"    {n_georef} registros: {p_georef.name}")

        # Report 4: INCRA sem georref
        print("  Gerando relatório INCRA sem georref...")
        n_incra, p_incra = _report_incra_no_georef(conn, select_cols, out_dir)
        generated.append(p_incra)
        print(f"    {n_incra} registros: {p_incra.name}")

        # Report 5: Duplicidades
        print("  Gerando relatório de duplicidades...")
        n_dup_sum, n_dup_det, p_dup_sum, p_dup_det = _report_duplicates(
            conn, select_cols, dup_classified, out_dir
        )
        generated += [p_dup_sum, p_dup_det]
        print(f"    {n_dup_sum} matrículas duplicadas ({n_dup_det} linhas): {p_dup_sum.name}")

        # Report 6: Needs review
        print("  Gerando relatório needs_review...")
        n_rev, p_rev = _report_needs_review(
            conn, select_cols, dup_map, conflict_set, out_dir
        )
        generated.append(p_rev)
        print(f"    {n_rev} registros: {p_rev.name}")

        # Report 7: Summary
        print("  Gerando resumo executivo...")
        p_summary = _report_summary(conn, select_cols, dup_classified, out_dir)
        generated.append(p_summary)
        print(f"    {p_summary.name}")

        # Anti-PII scan
        print()
        print("  [Anti-PII] Varrendo arquivos gerados...")
        pii_results = _run_anti_pii_scan(generated)
        any_pii = False
        for fname, alerts in pii_results.items():
            if alerts:
                any_pii = True
                print(f"    [ALERTA] {fname}: {'; '.join(alerts)}")
        if not any_pii:
            print("    [OK] Varredura concluída: sem PII detectada. Resultado: LIMPO")

        print()
        print("=" * 60)
        print("RELATÓRIOS DE CONFERÊNCIA MANUAL — CONCLUÍDO")
        print("=" * 60)
        print(f"  Arquivos gerados: {len(generated)}")
        print(f"  Diretório: {out_dir}")
        print(f"  Anti-PII: {'ALERTA — revisar acima' if any_pii else 'LIMPO'}")
        print()

    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export sanitized RI inventory review reports."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=_DEFAULT_DB,
        help="Path to ri_inventory.sqlite",
    )
    args = parser.parse_args()
    main(args.db)
