"""
Auditoria de reconciliação do inventário de matrículas rurais.

Compara contagens entre CSV, JSON e SQLite; explica divergências; lista
matrículas faltantes e classifica duplicidades.

LGPD: Apenas métricas agregadas e números de matrícula são processados e
exibidos. Nenhum nome, CPF, CNPJ ou dado pessoal é lido, armazenado ou
impresso neste script.

USO:
    python scripts/local_tools/audit_ri_inventory_reconciliation.py
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[2]
LOCAL_DATA = BASE_DIR / "_local_data"
SANITIZED_DIR = LOCAL_DATA / "ri_inventory" / "sanitized"
REPORTS_DIR = LOCAL_DATA / "ri_inventory" / "reports"
DB_PATH = LOCAL_DATA / "ri_inventory" / "db" / "ri_inventory.sqlite"

_TOTAL_GERAL_SERVENTIA = 3523

# Campos técnicos usados para comparação de duplicatas (sem PII)
_CAMPOS_TECNICOS = [
    "nome_imovel_sanitizado",
    "municipio",
    "area_texto_original",
    "area_valor_normalizado",
    "tem_georreferenciamento",
    "georreferenciamento_detectado_direto",
    "georreferenciamento_inferido_por_fonte",
    "georreferenciamento_valor",
    "tem_incra",
    "incra_codigo",
    "tem_nirf",
    "nirf_codigo",
    "tem_reserva",
    "reserva_valor",
]

# Padrões PII para varredura de relatórios
_CPF_RE = re.compile(r"\d{3}[\.\s]?\d{3}[\.\s]?\d{3}[\-\.\s]?\d{2}")
_CNPJ_RE = re.compile(r"\d{2}[\.\s]?\d{3}[\.\s]?\d{3}[\.\s\/]?\d{4}[\-\.\s]?\d{2}")


# ---------------------------------------------------------------------------
# Leitura das fontes de dados
# ---------------------------------------------------------------------------

def _count_csv(path: Path) -> int:
    if not path.exists():
        return -1
    with path.open(encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in csv.DictReader(f))


def _count_json(path: Path) -> int:
    if not path.exists():
        return -1
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return len(data) if isinstance(data, list) else -1
    except Exception:
        return -1


def _matriculas_from_csv(path: Path) -> list[int]:
    if not path.exists():
        return []
    result = []
    with path.open(encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            try:
                result.append(int(row.get("matricula_numero", "")))
            except (ValueError, TypeError):
                pass
    return result


# ---------------------------------------------------------------------------
# Consultas SQLite
# ---------------------------------------------------------------------------

def _db_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    """Retorna estatísticas agregadas do SQLite — sem PII."""
    stats: dict[str, Any] = {}

    # Totais por fonte
    for row in conn.execute(
        "SELECT fonte_relatorio, COUNT(*) as n FROM ri_matriculas_inventory "
        "GROUP BY fonte_relatorio"
    ):
        stats[f"sqlite_{row[0]}"] = row[1]

    stats["sqlite_total"] = conn.execute(
        "SELECT COUNT(*) FROM ri_matriculas_inventory"
    ).fetchone()[0]

    stats["sqlite_unicos"] = conn.execute(
        "SELECT COUNT(DISTINCT matricula_numero) FROM ri_matriculas_inventory"
    ).fetchone()[0]

    stats["sqlite_min"] = conn.execute(
        "SELECT MIN(matricula_numero) FROM ri_matriculas_inventory"
    ).fetchone()[0]

    stats["sqlite_max"] = conn.execute(
        "SELECT MAX(matricula_numero) FROM ri_matriculas_inventory"
    ).fetchone()[0]

    # Georreferenciamento — separado por tipo
    has_direto_col = _has_column(conn, "georreferenciamento_detectado_direto")
    has_fonte_col = _has_column(conn, "georreferenciamento_inferido_por_fonte")

    stats["georref_total"] = conn.execute(
        "SELECT COUNT(*) FROM ri_matriculas_inventory WHERE tem_georreferenciamento=1"
    ).fetchone()[0]

    if has_direto_col:
        stats["georref_direto"] = conn.execute(
            "SELECT COUNT(*) FROM ri_matriculas_inventory "
            "WHERE georreferenciamento_detectado_direto=1"
        ).fetchone()[0]
    else:
        stats["georref_direto"] = None  # campo não existe nesta versão do schema

    if has_fonte_col:
        stats["georref_inferido_fonte"] = conn.execute(
            "SELECT COUNT(*) FROM ri_matriculas_inventory "
            "WHERE georreferenciamento_inferido_por_fonte=1"
        ).fetchone()[0]
    else:
        stats["georref_inferido_fonte"] = None

    # INCRA com e sem Georef
    stats["incra_total"] = conn.execute(
        "SELECT COUNT(*) FROM ri_matriculas_inventory WHERE tem_incra=1"
    ).fetchone()[0]

    if has_direto_col and has_fonte_col:
        stats["incra_sem_georref_explicito"] = conn.execute(
            "SELECT COUNT(*) FROM ri_matriculas_inventory "
            "WHERE tem_incra=1 AND georreferenciamento_detectado_direto=0 "
            "AND georreferenciamento_inferido_por_fonte=0"
        ).fetchone()[0]
    else:
        stats["incra_sem_georref_explicito"] = None

    # NIRF
    stats["nirf_valido"] = conn.execute(
        "SELECT COUNT(*) FROM ri_matriculas_inventory WHERE tem_nirf=1"
    ).fetchone()[0]

    stats["nirf_zerado"] = conn.execute(
        "SELECT COUNT(*) FROM ri_matriculas_inventory "
        "WHERE observacoes_tecnicas_sem_pii LIKE '%nirf_zerado_ignorado%'"
    ).fetchone()[0]

    stats["nirf_ambiguo"] = conn.execute(
        "SELECT COUNT(*) FROM ri_matriculas_inventory "
        "WHERE observacoes_tecnicas_sem_pii LIKE '%nirf_ambiguo%'"
    ).fetchone()[0]

    # Reserva
    stats["reserva_sim"] = conn.execute(
        "SELECT COUNT(*) FROM ri_matriculas_inventory WHERE reserva_valor='Sim'"
    ).fetchone()[0]

    stats["reserva_nao"] = conn.execute(
        "SELECT COUNT(*) FROM ri_matriculas_inventory WHERE reserva_valor='Não'"
    ).fetchone()[0]

    # Área
    stats["com_area"] = conn.execute(
        "SELECT COUNT(*) FROM ri_matriculas_inventory "
        "WHERE area_valor_normalizado IS NOT NULL"
    ).fetchone()[0]

    # needs_review
    stats["needs_review"] = conn.execute(
        "SELECT COUNT(*) FROM ri_matriculas_inventory WHERE status_extracao='needs_review'"
    ).fetchone()[0]

    # Duplicidades na tabela de controle
    stats["duplicatas_registradas"] = conn.execute(
        "SELECT COUNT(*) FROM ri_inventory_duplicates"
    ).fetchone()[0]

    return stats


def _has_column(conn: sqlite3.Connection, col: str) -> bool:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(ri_matriculas_inventory)")}
    return col in existing


def _find_missing_matriculas(conn: sqlite3.Connection) -> list[int]:
    """Lista matrículas ausentes entre 1 e 3523 — apenas números."""
    all_nums = {
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT matricula_numero FROM ri_matriculas_inventory"
        )
    }
    expected = set(range(1, _TOTAL_GERAL_SERVENTIA + 1))
    return sorted(expected - all_nums)


def _classify_duplicates(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """
    Classifica duplicidades por matrícula (apenas campos técnicos).
    Sem exposição de nomes ou documentos pessoais.
    """
    dup_nums = [
        row[0]
        for row in conn.execute(
            """
            SELECT matricula_numero FROM ri_matriculas_inventory
            GROUP BY matricula_numero HAVING COUNT(*) > 1
            ORDER BY matricula_numero
            """
        )
    ]

    results = []
    for num in dup_nums:
        rows = conn.execute(
            """
            SELECT hash_bloco_origem, fonte_relatorio, pagina_origem,
                   nome_imovel_sanitizado, municipio,
                   area_texto_original, area_valor_normalizado,
                   tem_georreferenciamento, georreferenciamento_valor,
                   tem_incra, incra_codigo,
                   tem_nirf, nirf_codigo,
                   tem_reserva, reserva_valor
            FROM ri_matriculas_inventory
            WHERE matricula_numero = ?
            ORDER BY id
            """,
            (num,),
        ).fetchall()

        hashes = [r[0] for r in rows]
        fontes = list({r[1] for r in rows})
        paginas = [r[2] for r in rows]
        n = len(rows)

        # Comparar campos técnicos entre as ocorrências (excluindo hash e fonte)
        tecnicos = [r[3:] for r in rows]  # tudo exceto hash, fonte, página
        todos_iguais = all(t == tecnicos[0] for t in tecnicos[1:])
        hashes_unicos = len(set(hashes))

        if hashes_unicos == 1:
            classificacao = "EXACT_DUPLICATE"
            tem_diferenca = False
            campos_diff = []
        elif todos_iguais:
            classificacao = "TECHNICAL_DUPLICATE"
            tem_diferenca = False
            campos_diff = []
        else:
            # Identificar quais campos técnicos diferem (sem PII)
            campos_nomes = [
                "nome_imovel_sanitizado", "municipio",
                "area_texto_original", "area_valor_normalizado",
                "tem_georreferenciamento", "georreferenciamento_valor",
                "tem_incra", "incra_codigo",
                "tem_nirf", "nirf_codigo",
                "tem_reserva", "reserva_valor",
            ]
            campos_diff = []
            for i, campo in enumerate(campos_nomes):
                # Pular campos com dados pessoais (nome_imovel pode ter conteúdo)
                if campo == "nome_imovel_sanitizado":
                    # Registrar apenas SE DIFERE, sem expor o valor
                    valores = {t[i] for t in tecnicos}
                    if len(valores) > 1:
                        campos_diff.append("nome_imovel_sanitizado")
                else:
                    valores = {t[i] for t in tecnicos}
                    if len(valores) > 1:
                        campos_diff.append(campo)

            if campos_diff:
                classificacao = "CONFLICT_DUPLICATE"
                tem_diferenca = True
            else:
                classificacao = "NEEDS_MANUAL_REVIEW"
                tem_diferenca = False

        results.append({
            "matricula_numero": num,
            "ocorrencias": n,
            "fontes": fontes,
            "hashes_distintos": hashes_unicos,
            "paginas": paginas,
            "tem_diferenca_tecnica": tem_diferenca,
            "campos_tecnicos_diferentes": campos_diff,
            "classificacao": classificacao,
        })

    return results


# ---------------------------------------------------------------------------
# Análise de totais no PDF (via runs table)
# ---------------------------------------------------------------------------

def _get_runs_info(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT fonte_relatorio, total_reportado, total_blocos_detectados,
               total_registros_sanitizados, total_duplicidades, started_at
        FROM ri_inventory_runs
        ORDER BY id
        """
    ).fetchall()
    return [
        {
            "fonte": r[0],
            "total_reportado": r[1],
            "total_blocos": r[2],
            "total_sanitizados": r[3],
            "total_dups": r[4],
            "started_at": r[5],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Varredura anti-PII do relatório gerado
# ---------------------------------------------------------------------------

def _scan_report_for_pii(text: str) -> list[str]:
    """Varre texto de relatório por padrões CPF/CNPJ. Retorna lista de alertas."""
    alerts = []
    for i, line in enumerate(text.splitlines(), 1):
        if _CPF_RE.search(line):
            alerts.append(f"linha {i}: padrão CPF detectado")
        if _CNPJ_RE.search(line):
            alerts.append(f"linha {i}: padrão CNPJ detectado")
    return alerts


# ---------------------------------------------------------------------------
# Geração do relatório de reconciliação
# ---------------------------------------------------------------------------

def _generate_reconciliation_report(
    csv_rural: int,
    json_rural: int,
    csv_georref: int,
    json_georref: int,
    db_stats: dict[str, Any],
    missing: list[int],
    duplicates: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    run_ts: str,
) -> str:

    sqlite_rural = db_stats.get("sqlite_Relatorio_matriculas_rurais.pdf", "?")
    sqlite_georref = db_stats.get(
        "sqlite_Relatorio_matriculas_rurais_georrefrenciadas.pdf", "?"
    )
    # Também pode ter a versão com nome correto
    if sqlite_georref == "?":
        sqlite_georref = db_stats.get(
            "sqlite_Relatorio_matriculas_rurais_georreferenciadas.pdf", "?"
        )
    sqlite_total = db_stats.get("sqlite_total", "?")
    sqlite_unicos = db_stats.get("sqlite_unicos", "?")
    sqlite_min = db_stats.get("sqlite_min", "?")
    sqlite_max = db_stats.get("sqlite_max", "?")

    # Diferenças
    diff_rural_csv_json = (
        f"{csv_rural} == {json_rural} ✓"
        if csv_rural == json_rural
        else f"DIVERGÊNCIA: CSV={csv_rural}, JSON={json_rural}"
    )
    diff_georref_csv_json = (
        f"{csv_georref} == {json_georref} ✓"
        if csv_georref == json_georref
        else f"DIVERGÊNCIA: CSV={csv_georref}, JSON={json_georref}"
    )

    # Diferença CSV→SQLite = exact-match rejeitados por UNIQUE
    diff_rural_sqlite = (
        (csv_rural - sqlite_rural) if isinstance(sqlite_rural, int) and csv_rural > 0 else "?"
    )
    diff_georref_sqlite = (
        (csv_georref - sqlite_georref)
        if isinstance(sqlite_georref, int) and csv_georref > 0
        else "?"
    )

    # Explicação da divergência 3.582 vs 3.552
    expl_rural = (
        f"CSV/JSON={csv_rural} → SQLite={sqlite_rural} "
        f"(diferença={diff_rural_sqlite}: exact-match rejeitados por UNIQUE constraint)"
        if isinstance(diff_rural_sqlite, int)
        else "—"
    )
    expl_georref = (
        f"CSV/JSON={csv_georref} → SQLite={sqlite_georref} "
        f"(diferença={diff_georref_sqlite}: exact-match rejeitados por UNIQUE constraint)"
        if isinstance(diff_georref_sqlite, int)
        else "—"
    )

    # Matrículas faltantes
    missing_str = ", ".join(str(m) for m in missing) if missing else "Nenhuma"
    diff_serventia = (
        _TOTAL_GERAL_SERVENTIA - sqlite_unicos
        if isinstance(sqlite_unicos, int)
        else "?"
    )

    # Duplicidades: contagem por classificação
    dup_counts: dict[str, int] = {}
    for d in duplicates:
        c = d["classificacao"]
        dup_counts[c] = dup_counts.get(c, 0) + 1

    dup_table_rows = "\n".join(
        f"| {d['matricula_numero']} | {d['ocorrencias']} | "
        f"{';'.join(d['fontes'])} | {d['hashes_distintos']} | "
        f"{';'.join(d['paginas'] and [str(p) for p in d['paginas'][:3]] or ['?'])} | "
        f"{'Sim' if d['tem_diferenca_tecnica'] else 'Não'} | "
        f"{','.join(d['campos_tecnicos_diferentes']) if d['campos_tecnicos_diferentes'] else '—'} | "
        f"{d['classificacao']} |"
        for d in duplicates[:50]
    )
    if len(duplicates) > 50:
        dup_table_rows += f"\n| ... | ... | {len(duplicates)-50} registros adicionais | | | | | |"

    # Runs info
    runs_rows = "\n".join(
        f"| {r['fonte']} | {r['total_reportado']} | "
        f"{r['total_blocos']} | {r['total_sanitizados']} | {r['total_dups']} |"
        for r in runs
    )

    # Flags por fonte (do DB)
    georref_direto = db_stats.get("georref_direto")
    georref_direto_str = str(georref_direto) if georref_direto is not None else "campo não existe (DB pré-v3)"
    georref_fonte = db_stats.get("georref_inferido_fonte")
    georref_fonte_str = str(georref_fonte) if georref_fonte is not None else "campo não existe (DB pré-v3)"
    incra_sem = db_stats.get("incra_sem_georref_explicito")
    incra_sem_str = str(incra_sem) if incra_sem is not None else "campo não existe (DB pré-v3)"

    return f"""# Relatório de Reconciliação — Inventário de Matrículas Rurais
## Cartório Costa Teixeira — Terezópolis de Goiás

**Gerado em:** {run_ts}
**Script:** scripts/local_tools/audit_ri_inventory_reconciliation.py
**Classificação:** USO INTERNO — NÃO VERSIONAR

---

## 1. Totais por fonte de dados

| Fonte | CSV | JSON | SQLite |
|---|---|---|---|
| Relatório Rural | {csv_rural} | {json_rural} | {sqlite_rural} |
| Relatório Georref | {csv_georref} | {json_georref} | {sqlite_georref} |
| **TOTAL** | **{csv_rural+csv_georref if csv_rural > 0 and csv_georref > 0 else '?'}** | **{json_rural+json_georref if json_rural > 0 and json_georref > 0 else '?'}** | **{sqlite_total}** |

---

## 2. Divergências explicadas

### 2.1 CSV vs JSON
- Rural: {diff_rural_csv_json}
- Georref: {diff_georref_csv_json}

> CSV e JSON são gerados no mesmo momento da extração a partir do mesmo
> conjunto de registros, portanto devem sempre ser iguais.

### 2.2 CSV/JSON vs SQLite — Explicação da divergência

- Rural: {expl_rural}
- Georref: {expl_georref}

> **Causa**: a tabela SQLite tem uma constraint `UNIQUE(fonte_relatorio,
> matricula_numero, hash_bloco_origem)`. Quando o mesmo bloco (mesma fonte,
> mesma matrícula, mesmo hash de conteúdo) é reinserido, a instrução
> `INSERT OR IGNORE` silenciosamente descarta o registro duplicado.
> Esse comportamento é esperado e não indica perda de dado — significa que
> o mesmo bloco aparece mais de uma vez no PDF (páginas sobrepostas ou
> relação de dados repetida).

### 2.3 Total geral da serventia vs matrículas únicas no SQLite

| Indicador | Valor |
|---|---|
| Total geral da serventia (institucional) | {_TOTAL_GERAL_SERVENTIA} |
| Matrículas únicas no SQLite | {sqlite_unicos} |
| Diferença | {diff_serventia} |
| Menor matrícula | {sqlite_min} |
| Maior matrícula | {sqlite_max} |

---

## 3. Matrículas faltantes (entre 1 e {_TOTAL_GERAL_SERVENTIA})

**Quantidade:** {len(missing)}

**Lista (apenas números):** {missing_str}

> Hipóteses para ausência:
> - A matrícula pode estar em outro lote do PDF não processado.
> - A matrícula pode ter número diferente do sequencial (ex: matrícula de
>   imóvel urbano ou de outra circunscrição incluída no relatório).
> - O bloco pode ter formato não reconhecido pelo parser (tipo T, letra
>   diferente, linha corrompida).
> - A matrícula pode não existir (número reservado, cancelado ou ainda
>   não aberto).
> **Recomendação:** confirmar com equipe do RI via consulta ao Engegraph.

---

## 4. Flags e estatísticas — banco SQLite

### 4.1 Georreferenciamento (separação semântica v3)

| Indicador | Quantidade |
|---|---|
| Georref. total (direto + inferido) | {db_stats.get('georref_total', '?')} |
| Georref. detectado direto (Sim explícito em Georef.) | {georref_direto_str} |
| Georref. inferido por fonte (relatório georref) | {georref_fonte_str} |
| INCRA total | {db_stats.get('incra_total', '?')} |
| INCRA sem Georef. explícito | {incra_sem_str} |

### 4.2 NIRF

| Indicador | Quantidade |
|---|---|
| NIRF válido detectado | {db_stats.get('nirf_valido', '?')} |
| NIRF zerado/placeholder ignorado | {db_stats.get('nirf_zerado', '?')} |
| NIRF ambíguo | {db_stats.get('nirf_ambiguo', '?')} |
| NIRF ausente | {db_stats.get('sqlite_total', 0) - db_stats.get('nirf_valido', 0) - db_stats.get('nirf_zerado', 0) - db_stats.get('nirf_ambiguo', 0)} |

### 4.3 Outros campos

| Indicador | Quantidade |
|---|---|
| Reserva Sim | {db_stats.get('reserva_sim', '?')} |
| Reserva Não | {db_stats.get('reserva_nao', '?')} |
| Reserva não informada | {db_stats.get('sqlite_total', 0) - db_stats.get('reserva_sim', 0) - db_stats.get('reserva_nao', 0)} |
| Com área extraída | {db_stats.get('com_area', '?')} |
| needs_review | {db_stats.get('needs_review', '?')} |

---

## 5. Histórico de runs (ri_inventory_runs)

| Fonte | Total reportado | Blocos | Sanitizados | Duplicidades |
|---|---|---|---|---|
{runs_rows if runs_rows else "| (nenhum run registrado) | | | | |"}

> **Nota sobre 'Total reportado'**: O valor detectado no PDF rural é um
> **subtotal repetido por página/lote**, não o total global do relatório.
> Isso é evidenciado pela discrepância entre o valor detectado e o número
> real de registros extraídos. O total institucional da serventia é
> {_TOTAL_GERAL_SERVENTIA} matrículas.

---

## 6. Duplicidades classificadas

**Total de matrículas duplicadas:** {len(duplicates)}

| Classificação | Quantidade |
|---|---|
| EXACT_DUPLICATE (mesmo hash) | {dup_counts.get('EXACT_DUPLICATE', 0)} |
| TECHNICAL_DUPLICATE (mesmos campos técnicos, hash diferente) | {dup_counts.get('TECHNICAL_DUPLICATE', 0)} |
| CONFLICT_DUPLICATE (campos técnicos divergentes) | {dup_counts.get('CONFLICT_DUPLICATE', 0)} |
| NEEDS_MANUAL_REVIEW | {dup_counts.get('NEEDS_MANUAL_REVIEW', 0)} |

### Detalhamento (matrícula, ocorrências, classificação)

| Matrícula | N | Fontes | Hashes | Páginas | Diferença técnica | Campos | Classificação |
|---|---|---|---|---|---|---|---|
{dup_table_rows if dup_table_rows else "| (nenhuma) | | | | | | | |"}

> **Legenda:**
> - EXACT_DUPLICATE: mesmo bloco idêntico (hash igual) — rejeitado por UNIQUE no SQLite.
> - TECHNICAL_DUPLICATE: mesma matrícula, mesmos dados técnicos, hash diferente (bloco
>   levemente diferente no PDF mas equivalente).
> - CONFLICT_DUPLICATE: mesma matrícula com dados técnicos divergentes — requer revisão.
> - NEEDS_MANUAL_REVIEW: não foi possível classificar com segurança.

---

## 7. Alertas

"""


def _build_alertas(
    csv_rural: int, csv_georref: int,
    db_stats: dict[str, Any],
    missing: list[int],
    duplicates: list[dict[str, Any]],
) -> list[str]:
    alertas = []

    sqlite_unicos = db_stats.get("sqlite_unicos", 0)
    if isinstance(sqlite_unicos, int):
        if sqlite_unicos > _TOTAL_GERAL_SERVENTIA:
            alertas.append(
                f"ALERTA CRÍTICO: {sqlite_unicos} matrículas únicas no SQLite > "
                f"{_TOTAL_GERAL_SERVENTIA} (total geral da serventia) — reconciliar com RI"
            )
        elif sqlite_unicos < _TOTAL_GERAL_SERVENTIA:
            diff = _TOTAL_GERAL_SERVENTIA - sqlite_unicos
            alertas.append(
                f"AVISO: {sqlite_unicos} matrículas únicas no SQLite < "
                f"{_TOTAL_GERAL_SERVENTIA} (faltam {diff} — ver seção 3)"
            )

    if len(missing) > 0:
        alertas.append(
            f"AVISO: {len(missing)} matrículas faltantes entre 1 e "
            f"{_TOTAL_GERAL_SERVENTIA}: {missing}"
        )

    conflicts = [d for d in duplicates if d["classificacao"] == "CONFLICT_DUPLICATE"]
    if conflicts:
        nums = [str(d["matricula_numero"]) for d in conflicts[:10]]
        alertas.append(
            f"ATENÇÃO: {len(conflicts)} CONFLICT_DUPLICATE — matrículas com dados "
            f"técnicos divergentes: {', '.join(nums)}"
        )

    if db_stats.get("nirf_valido", 0) == 0:
        alertas.append(
            "CONFIRMAÇÃO PENDENTE: NIRF=0 em toda a base — confirmar com equipe do RI "
            "se há imóveis com NIRF preenchido no sistema Engegraph"
        )

    if db_stats.get("reserva_sim", 0) == 0:
        alertas.append(
            "CONFIRMAÇÃO PENDENTE: Reserva Sim=0 em toda a base — confirmar com equipe do RI "
            "se há reservas legais registradas"
        )

    georref_direto = db_stats.get("georref_direto")
    incra_total = db_stats.get("incra_total", 0)
    if georref_direto is not None and isinstance(incra_total, int):
        if incra_total > georref_direto:
            alertas.append(
                f"INFO: {incra_total} registros com INCRA mas apenas {georref_direto} "
                f"com Georef. Sim explícito — INCRA não implica georreferenciamento confirmado"
            )

    return alertas


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("[INFO] Iniciando auditoria de reconciliação...")

    if not DB_PATH.exists():
        print(f"[ERRO] Banco SQLite não encontrado: {DB_PATH}", file=__import__("sys").stderr)
        __import__("sys").exit(1)

    # Contar CSV/JSON
    csv_rural = _count_csv(SANITIZED_DIR / "ri_rural_inventory_rural_sanitized.csv")
    json_rural = _count_json(SANITIZED_DIR / "ri_rural_inventory_rural_sanitized.json")
    csv_georref = _count_csv(SANITIZED_DIR / "ri_rural_inventory_georref_sanitized.csv")
    json_georref = _count_json(SANITIZED_DIR / "ri_rural_inventory_georref_sanitized.json")

    print(f"  CSV rural: {csv_rural}, JSON rural: {json_rural}")
    print(f"  CSV georref: {csv_georref}, JSON georref: {json_georref}")

    # Consultar SQLite
    conn = sqlite3.connect(str(DB_PATH))
    try:
        stats = _db_stats(conn)
        missing = _find_missing_matriculas(conn)
        duplicates = _classify_duplicates(conn)
        runs = _get_runs_info(conn)
    finally:
        conn.close()

    print(f"  SQLite total: {stats.get('sqlite_total')}")
    print(f"  Matrículas faltantes: {len(missing)}")
    print(f"  Matrículas duplicadas: {len(duplicates)}")

    run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    report = _generate_reconciliation_report(
        csv_rural=csv_rural,
        json_rural=json_rural,
        csv_georref=csv_georref,
        json_georref=json_georref,
        db_stats=stats,
        missing=missing,
        duplicates=duplicates,
        runs=runs,
        run_ts=run_ts,
    )

    # Adicionar alertas
    alertas = _build_alertas(csv_rural, csv_georref, stats, missing, duplicates)
    if alertas:
        report += "\n".join(f"- {a}" for a in alertas) + "\n"
    else:
        report += "- Nenhum alerta crítico detectado.\n"

    report += """
---

## 8. Confirmação de proteção de dados

- Nenhum nome de proprietário foi lido, processado ou impresso.
- Nenhum CPF, CNPJ ou RG foi processado ou salvo.
- Apenas números de matrícula e métricas técnicas estão neste relatório.
- Os PDFs brutos permanecem em `_local_data/ri_inventory/raw/`.

---

## 9. Próximos passos recomendados

1. Validar matrículas faltantes com equipe do RI via Engegraph.
2. Investigar CONFLICT_DUPLICATE: mesma matrícula com dados técnicos divergentes.
3. Confirmar NIRF e Reserva Sim com equipe do RI (possível falso negativo de parsing).
4. Cruzar georreferenciados detectados com consulta ao SIGEF.
5. Após validação, os dados podem alimentar o Relatório Diagnóstico v2.0.

*Relatório gerado automaticamente — uso restrito à equipe técnica da serventia.*
"""

    # Varredura anti-PII do relatório
    pii_alerts = _scan_report_for_pii(report)
    if pii_alerts:
        print("[ERRO] PII detectada no relatório gerado — NÃO SALVO.", file=__import__("sys").stderr)
        for a in pii_alerts:
            print(f"  {a}", file=__import__("sys").stderr)
        __import__("sys").exit(1)

    # Salvar relatório
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "ri_inventory_reconciliation.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"[OK] Relatório: {report_path}")

    # Relatório de duplicidades detalhado
    dup_report = _generate_duplicates_report(duplicates, run_ts)
    dup_report_path = REPORTS_DIR / "ri_inventory_duplicates_audit.md"
    dup_report_path.write_text(dup_report, encoding="utf-8")
    print(f"[OK] Relatório de duplicidades: {dup_report_path}")

    print("\n[AUDITORIA CONCLUÍDA]")
    print(f"  Matrículas faltantes: {len(missing)} — {sorted(missing)}")
    print(f"  Duplicidades classificadas: {len(duplicates)}")
    print("  Anti-PII: LIMPO")


def _generate_duplicates_report(
    duplicates: list[dict[str, Any]], run_ts: str
) -> str:
    dup_counts: dict[str, int] = {}
    for d in duplicates:
        c = d["classificacao"]
        dup_counts[c] = dup_counts.get(c, 0) + 1

    rows = []
    for d in duplicates:
        rows.append(
            f"| {d['matricula_numero']} | {d['ocorrencias']} | "
            f"{';'.join(d['fontes'])} | {d['hashes_distintos']} | "
            f"{';'.join(str(p) for p in (d['paginas'] or [])[:4])} | "
            f"{'Sim' if d['tem_diferenca_tecnica'] else 'Não'} | "
            f"{','.join(d['campos_tecnicos_diferentes']) or '—'} | "
            f"{d['classificacao']} |"
        )

    rows_str = "\n".join(rows) if rows else "| (nenhuma) | | | | | | | |"

    return f"""# Auditoria de Duplicidades — Inventário de Matrículas Rurais
## Cartório Costa Teixeira — Terezópolis de Goiás

**Gerado em:** {run_ts}
**Classificação:** USO INTERNO — NÃO VERSIONAR

---

## Resumo

| Classificação | Quantidade |
|---|---|
| EXACT_DUPLICATE | {dup_counts.get('EXACT_DUPLICATE', 0)} |
| TECHNICAL_DUPLICATE | {dup_counts.get('TECHNICAL_DUPLICATE', 0)} |
| CONFLICT_DUPLICATE | {dup_counts.get('CONFLICT_DUPLICATE', 0)} |
| NEEDS_MANUAL_REVIEW | {dup_counts.get('NEEDS_MANUAL_REVIEW', 0)} |
| **TOTAL** | **{len(duplicates)}** |

---

## Detalhamento

| Matrícula | N | Fontes | Hashes | Páginas | Dif. Técnica | Campos | Classificação |
|---|---|---|---|---|---|---|---|
{rows_str}

---

## Legenda

- **EXACT_DUPLICATE**: mesmo bloco (mesmo hash) — exact-match rejeitado pelo UNIQUE do SQLite.
- **TECHNICAL_DUPLICATE**: mesma matrícula, dados técnicos iguais, hash diferente (blocos
  ligeiramente diferentes no PDF, mas semanticamente equivalentes).
- **CONFLICT_DUPLICATE**: mesma matrícula com dados técnicos divergentes — exige revisão manual.
- **NEEDS_MANUAL_REVIEW**: não foi possível classificar automaticamente.

## Proteção de dados

- Nenhum nome, CPF, CNPJ ou RG foi processado ou exibido.
- Apenas campos técnicos (flags, códigos, páginas) foram comparados.
- A coluna "nome_imovel_sanitizado" foi comparada apenas como sinal de divergência
  (Sim/Não), sem expor o valor.

*Relatório gerado automaticamente — uso restrito à equipe técnica da serventia.*
"""


if __name__ == "__main__":
    main()
