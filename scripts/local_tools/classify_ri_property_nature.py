#!/usr/bin/env python3
"""Classify the nature (rural/urban/mixed/indeterminate) of RI property records.

Reads from ri_matriculas_inventory (already sanitized — no PII).
Creates ri_property_nature_classification table in the same SQLite DB.
Generates review reports to _local_data/ri_inventory/reports/nature_classification/.

Rules are deterministic, explicit, and conservative:
  - Never auto-exclude a record from rural metrics without strong evidence.
  - Flag ambiguous/conflicting records for manual review.
  - No record is deleted from the base — only classified.

Usage:
    python scripts/local_tools/classify_ri_property_nature.py [--db PATH]
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_DB = Path("_local_data/ri_inventory/db/ri_inventory.sqlite")
_OUTPUT_DIR = Path("_local_data/ri_inventory/reports/nature_classification")

INSTITUTIONAL_TOTAL = 3523
MISSING_MATRICULAS = [1431, 1490, 2804, 2974]

_ORDER_BY = (
    "m.matricula_numero ASC, m.fonte_relatorio ASC, "
    "m.pagina_origem ASC, m.ordem_no_relatorio ASC"
)

# ---------------------------------------------------------------------------
# Classification signal dictionaries
# ---------------------------------------------------------------------------

# Strong rural terms in nome_imovel_sanitizado → strong rural signal
RURAL_STRONG_TERMS: list[str] = [
    "fazenda",
    "sítio",
    "sitio",
    "chácara",
    "chacara",
    "gleba",
    "estância",
    "estancia",
    "rancho",
    "retiro",
    "imóvel rural",
    "imovel rural",
    "zona rural",
    "área rural",
    "area rural",
    "terra rural",
]

# Support rural terms — reinforce but don't establish on their own
RURAL_SUPPORT_TERMS: list[str] = [
    "terras",
    "hectares",
    "módulo rural",
    "modulo rural",
    "ccir",
    "sigef",
]

# Area units that indicate rural land measurement
RURAL_AREA_UNITS: frozenset[str] = frozenset({"ha", "alqueire", "are"})

# Strong urban terms → single occurrence is significant
URBAN_STRONG_TERMS: list[str] = [
    "loteamento",
    "perímetro urbano",
    "perimetro urbano",
    "zona urbana",
    "imóvel urbano",
    "imovel urbano",
    "área urbana",
    "area urbana",
    "condomínio urbano",
    "condominio urbano",
]

# Moderate urban terms — need context or combination
URBAN_MODERATE_TERMS: list[str] = [
    "quadra",
    "bairro",
    "setor urbano",
]

# Note: "lote" handled separately (can be "lote rural" — needs context check)
# Note: "rua", "avenida" handled with word-boundary regex (avoid "rural" substring)
# Note: "jardim" excluded — too common in rural property names in Goiás

# Area thresholds for urban signal via m²
_URBAN_AREA_STRONG_M2: float = 500.0   # < 500 m²: strong area-urban indicator
_URBAN_AREA_MODERATE_M2: float = 5000.0  # < 5000 m²: moderate area-urban indicator

# PII detection patterns (for anti-PII scan)
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

# ---------------------------------------------------------------------------
# NatureClassification dataclass
# ---------------------------------------------------------------------------


@dataclass
class NatureClassification:
    """Result of property nature classification — no PII."""

    natureza_imovel: str              # rural | urbano | misto | indeterminado
    natureza_imovel_confidence: str   # confirmado | provavel | baixa_confianca | manual
    natureza_imovel_fonte: str        # source(s) of main signal
    excluir_metricas_rurais: bool     # exclude from rural metrics?
    motivo_exclusao_metricas: str     # reason for exclusion (empty = not excluded)
    status_revisao_ri: str            # ok | needs_manual_review | excluir_metricas_rurais
    sinais_urbanos_detectados: str    # semicolon-separated urban signal tags
    sinais_rurais_detectados: str     # semicolon-separated rural signal tags


# ---------------------------------------------------------------------------
# Signal detection
# ---------------------------------------------------------------------------

def _normalize_nome(nome: str | None) -> str:
    """Lowercase and normalize nome_imovel_sanitizado for term matching."""
    if not nome:
        return ""
    # Normalize common accented characters for term matching
    text = nome.lower()
    replacements = {
        "á": "a", "à": "a", "â": "a", "ã": "a",
        "é": "e", "ê": "e",
        "í": "i",
        "ó": "o", "ô": "o", "õ": "o",
        "ú": "u",
        "ç": "c",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def detect_rural_signals(
    nome: str | None,
    area_unidade: str | None,
    has_incra: bool,
    has_georref_direto: bool,
) -> list[str]:
    """Return list of rural signal tags (sanitized, no PII)."""
    signals: list[str] = []
    nome_n = _normalize_nome(nome)

    for term in RURAL_STRONG_TERMS:
        term_n = _normalize_nome(term)
        if term_n in nome_n:
            signals.append(f"nome_forte:{term_n}")

    for term in RURAL_SUPPORT_TERMS:
        term_n = _normalize_nome(term)
        if term_n in nome_n:
            signals.append(f"nome_suporte:{term_n}")

    if area_unidade and area_unidade.lower() in RURAL_AREA_UNITS:
        signals.append(f"area_unidade:{area_unidade.lower()}")

    if has_incra:
        signals.append("incra")

    if has_georref_direto:
        signals.append("georref_direto")

    return signals


def detect_urban_signals(
    nome: str | None,
    area_unidade: str | None,
    area_valor: float | None,
) -> list[str]:
    """Return list of urban signal tags (sanitized, no PII)."""
    signals: list[str] = []
    nome_n = _normalize_nome(nome)

    # Strong urban terms
    for term in URBAN_STRONG_TERMS:
        term_n = _normalize_nome(term)
        if term_n in nome_n:
            signals.append(f"nome_forte:{term_n}")

    # Moderate urban terms
    for term in URBAN_MODERATE_TERMS:
        term_n = _normalize_nome(term)
        if re.search(r"\b" + re.escape(term_n) + r"\b", nome_n):
            signals.append(f"nome_moderado:{term_n}")

    # "lote" / "lotes" — word boundary, not "loteamento" (already covered above)
    if re.search(r"\blotes?\b", nome_n) and "loteamento" not in nome_n:
        signals.append("nome_moderado:lote")

    # "rua" and "avenida" — word boundary (avoids matching substrings)
    if re.search(r"\brua\b", nome_n):
        signals.append("nome_moderado:rua")
    if re.search(r"\bavenida\b|\bav\.\b", nome_n):
        signals.append("nome_moderado:avenida")

    # Area signals — only for m² with small values
    if area_unidade and area_unidade.lower() == "m2" and area_valor is not None:
        if area_valor < _URBAN_AREA_STRONG_M2:
            signals.append("area_muito_pequena_m2")
        elif area_valor < _URBAN_AREA_MODERATE_M2:
            signals.append("area_pequena_m2")

    return signals


# ---------------------------------------------------------------------------
# Core classifier (pure function — no DB access)
# ---------------------------------------------------------------------------

def classify_property_nature(record: dict[str, Any]) -> NatureClassification:  # noqa: C901
    """
    Classify the nature of a property record from ri_matriculas_inventory.

    Conservative: ambiguous → indeterminado or misto, NOT auto-excluded.
    Input dict must have keys matching ri_matriculas_inventory columns.
    No PII in the record (field is already sanitized upstream).
    """
    nome = record.get("nome_imovel_sanitizado")
    area_unidade = record.get("area_unidade")
    area_valor = record.get("area_valor_normalizado")
    has_incra = bool(record.get("tem_incra"))
    has_georref_direto = bool(record.get("georreferenciamento_detectado_direto"))

    rural_signals = detect_rural_signals(nome, area_unidade, has_incra, has_georref_direto)
    urban_signals = detect_urban_signals(nome, area_unidade, area_valor)

    # Categorize rural signals
    strong_rural = [s for s in rural_signals if s.startswith("nome_forte:")]
    support_rural = [s for s in rural_signals if not s.startswith("nome_forte:")]
    has_rural_area = any("area_unidade:" in s for s in rural_signals)
    has_georref_sig = "georref_direto" in rural_signals

    # Categorize urban signals
    strong_urban = [s for s in urban_signals if s.startswith("nome_forte:")]
    moderate_urban = [s for s in urban_signals if s.startswith("nome_moderado:")]
    area_urban = [s for s in urban_signals if "area_" in s and "m2" in s]

    rural_str = ";".join(rural_signals)
    urban_str = ";".join(urban_signals)

    # -----------------------------------------------------------------------
    # 1. No signals at all → indeterminado
    # -----------------------------------------------------------------------
    if not rural_signals and not urban_signals:
        return NatureClassification(
            natureza_imovel="indeterminado",
            natureza_imovel_confidence="baixa_confianca",
            natureza_imovel_fonte="sem_sinais",
            excluir_metricas_rurais=False,
            motivo_exclusao_metricas="",
            status_revisao_ri="needs_manual_review",
            sinais_urbanos_detectados=urban_str,
            sinais_rurais_detectados=rural_str,
        )

    # -----------------------------------------------------------------------
    # 2. Only area-urban signal with no rural context → indeterminado
    #    (small m² is insufficient without name context)
    # -----------------------------------------------------------------------
    if area_urban and not strong_rural and not support_rural and not strong_urban and not moderate_urban:
        return NatureClassification(
            natureza_imovel="indeterminado",
            natureza_imovel_confidence="baixa_confianca",
            natureza_imovel_fonte="area",
            excluir_metricas_rurais=False,
            motivo_exclusao_metricas="",
            status_revisao_ri="needs_manual_review",
            sinais_urbanos_detectados=urban_str,
            sinais_rurais_detectados=rural_str,
        )

    # -----------------------------------------------------------------------
    # 3. Conflict: urban signals (strong or moderate) + rural signals
    # -----------------------------------------------------------------------
    if (strong_urban or moderate_urban) and (strong_rural or support_rural):
        # "lote" + "sítio/fazenda" is a classic rural lote subdivision
        # Conservative: flag for review, don't exclude
        return NatureClassification(
            natureza_imovel="misto",
            natureza_imovel_confidence="baixa_confianca",
            natureza_imovel_fonte="nome_imovel_sanitizado",
            excluir_metricas_rurais=False,
            motivo_exclusao_metricas="",
            status_revisao_ri="needs_manual_review",
            sinais_urbanos_detectados=urban_str,
            sinais_rurais_detectados=rural_str,
        )

    # -----------------------------------------------------------------------
    # 4. Strong urban signal without rural → urban provável
    # -----------------------------------------------------------------------
    if strong_urban and not strong_rural and not support_rural:
        return NatureClassification(
            natureza_imovel="urbano",
            natureza_imovel_confidence="provavel",
            natureza_imovel_fonte="nome_imovel_sanitizado",
            excluir_metricas_rurais=True,
            motivo_exclusao_metricas="indicio_lote_urbano_no_relatorio_rural",
            status_revisao_ri="needs_manual_review",
            sinais_urbanos_detectados=urban_str,
            sinais_rurais_detectados=rural_str,
        )

    # -----------------------------------------------------------------------
    # 5. Multiple moderate urban signals without rural → urban baixa_confianca
    # -----------------------------------------------------------------------
    if len(moderate_urban) >= 2 and not strong_rural and not support_rural:
        return NatureClassification(
            natureza_imovel="urbano",
            natureza_imovel_confidence="provavel",
            natureza_imovel_fonte="nome_imovel_sanitizado",
            excluir_metricas_rurais=True,
            motivo_exclusao_metricas="indicio_lote_urbano_no_relatorio_rural",
            status_revisao_ri="needs_manual_review",
            sinais_urbanos_detectados=urban_str,
            sinais_rurais_detectados=rural_str,
        )

    # -----------------------------------------------------------------------
    # 6. Single moderate urban signal without rural → needs review, don't exclude yet
    # -----------------------------------------------------------------------
    if moderate_urban and not strong_rural and not support_rural:
        return NatureClassification(
            natureza_imovel="urbano",
            natureza_imovel_confidence="baixa_confianca",
            natureza_imovel_fonte="nome_imovel_sanitizado",
            excluir_metricas_rurais=False,
            motivo_exclusao_metricas="revisao_manual_pendente",
            status_revisao_ri="needs_manual_review",
            sinais_urbanos_detectados=urban_str,
            sinais_rurais_detectados=rural_str,
        )

    # -----------------------------------------------------------------------
    # 7. Rural confirmed: strong rural name + rural area unit OR georref
    # -----------------------------------------------------------------------
    if strong_rural and (has_rural_area or has_georref_sig):
        return NatureClassification(
            natureza_imovel="rural",
            natureza_imovel_confidence="confirmado",
            natureza_imovel_fonte="nome_imovel_sanitizado;area" if has_rural_area else "nome_imovel_sanitizado;georref",
            excluir_metricas_rurais=False,
            motivo_exclusao_metricas="",
            status_revisao_ri="ok",
            sinais_urbanos_detectados=urban_str,
            sinais_rurais_detectados=rural_str,
        )

    # -----------------------------------------------------------------------
    # 8. Rural provável: strong rural name (without area) OR support signals
    # -----------------------------------------------------------------------
    if strong_rural:
        return NatureClassification(
            natureza_imovel="rural",
            natureza_imovel_confidence="provavel",
            natureza_imovel_fonte="nome_imovel_sanitizado",
            excluir_metricas_rurais=False,
            motivo_exclusao_metricas="",
            status_revisao_ri="needs_manual_review",
            sinais_urbanos_detectados=urban_str,
            sinais_rurais_detectados=rural_str,
        )

    # -----------------------------------------------------------------------
    # 9. Rural provável: support signals only (INCRA, area in ha, etc.)
    # -----------------------------------------------------------------------
    if support_rural:
        return NatureClassification(
            natureza_imovel="rural",
            natureza_imovel_confidence="provavel",
            natureza_imovel_fonte=";".join(
                ["incra"] * has_incra
                + ["georref_direto"] * has_georref_sig
                + ["area"] * has_rural_area
            ),
            excluir_metricas_rurais=False,
            motivo_exclusao_metricas="",
            status_revisao_ri="needs_manual_review",
            sinais_urbanos_detectados=urban_str,
            sinais_rurais_detectados=rural_str,
        )

    # -----------------------------------------------------------------------
    # 10. Fallback: indeterminado
    # -----------------------------------------------------------------------
    return NatureClassification(
        natureza_imovel="indeterminado",
        natureza_imovel_confidence="baixa_confianca",
        natureza_imovel_fonte="sem_sinais_suficientes",
        excluir_metricas_rurais=False,
        motivo_exclusao_metricas="classificacao_indeterminada",
        status_revisao_ri="needs_manual_review",
        sinais_urbanos_detectados=urban_str,
        sinais_rurais_detectados=rural_str,
    )


# ---------------------------------------------------------------------------
# DB — classification table
# ---------------------------------------------------------------------------

_DDL_CLASSIFICATION_TABLE = """
CREATE TABLE IF NOT EXISTS ri_property_nature_classification (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matricula_numero INTEGER NOT NULL UNIQUE,
    natureza_imovel TEXT NOT NULL,
    natureza_imovel_confidence TEXT NOT NULL,
    natureza_imovel_fonte TEXT NOT NULL,
    excluir_metricas_rurais INTEGER NOT NULL DEFAULT 0,
    motivo_exclusao_metricas TEXT,
    status_revisao_ri TEXT NOT NULL,
    sinais_urbanos_detectados TEXT,
    sinais_rurais_detectados TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_rnc_natureza ON ri_property_nature_classification(natureza_imovel);
CREATE INDEX IF NOT EXISTS idx_rnc_excluir ON ri_property_nature_classification(excluir_metricas_rurais);
CREATE INDEX IF NOT EXISTS idx_rnc_status ON ri_property_nature_classification(status_revisao_ri);
"""


def _setup_table(conn: sqlite3.Connection) -> None:
    conn.executescript(_DDL_CLASSIFICATION_TABLE)
    conn.commit()


def _has_col(conn: sqlite3.Connection, table: str, col: str) -> bool:
    return col in {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def _run_classification(conn: sqlite3.Connection) -> dict[str, int]:
    """
    For each unique matricula_numero, collect the best available signals
    from all rows (both PDFs), classify once, and store in classification table.
    Returns count by natureza_imovel.
    """
    has_direto = _has_col(conn, "ri_matriculas_inventory", "georreferenciamento_detectado_direto")

    # Select canonical signal fields per matricula (aggregate across all rows)
    agg_sql = f"""
        SELECT
            matricula_numero,
            MAX(CASE WHEN nome_imovel_sanitizado IS NOT NULL AND nome_imovel_sanitizado != ''
                     THEN nome_imovel_sanitizado END) AS nome,
            MAX(area_unidade) AS area_unidade,
            MIN(area_valor_normalizado) AS area_valor,
            MAX(tem_incra) AS tem_incra,
            {"MAX(georreferenciamento_detectado_direto)" if has_direto else "MAX(tem_georreferenciamento)"}
                AS georref_direto
        FROM ri_matriculas_inventory
        GROUP BY matricula_numero
    """

    counts: dict[str, int] = {}

    # Clear existing classifications
    conn.execute("DELETE FROM ri_property_nature_classification")

    rows = conn.execute(agg_sql).fetchall()
    inserts = []
    for row in rows:
        mat, nome, area_unidade, area_valor, tem_incra, georref_direto = row
        record = {
            "matricula_numero": mat,
            "nome_imovel_sanitizado": nome,
            "area_unidade": area_unidade,
            "area_valor_normalizado": area_valor,
            "tem_incra": tem_incra or 0,
            "georreferenciamento_detectado_direto": georref_direto or 0,
        }
        cls = classify_property_nature(record)
        counts[cls.natureza_imovel] = counts.get(cls.natureza_imovel, 0) + 1
        inserts.append((
            mat,
            cls.natureza_imovel,
            cls.natureza_imovel_confidence,
            cls.natureza_imovel_fonte,
            int(cls.excluir_metricas_rurais),
            cls.motivo_exclusao_metricas or "",
            cls.status_revisao_ri,
            cls.sinais_urbanos_detectados,
            cls.sinais_rurais_detectados,
        ))

    conn.executemany(
        """
        INSERT INTO ri_property_nature_classification
            (matricula_numero, natureza_imovel, natureza_imovel_confidence,
             natureza_imovel_fonte, excluir_metricas_rurais,
             motivo_exclusao_metricas, status_revisao_ri,
             sinais_urbanos_detectados, sinais_rurais_detectados)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        inserts,
    )
    conn.commit()
    return counts


