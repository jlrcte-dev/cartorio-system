"""
Consulta interativa do inventário RI (Indicador Real JSON) — Cartório System

Sprint: RI-REAL-JSON-1

USO:
    # Listar rurais com CAR:
    python scripts/local_tools/query_ri_real_json_inventory.py --filter natureza=rural tem_car=true

    # Listar georreferenciados:
    python scripts/local_tools/query_ri_real_json_inventory.py --georef

    # Buscar matrícula específica:
    python scripts/local_tools/query_ri_real_json_inventory.py --matricula 381

    # Resumo geral:
    python scripts/local_tools/query_ri_real_json_inventory.py --summary

    # Needs review:
    python scripts/local_tools/query_ri_real_json_inventory.py --needs-review

PROTEÇÃO DE DADOS:
    Apenas campos sanitizados são exibidos. CONTRIBUINTE nunca é exibido.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "_local_data" / "ri_inventory" / "db" / "ri_inventory.sqlite"

# Campos que podem ser exibidos — nunca incluir CONTRIBUINTE ou dados pessoais
_SAFE_DISPLAY_FIELDS = [
    "matricula_numero",
    "numero_registro",
    "natureza_imovel",
    "tem_car",
    "tem_nirf",
    "nirf_status",
    "tem_ccir",
    "tem_numero_incra",
    "tem_sigef",
    "possui_georreferenciamento",
    "georreferenciamento_criterio",
    "status_extracao",
    "status_revisao_ri",
    "observacoes_tecnicas_sem_pii",
]

_SUMMARY_SQL = """
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN natureza_imovel='urbano' THEN 1 ELSE 0 END) AS urbanos,
    SUM(CASE WHEN natureza_imovel='rural' THEN 1 ELSE 0 END) AS rurais,
    SUM(CASE WHEN natureza_imovel='indeterminado' THEN 1 ELSE 0 END) AS indeterminados,
    SUM(CASE WHEN natureza_imovel='rural' AND tem_car=1 THEN 1 ELSE 0 END) AS rurais_car,
    SUM(CASE WHEN natureza_imovel='rural' AND tem_nirf=1 THEN 1 ELSE 0 END) AS rurais_nirf,
    SUM(CASE WHEN natureza_imovel='rural' AND tem_ccir=1 THEN 1 ELSE 0 END) AS rurais_ccir,
    SUM(CASE WHEN natureza_imovel='rural' AND tem_numero_incra=1 THEN 1 ELSE 0 END) AS rurais_incra,
    SUM(CASE WHEN natureza_imovel='rural' AND tem_sigef=1 THEN 1 ELSE 0 END) AS rurais_sigef,
    SUM(CASE WHEN possui_georreferenciamento=1 THEN 1 ELSE 0 END) AS georef,
    SUM(CASE WHEN status_revisao_ri='needs_manual_review' THEN 1 ELSE 0 END) AS needs_review
