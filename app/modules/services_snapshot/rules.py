"""Regras calibradas com o operador (20/10/2026) e classificação dos registros por aba.

- Linha elegível = um serviço (pode ter vários atos); sem deduplicação.
- Aba = setor, vinculado pelo NOME normalizado igual a um rótulo aprovado; nunca posição.
- Campos reconhecidos pelo cabeçalho; Situação = Observações; Data inicial = Data de
  início (cadastro); Data final = Data de término (encerramento). Só os oito campos
  aprovados tornam a linha elegível; os auxiliares de prenotação não criam serviço.
  Linhas ocultas contam (o filtro da planilha é apresentação).
- Status por igualdade exata após normalizar caixa, acentos e espaços; sem aproximação.
  Datas nunca classificam: data final preenchida não encerra serviço.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from app.modules.services_snapshot.dates import DATE_FIELDS, SAMPLES, TabDates
from app.modules.services_snapshot.xlsx import Sheet, parse_range


def norm(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    no_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(no_marks.split()).casefold()


FIELDS = [
    ("tarefa", "Tarefa"),
    ("prioridade", "Prioridade"),
    ("solicitante", "Solicitante"),
    ("status", "Status"),
    ("data_inicio", "Data de início"),
    ("data_termino", "Data de término"),
    ("responsavel", "Responsável"),
    ("observacoes", "Observações"),
]
FIELD_LABEL = dict(FIELDS)
HEADER_TO_FIELD = {norm(label): key for key, label in FIELDS} | {
    norm("Situação"): "observacoes",
    norm("Data inicial"): "data_inicio",
    norm("Data final"): "data_termino",
}
MULTI_ALLOWED = {"observacoes"}  # Observações e Situação podem coexistir

# Auxiliares lidos só para os indicadores de prenotação do RI; fora da elegibilidade.
# PRENOTAÇÃO não entra: pode conter número de protocolo, nunca é tratada como data.
AUX_HEADERS = {
    norm("Data da prenotação"): "data_prenotacao",
    norm("Data de prenotação"): "data_prenotacao",
    norm("Vencimento da Prenotação"): "vencimento_prenotacao",
}
PRENOTATION_SECTOR = "Registro de Imóveis"

# Campos nomeados da fonte, preservados nela e fora dos cálculos deste retrato.
NAMED_IGNORED = ["PRENOTAÇÃO", "Outorgante"]
NAMED_IGNORED_V10 = ["PRENOTAÇÃO", "Vencimento da Prenotação", "Outorgante"]  # formato 1.0
NAMED_IGNORED_BY_NORM = {norm(x): x for x in NAMED_IGNORED}

SECTORS = [
    "Escrituras",
    "Registro de Imóveis",
    "Escrituras - Diversas",
    "Registro Civil",
    "Procurações",
    "Diversos",
]
SECTOR_BY_NORM = {norm(x): x for x in SECTORS}

CATEGORY_LABEL = {
    "em_execucao": "em execução",
    "aguardando_assinatura": "aguardando assinatura",
    "aguardando_documentacao": "aguardando documentação",
    "aguardando_pagamento": "aguardando pagamento",
    "pronto_para_finalizar": "pronto para finalizar",
    "nao_iniciado": "não iniciado",
    "bloqueado": "bloqueado",
    "aguardando_escritura": "aguardando escritura",
    "pendente_protocolo": "pendente de protocolo",
    "concluido": "concluído",
    "cancelado": "cancelado",
}
CATEGORIES = list(CATEGORY_LABEL)
CLOSED = ["concluido", "cancelado"]  # encerramentos distintos
OPEN = [c for c in CATEGORIES if c not in CLOSED]  # inclui bloqueado

STATUS_RULES = [
    ("Em execução", "em_execucao"),
    ("falta ass", "aguardando_assinatura"),
    ("FALTA DOCS", "aguardando_documentacao"),
    ("Falta Pagamento", "aguardando_pagamento"),
    ("Finalização", "pronto_para_finalizar"),
    ("Não iniciada", "nao_iniciado"),
    ("Bloqueado", "bloqueado"),
    ("Bloqueada", "bloqueado"),
    ("Concluída", "concluido"),
    ("Concluído", "concluido"),
    ("Concluído/entregue", "concluido"),
    ("Cancelado", "cancelado"),
    ("Cancelada", "cancelado"),
    ("Aguardando escritura", "aguardando_escritura"),
    ("Pendente de protocolo", "pendente_protocolo"),
]
STATUS_MAP = {norm(label): cat for label, cat in STATUS_RULES}
HIDDEN_BY_FILTER = {"bloqueado", "concluido"}  # regra visual informada pelo operador

SIGNAL_KEYS = [
    "oculto_com_status_fora_de_bloqueado_ou_concluido",
    "visivel_com_status_bloqueado_ou_concluido",
]
PENDING_REASONS = [
    "tabela não identificada de forma única",
    "tabela sem linha de cabeçalho",
    "Tarefa ausente no cabeçalho",
    "Tarefa duplicado no cabeçalho",
    "Status ausente no cabeçalho",
    "Status duplicado no cabeçalho",
]
GAP_TEXT = ["campo ausente", "campo ambíguo"]
TOTAL_RE = re.compile(r"^\s*(sub\s*-?\s*)?totais?\b", re.IGNORECASE)


@dataclass
class UnknownStatus:
    """Atribui apelidos diagnósticos (desconhecido_NN) por ordem de aparição no relatório.
    O valor real só existe em memória; os apelidos não são identificadores permanentes."""

    aliases: dict[str, str] = field(default_factory=dict)

    def alias_for(self, normalized: str) -> str:
        return self.aliases.setdefault(normalized, f"desconhecido_{len(self.aliases) + 1:02d}")


def _pct(part: int, whole: int) -> float | None:
    return round(100 * part / whole, 1) if whole else None


def _group(category: str) -> str:
    if category in OPEN:
        return "nao_encerrados"
    if category in CLOSED:
        return "concluidos" if category == "concluido" else "cancelados"
    return "sem_status_reconhecido"  # ausente ou não mapeado: nunca inferido das datas


def classify_sheet(sheet: Sheet, alias: str, unknown: UnknownStatus, reference: date) -> dict:
    sector = SECTOR_BY_NORM.get(norm(sheet.name))
    base = {
        "alias": alias,
        "setor": sector,
        "vinculo_setor": "nome_confere" if sector else "nao_vinculado",
    }

    def pending(reason: str) -> dict:
        return {**base, "situacao": "schema_pending", "motivo": reason}

    if len(sheet.tables) != 1:
        return pending(PENDING_REASONS[0])
    table = sheet.tables[0]
    r1, c1, r2, c2 = parse_range(table.ref)
    if not table.header_rows:
        return pending(PENDING_REASONS[1])

    by_field: dict[str, list[int]] = {}
    by_aux: dict[str, list[int]] = {}
    ignored: list[int] = []
    named_ignored: set[str] = set()
    for i, header in enumerate(table.columns):
        field_key = HEADER_TO_FIELD.get(norm(header))
        aux_key = AUX_HEADERS.get(norm(header))
        if field_key:
            by_field.setdefault(field_key, []).append(c1 + i)
        elif aux_key:
            by_aux.setdefault(aux_key, []).append(c1 + i)
        else:
            ignored.append(c1 + i)
            if norm(header) in NAMED_IGNORED_BY_NORM:
                named_ignored.add(NAMED_IGNORED_BY_NORM[norm(header)])
    for required, label in (("tarefa", "Tarefa"), ("status", "Status")):
        n = len(by_field.get(required, []))
        if n != 1:
            return pending(f"{label} {'ausente' if n == 0 else 'duplicado'} no cabeçalho")
    ambiguous = {f for f, cols in by_field.items() if len(cols) > 1 and f not in MULTI_ALLOWED}
    approved = sorted(c for cols in by_field.values() for c in cols)
    not_eligible = ignored + [c for cols in by_aux.values() for c in cols]
    status_col = by_field["status"][0]

    date_cols: dict[str, int] = {}
    date_states: dict[str, str] = {}
    for f in DATE_FIELDS:
        cols = (by_field if f in FIELD_LABEL else by_aux).get(f, [])
        if not cols:
            date_states[f] = "nao_identificado"
        elif len(cols) > 1:
            date_states[f] = "ambiguo"
        else:
            date_states[f] = "identificado"
            date_cols[f] = cols[0]
    dates = TabDates(
        reference,
        sheet.date1904,
        date_cols,
        date_states,
        prenotation=sector == PRENOTATION_SECTOR,
    )

    rows = sheet.rows()
    cats: Counter[str] = Counter()
    lines: Counter[str] = Counter()
    unknown_counts: Counter[str] = Counter()
    missing: Counter[str] = Counter()
    signals: Counter[str] = Counter()
    for r in range(r1 + table.header_rows, r2 - table.totals_rows + 1):
        cells = rows.get(r, {})

        def has(c: int, row_cells: dict = cells) -> bool:
            cell = row_cells.get(c)
            return cell is not None and cell.filled()

        if not any(has(c) for c in approved):
            lines["so_campos_ignorados" if any(has(c) for c in not_eligible) else "vazias"] += 1
            continue
        if any(
            (t := cells[c].text() if c in cells else None) and TOTAL_RE.match(t) for c in approved
        ) or any("SUBTOTAL(" in (cells[c].formula or "").upper() for c in approved if c in cells):
            lines["totais_subtotais"] += 1
            continue
        status_cell = cells.get(status_col)
        value = status_cell.value if status_cell else None
        if not has(status_col):
            category = "status_ausente"
        elif value is not None and value[0] == "texto" and norm(value[1]) in STATUS_MAP:
            category = STATUS_MAP[norm(value[1])]
        else:
            category = "status_nao_mapeado"
            key = (
                norm(value[1])
                if value and value[0] == "texto"
                else f"<{value[0] if value else 'sem cache'}>"
            )
            unknown_counts[unknown.alias_for(key)] += 1
        cats[category] += 1
        dates.add(_group(category), cells)
        hidden = r in sheet.hidden_rows
        lines["ocultos" if hidden else "visiveis"] += 1
        if hidden and category not in HIDDEN_BY_FILTER:
            signals[SIGNAL_KEYS[0]] += 1
        if not hidden and category in HIDDEN_BY_FILTER:
            signals[SIGNAL_KEYS[1]] += 1
        for f in ("tarefa", "responsavel", "data_inicio"):
            if f in by_field and f not in ambiguous and not has(by_field[f][0]):
                missing[f] += 1

    absent, unmapped = cats["status_ausente"], cats["status_nao_mapeado"]
    total = sum(cats[c] for c in CATEGORIES) + absent + unmapped
    concluded, cancelled = cats["concluido"], cats["cancelado"]
    open_rec = sum(cats[c] for c in OPEN)

    def gap(f: str) -> int | str:
        if f not in by_field:
            return GAP_TEXT[0]
        return GAP_TEXT[1] if f in ambiguous else missing[f]

    return {
        **base,
        "situacao": "interpretada",
        "motivo": None,
        "campos_ausentes": [FIELD_LABEL[f] for f, _ in FIELDS if f not in by_field],
        "campos_ambiguos": [FIELD_LABEL[f] for f, _ in FIELDS if f in ambiguous],
        "campos_ignorados_nomeados": [x for x in NAMED_IGNORED if x in named_ignored],
        "campos_ignorados_outros": len(ignored) - len(named_ignored),
        "linhas_desconsideradas": {
            k: lines[k] for k in ("so_campos_ignorados", "vazias", "totais_subtotais")
        },
        "total": total,
        "categorias": {c: cats[c] for c in CATEGORIES},
        "status_ausente": absent,
        "status_nao_mapeado": unmapped,
        "nao_mapeados_por_alias": dict(sorted(unknown_counts.items())),
        "concluidos": concluded,
        "cancelados": cancelled,
        "nao_encerrados_reconhecidos": open_rec,
        "visiveis": lines["visiveis"],
        "ocultos": lines["ocultos"],
        "sem_tarefa": gap("tarefa"),
        "sem_responsavel": gap("responsavel"),
        "sem_data_de_inicio": gap("data_inicio"),
        "sinais_de_conferencia": {k: signals[k] for k in SIGNAL_KEYS},
        "datas": dates.to_dict(),
        SAMPLES: dates.samples(),
        "status_reconhecido_pct": _pct(total - absent - unmapped, total),
        "reconciliacoes": {
            "categorias_ausentes_nao_mapeados": total
            == sum(cats[c] for c in CATEGORIES) + absent + unmapped,
            "encerrados_nao_encerrados_ausentes_nao_mapeados": total
            == concluded + cancelled + open_rec + absent + unmapped,
            "visiveis_ocultos": total == lines["visiveis"] + lines["ocultos"],
        },
    }


def classify_workbook(sheets: list[Sheet], reference: date) -> list[dict]:
    """``reference``: data civil da captura; nunca o relógio de quem consulta."""
    unknown = UnknownStatus()
    return [classify_sheet(s, f"aba_{i:02d}", unknown, reference) for i, s in enumerate(sheets, 1)]


def aggregate(tabs: list[dict]) -> dict:
    done = [t for t in tabs if t["situacao"] == "interpretada"]
    keys = [
        "total",
        "status_ausente",
        "status_nao_mapeado",
        "concluidos",
        "cancelados",
        "nao_encerrados_reconhecidos",
        "visiveis",
        "ocultos",
    ]
    agg: dict = {k: sum(t[k] for t in done) for k in keys}
    agg["categorias"] = {c: sum(t["categorias"][c] for t in done) for c in CATEGORIES}
    filled = agg["total"] - agg["status_ausente"]
    recognized = filled - agg["status_nao_mapeado"]
    agg["status_reconhecido_pct_do_total"] = _pct(recognized, agg["total"])
    agg["status_reconhecido_pct_dos_preenchidos"] = _pct(recognized, filled)
    return agg