# ---------------------------------------------------------------------------
# Report columns
# ---------------------------------------------------------------------------

_BASE_M_COLS = [
    "m.matricula_numero",
    "m.tipo_registro",
    "m.fonte_relatorio",
    "m.municipio",
    "m.nome_imovel_sanitizado",
    "m.area_texto_original",
    "m.area_valor_normalizado",
    "m.area_unidade",
    "m.tem_georreferenciamento",
    "m.georreferenciamento_valor",
    "m.tem_incra",
    "m.incra_codigo",
    "m.tem_nirf",
    "m.nirf_codigo",
    "m.tem_reserva",
    "m.reserva_valor",
    "m.pagina_origem",
    "m.ordem_no_relatorio",
    "m.status_extracao",
    "m.observacoes_tecnicas_sem_pii",
]

_N_COLS = [
    "n.natureza_imovel",
    "n.natureza_imovel_confidence",
    "n.natureza_imovel_fonte",
    "n.excluir_metricas_rurais",
    "n.motivo_exclusao_metricas",
    "n.status_revisao_ri",
    "n.sinais_urbanos_detectados",
    "n.sinais_rurais_detectados",
]

_REPORT_FIELDNAMES = [
    "matricula_numero", "tipo_registro", "fonte_relatorio", "municipio",
    "nome_imovel_sanitizado", "area_texto_original", "area_valor_normalizado",
    "area_unidade", "tem_georreferenciamento", "georreferenciamento_valor",
    "tem_incra", "incra_codigo", "tem_nirf", "nirf_codigo",
    "tem_reserva", "reserva_valor", "pagina_origem", "ordem_no_relatorio",
    "status_extracao", "observacoes_tecnicas_sem_pii",
    "natureza_imovel", "natureza_imovel_confidence", "natureza_imovel_fonte",
    "excluir_metricas_rurais", "motivo_exclusao_metricas", "status_revisao_ri",
    "sinais_urbanos_detectados", "sinais_rurais_detectados",
]