FROM ri_real_json_inventory
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        print(f"[ERRO] Banco não encontrado: {db_path}", file=sys.stderr)
        print("[DICA] Execute primeiro: python scripts/local_tools/analyze_ri_real_json.py --write-db", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def cmd_summary(conn: sqlite3.Connection) -> None:
    row = conn.execute(_SUMMARY_SQL).fetchone()
    if not row:
        print("Sem dados.")
        return
    print("\n=== RESUMO DO INVENTÁRIO RI (SQLite) ===")
    print(f"  Total registros        : {row['total']}")
    print(f"  Urbanos                : {row['urbanos']}")
    print(f"  Rurais                 : {row['rurais']}")
    print(f"  Indeterminados         : {row['indeterminados']}")
    print(f"  Rurais com CAR         : {row['rurais_car']}")
    print(f"  Rurais com NIRF válido : {row['rurais_nirf']}")
    print(f"  Rurais com CCIR        : {row['rurais_ccir']}")
    print(f"  Rurais com INCRA       : {row['rurais_incra']}")
    print(f"  Rurais com SIGEF       : {row['rurais_sigef']}")
    print(f"  Com georreferenciamento: {row['georef']}")
    print(f"  Needs review           : {row['needs_review']}")


def _print_rows(rows: list[sqlite3.Row], limit: int = 50) -> None:
    if not rows:
        print("Nenhum registro encontrado.")
        return
    print(f"\n{len(rows)} registro(s) encontrado(s).")
    for i, row in enumerate(rows[:limit]):
        parts = [f"Mat={row['matricula_numero']}", f"NR={row['numero_registro']}"]
        for f in _SAFE_DISPLAY_FIELDS[2:]:
            v = row[f]
            if v not in (None, "", 0, "0", False, "ok"):
                parts.append(f"{f}={v}")
        print("  " + " | ".join(parts))
    if len(rows) > limit:
        print(f"  ... (+{len(rows) - limit} não exibidos)")


def cmd_georef(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT * FROM ri_real_json_inventory WHERE possui_georreferenciamento=1 ORDER BY matricula_numero"
    ).fetchall()
    print("\n=== GEORREFERENCIADOS ===")
    _print_rows(rows)


def cmd_needs_review(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT * FROM ri_real_json_inventory WHERE status_revisao_ri='needs_manual_review' ORDER BY matricula_numero"
    ).fetchall()
    print("\n=== NEEDS REVIEW ===")
    _print_rows(rows)


def cmd_matricula(conn: sqlite3.Connection, matricula: int) -> None:
    rows = conn.execute(
        "SELECT * FROM ri_real_json_inventory WHERE matricula_numero=?", (matricula,)
    ).fetchall()
    print(f"\n=== MATRÍCULA {matricula} ===")
    _print_rows(rows)


def cmd_filter(conn: sqlite3.Connection, filters: list[str]) -> None:
    """Filtros simples: campo=valor, ex: natureza=rural tem_car=true"""
    where_parts = []
    params = []
    for f in filters:
        if "=" not in f:
            print(f"[AVISO] Filtro inválido ignorado: {f}")
            continue
        col, val = f.split("=", 1)
        col = col.strip().lower()
        val = val.strip().lower()
        # Validar que coluna é segura
        if col not in _SAFE_DISPLAY_FIELDS + ["cns", "livro", "natureza_imovel",
                                               "natureza_imovel_confidence", "nirf_status",
                                               "localizacao_codigo"]:
            print(f"[AVISO] Coluna não permitida para filtro: {col}")
            continue
        # Converter bool
        if val in ("true", "1", "sim"):
            val = "1"
        elif val in ("false", "0", "nao", "não"):
            val = "0"
        where_parts.append(f"{col}=?")
        params.append(val)

    if not where_parts:
        print("[ERRO] Nenhum filtro válido.")
        return

    sql = f"SELECT * FROM ri_real_json_inventory WHERE {' AND '.join(where_parts)} ORDER BY matricula_numero"
    rows = conn.execute(sql, params).fetchall()
    print(f"\n=== FILTRO: {', '.join(filters)} ===")
    _print_rows(rows)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Consulta o inventário RI (Indicador Real JSON)")
    p.add_argument("--db", default=str(DB_PATH), help="Caminho para o SQLite")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--summary", action="store_true", help="Resumo geral")
    g.add_argument("--georef", action="store_true", help="Listar georreferenciados")
    g.add_argument("--needs-review", action="store_true", help="Listar needs_manual_review")
    g.add_argument("--matricula", type=int, help="Buscar matrícula específica")
    g.add_argument("--filter", nargs="+", metavar="campo=valor", help="Filtros (ex: natureza=rural tem_car=true)")
    return p


if __name__ == "__main__":
    args = _build_parser().parse_args()
    db_path = Path(args.db)
    conn = _connect(db_path)

    try:
        if args.summary:
            cmd_summary(conn)
        elif args.georef:
            cmd_georef(conn)
        elif args.needs_review:
            cmd_needs_review(conn)
        elif args.matricula is not None:
            cmd_matricula(conn, args.matricula)
        elif args.filter:
            cmd_filter(conn, args.filter)
    finally:
        conn.close()