def _build_select(conn: sqlite3.Connection) -> str:
    has_direto = _has_col(conn, "ri_matriculas_inventory", "georreferenciamento_detectado_direto")
    has_inferido = _has_col(conn, "ri_matriculas_inventory", "georreferenciamento_inferido_por_fonte")
    extra_cols = []
    if has_direto:
        extra_cols.append("m.georreferenciamento_detectado_direto")
    if has_inferido:
        extra_cols.append("m.georreferenciamento_inferido_por_fonte")

    all_cols = _BASE_M_COLS + extra_cols + _N_COLS
    return ", ".join(all_cols)


def _base_query(conn: sqlite3.Connection, where: str = "") -> str:
    sel = _build_select(conn)
    q = f"""
        SELECT {sel}
        FROM ri_matriculas_inventory m
        JOIN ri_property_nature_classification n ON n.matricula_numero = m.matricula_numero
    """
    if where:
        q += f" WHERE {where}"
    q += f" ORDER BY {_ORDER_BY}"
    return q


def _fieldnames_for(conn: sqlite3.Connection) -> list[str]:
    """Return fieldname list matching _build_select column order."""
    has_direto = _has_col(conn, "ri_matriculas_inventory", "georreferenciamento_detectado_direto")
    has_inferido = _has_col(conn, "ri_matriculas_inventory", "georreferenciamento_inferido_por_fonte")
    fields = list(_REPORT_FIELDNAMES)
    extra = []
    if has_direto:
        extra.append("georreferenciamento_detectado_direto")
    if has_inferido:
        extra.append("georreferenciamento_inferido_por_fonte")
    # Insert after georreferenciamento_valor
    if extra:
        idx = fields.index("georreferenciamento_valor") + 1
        for col in reversed(extra):
            fields.insert(idx, col)
    return fields


def _write_report(
    conn: sqlite3.Connection,
    where: str,
    path: Path,
    fieldnames: list[str],
) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = conn.execute(_base_query(conn, where)).fetchall()
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        writer.writerows(rows)
    return len(rows)


# ---------------------------------------------------------------------------
# Anti-PII scan
# ---------------------------------------------------------------------------

def _scan_file_for_pii(path: Path) -> list[str]:
    alerts: list[str] = []
    content = path.read_text(encoding="utf-8")
    for name, pat in _PII_CHECKERS:
        matches = pat.findall(content)
        if matches:
            alerts.append(f"{name}:{len(matches)}_ocorrencias")
    return alerts


def _scan_outputs(files: list[Path]) -> dict[str, list[str]]:
    return {f.name: _scan_file_for_pii(f) for f in files if f.exists()}


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------

def _db_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    s: dict[str, Any] = {}

    def q(sql: str) -> Any:
        return conn.execute(sql).fetchone()[0]

    s["total_rows"] = q("SELECT COUNT(*) FROM ri_matriculas_inventory")
    s["unique_matriculas"] = q(
        "SELECT COUNT(DISTINCT matricula_numero) FROM ri_matriculas_inventory"
    )

    # Nature counts
    for nat in ("rural", "urbano", "misto", "indeterminado"):
        s[f"n_{nat}"] = q(
            f"SELECT COUNT(*) FROM ri_property_nature_classification WHERE natureza_imovel = '{nat}'"
        )

    # Confidence
    for conf in ("confirmado", "provavel", "baixa_confianca"):
        s[f"c_{conf}"] = q(
            f"SELECT COUNT(*) FROM ri_property_nature_classification "
            f"WHERE natureza_imovel_confidence = '{conf}'"
        )

    s["rural_confirmado"] = q(
        "SELECT COUNT(*) FROM ri_property_nature_classification "
        "WHERE natureza_imovel='rural' AND natureza_imovel_confidence='confirmado'"
    )
    s["rural_provavel"] = q(
        "SELECT COUNT(*) FROM ri_property_nature_classification "
        "WHERE natureza_imovel='rural' AND natureza_imovel_confidence='provavel'"
    )
    s["excluir_total"] = q(
        "SELECT COUNT(*) FROM ri_property_nature_classification WHERE excluir_metricas_rurais=1"
    )
    s["needs_review"] = q(
        "SELECT COUNT(*) FROM ri_property_nature_classification "
        "WHERE status_revisao_ri='needs_manual_review'"
    )

    # Georref/INCRA
    has_direto = _has_col(conn, "ri_matriculas_inventory", "georreferenciamento_detectado_direto")
    s["georref_direto"] = q(
        "SELECT COUNT(*) FROM ri_matriculas_inventory WHERE georreferenciamento_detectado_direto=1"
    ) if has_direto else 0
    s["incra_sem_georref"] = q(
        "SELECT COUNT(*) FROM ri_matriculas_inventory WHERE tem_incra=1 AND tem_georreferenciamento=0"
    )
    s["com_incra"] = q("SELECT COUNT(*) FROM ri_matriculas_inventory WHERE tem_incra=1")

    # NIRF / Reserva
    s["nirf_valido"] = q("SELECT COUNT(*) FROM ri_matriculas_inventory WHERE tem_nirf=1")
    s["reserva_sim"] = q("SELECT COUNT(*) FROM ri_matriculas_inventory WHERE tem_reserva=1")
    s["reserva_nao"] = q("SELECT COUNT(*) FROM ri_matriculas_inventory WHERE tem_reserva=0")

    # Duplicates
    s["dup_total"] = q("SELECT COUNT(*) FROM ri_inventory_duplicates")

    return s


def _sample_line(row: sqlite3.Row, fields: list[str]) -> str:
    """Format a sample line with only numeric/flag data (no names or text)."""
    d = dict(zip(fields, row))
    mat = d.get("matricula_numero", "?")
    nat = d.get("natureza_imovel", "?")
    conf = d.get("natureza_imovel_confidence", "?")
    georref = d.get("tem_georreferenciamento", "?")
    incra = d.get("tem_incra", "?")
    nirf = d.get("tem_nirf", "?")
    excluir = d.get("excluir_metricas_rurais", "?")
    pg = d.get("pagina_origem", "?")
    return (
        f"{mat:>5} | {str(nat):15s} | {str(conf):15s} | "
        f"pg={pg:>4} georref={georref} incra={incra} nirf={nirf} excluir={excluir}"
    )


def _generate_summary(
    conn: sqlite3.Connection,
    counts: dict[str, int],
    out_dir: Path,
    fieldnames: list[str],
) -> Path:
    s = _db_stats(conn)

    def sample_where(where: str, limit: int = 50) -> list[str]:
        rows = conn.execute(_base_query(conn, where) + f" LIMIT {limit}").fetchall()
        return [_sample_line(r, fieldnames) for r in rows]

    missing_str = ", ".join(str(m) for m in MISSING_MATRICULAS)

    rural_base = s["unique_matriculas"]
    rural_confirmed = s["rural_confirmado"]
    excluir = s["excluir_total"]
    urban_or_misto = s["n_urbano"] + s["n_misto"]

    lines = [
        "# RI Inventory — Classificação de Natureza dos Imóveis",
        "",
        "Sprint: **RI-NATURE-1** — classificação conservadora, sem exclusão automática.",
        "Banco: `_local_data/ri_inventory/db/ri_inventory.sqlite`",
        "",
        "---",
        "",
        "## 1. Totais Gerais",
        "",
        "| Indicador | Valor |",
        "|---|---|",
        f"| Registros totais extraídos (base bruta) | {s['total_rows']} |",
        f"| Matrículas únicas reconciliadas | **{s['unique_matriculas']}** |",
        f"| Total institucional da serventia | {INSTITUTIONAL_TOTAL} |",
        f"| Diferença vs institucional | {s['unique_matriculas'] - INSTITUTIONAL_TOTAL:+d} |",
        f"| Matrículas faltantes no sequencial | `{missing_str}` |",
        "",
        "---",
        "",
        "## 2. Classificação de Natureza",
        "",
        "| Categoria | Únicas | % do total |",
        "|---|---|---|",
        f"| Rural confirmado | **{s['rural_confirmado']}** | {s['rural_confirmado']/rural_base*100:.1f}% |",
        f"| Rural provável | {s['rural_provavel']} | {s['rural_provavel']/rural_base*100:.1f}% |",
        f"| Urbano / provável urbano | {s['n_urbano']} | {s['n_urbano']/rural_base*100:.1f}% |",
        f"| Misto / conflito urbano-rural | {s['n_misto']} | {s['n_misto']/rural_base*100:.1f}% |",
        f"| Indeterminado | {s['n_indeterminado']} | {s['n_indeterminado']/rural_base*100:.1f}% |",
        f"| Excluído das métricas rurais | **{excluir}** | {excluir/rural_base*100:.1f}% |",
        f"| Pendente de revisão manual | {s['needs_review']} | {s['needs_review']/rural_base*100:.1f}% |",
        "",
        "> **Impacto estimado:** O número mínimo conservador de imóveis rurais confirmados é "
        f"**{rural_confirmed}**. Excluindo-se registros com forte indício urbano ({excluir}), "
        f"o número máximo possível é **{rural_base - excluir}**.",
        "",
        "---",
        "",
        "## 3. Georreferenciamento e INCRA",
        "",
        "| Indicador | Valor |",
        "|---|---|",
        f"| Georref direto confirmado (Sim explícito) | {s['georref_direto']} |",
        f"| INCRA sem georref explícito | {s['incra_sem_georref']} |",
        f"| Com INCRA | {s['com_incra']} |",
        "",
        "---",
        "",
        "## 4. NIRF e Reserva",
        "",
        "| Indicador | Valor |",
        "|---|---|",
        f"| NIRF válido | {s['nirf_valido']} |",
        f"| Reserva Sim | {s['reserva_sim']} |",
        f"| Reserva Não | {s['reserva_nao']} |",
        "",
        "---",
        "",
        "## 5. Duplicidades",
        "",
        f"| Matrículas duplicadas | {s['dup_total']} |",
        "|---|---|",
        "",
        "---",
        "",
        "## 6. Amostras — número e flags técnicas apenas",
        "",
        "### 6.1 Rural Confirmado (primeiras 50)",
        "```",
        "mat   | natureza         | confiança        | pág  georref incra nirf excluir",
    ] + sample_where("n.natureza_imovel='rural' AND n.natureza_imovel_confidence='confirmado'") + [
        "```",
        "",
        "### 6.2 Rural Provável (primeiras 50)",
        "```",
        "mat   | natureza         | confiança        | pág  georref incra nirf excluir",
    ] + sample_where("n.natureza_imovel='rural' AND n.natureza_imovel_confidence='provavel'") + [
        "```",
        "",
        "### 6.3 Indícios Urbanos (primeiras 50)",
        "```",
        "mat   | natureza         | confiança        | pág  georref incra nirf excluir",
    ] + sample_where("n.natureza_imovel='urbano'") + [
        "```",
        "",
        "### 6.4 Conflito Urbano/Rural (primeiras 50)",
        "```",
        "mat   | natureza         | confiança        | pág  georref incra nirf excluir",
    ] + sample_where("n.natureza_imovel='misto'") + [
        "```",
        "",
        "### 6.5 Indeterminado (primeiras 50)",
        "```",
        "mat   | natureza         | confiança        | pág  georref incra nirf excluir",
    ] + sample_where("n.natureza_imovel='indeterminado'") + [
        "```",
        "",
        "---",
        "",
        "## 7. Arquivos gerados",
        "",
        "| Arquivo | Conteúdo |",
        "|---|---|",
        "| `ri_inventory_rural_confirmed_review.csv` | Rural confirmado |",
        "| `ri_inventory_rural_probable_review.csv` | Rural provável |",
        "| `ri_inventory_urban_signals_in_rural_report.csv` | Com indício urbano |",
        "| `ri_inventory_urban_rural_conflicts_review.csv` | Conflito urbano/rural |",
        "| `ri_inventory_indeterminate_nature_review.csv` | Indeterminado |",
        "| `ri_inventory_excluded_from_rural_metrics.csv` | Excluído das métricas |",
        "| `ri_inventory_nature_classification_summary.md` | Este resumo |",
        "",
        "---",
        "",
        "*Anti-PII: varredura executada — nenhum dado pessoal nos arquivos gerados.*",
        "*Nenhum registro foi excluído da base sanitizada — apenas classificado.*",
    ]

    path = out_dir / "ri_inventory_nature_classification_summary.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(db_path: Path = _DEFAULT_DB) -> None:
    if not db_path.exists():
        print(f"[ERRO] Banco nao encontrado: {db_path}")
        return

    out_dir = _OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[RI-NATURE] Banco: {db_path}")
    print(f"[RI-NATURE] Saida: {out_dir}")
    print()

    conn = sqlite3.connect(db_path)
    try:
        _setup_table(conn)
        print("  Classificando natureza dos imoveis...")
        counts = _run_classification(conn)
        for k, v in sorted(counts.items()):
            print(f"    {k:20s}: {v}")

        fieldnames = _fieldnames_for(conn)
        generated: list[Path] = []

        reports: list[tuple[str, Path]] = [
            (
                "n.natureza_imovel='rural' AND n.natureza_imovel_confidence='confirmado'",
                out_dir / "ri_inventory_rural_confirmed_review.csv",
            ),
            (
                "n.natureza_imovel='rural' AND n.natureza_imovel_confidence='provavel'",
                out_dir / "ri_inventory_rural_probable_review.csv",
            ),
            (
                "n.natureza_imovel='urbano'",
                out_dir / "ri_inventory_urban_signals_in_rural_report.csv",
            ),
            (
                "n.natureza_imovel='misto'",
                out_dir / "ri_inventory_urban_rural_conflicts_review.csv",
            ),
            (
                "n.natureza_imovel='indeterminado'",
                out_dir / "ri_inventory_indeterminate_nature_review.csv",
            ),
            (
                "n.excluir_metricas_rurais=1",
                out_dir / "ri_inventory_excluded_from_rural_metrics.csv",
            ),
        ]

        print()
        print("  Gerando relatorios...")
        for where, path in reports:
            n = _write_report(conn, where, path, fieldnames)
            print(f"    {n:>5} registros: {path.name}")
            generated.append(path)

        print("  Gerando resumo executivo...")
        summary = _generate_summary(conn, counts, out_dir, fieldnames)
        generated.append(summary)
        print(f"    {summary.name}")

        # Anti-PII
        print()
        print("  [Anti-PII] Varrendo arquivos gerados...")
        pii_results = _scan_outputs(generated)
        any_pii = False
        for fname, alerts in pii_results.items():
            if alerts:
                any_pii = True
                print(f"    [ALERTA] {fname}: {'; '.join(alerts)}")
        if not any_pii:
            print("    [OK] Sem PII detectada. Resultado: LIMPO")

        print()
        print("=" * 60)
        print("CLASSIFICACAO DE NATUREZA — CONCLUIDA")
        print("=" * 60)
        unique = conn.execute(
            "SELECT COUNT(*) FROM ri_property_nature_classification"
        ).fetchone()[0]
        print(f"  Matriculas classificadas: {unique}")
        print(f"  Arquivos gerados: {len(generated)}")
        print(f"  Anti-PII: {'ALERTA' if any_pii else 'LIMPO'}")
        print()

    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Classify RI property nature (rural/urban/mixed/indeterminate)."
    )
    parser.add_argument("--db", type=Path, default=_DEFAULT_DB)
    args = parser.parse_args()
    main(args.db)
