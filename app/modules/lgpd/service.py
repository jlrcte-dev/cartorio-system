from __future__ import annotations

import csv
import datetime as _dt
import io
from collections import Counter
from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import CartorioException
from app.modules.lgpd.enums import (
    LgpdActionCategory,
    LgpdActionPriority,
    LgpdActionStatus,
    LgpdActionType,
)
from app.modules.lgpd.models import LgpdAction, LgpdActionStatusHistory
from app.modules.lgpd.rules import (
    normalize_action_type,
    normalize_category,
    normalize_key,
    normalize_priority,
    normalize_status,
    parse_csv_date,
    strip_html,
    validate_action_code,
    validate_status_transition,
)
from app.modules.lgpd.schemas import (
    LgpdActionImportReport,
    LgpdActionImportRowError,
    LgpdActionSummary,
    LgpdActionUpdate,
)

# Colunas mínimas (após normalização) que precisamos no CSV da INOVA.
_REQUIRED_COLUMNS = {
    "id_acao",
    "atividade_entregavel",
    "categoria",
    "tipo_de_acao",
    "nivel_de_prioridade",
    "status",
}

# Mapa de cabeçalhos brutos do CSV INOVA → chave canônica usada internamente.
# Cobre as variantes com newline em "Responsável\nExecutante".
_HEADER_ALIASES = {
    "id acao": "id_acao",
    "id de acao": "id_acao",
    "id da acao": "id_acao",
    "atividade entregavel": "atividade_entregavel",
    "atividade/entregavel": "atividade_entregavel",
    "categoria": "categoria",
    "acoes": "acoes",
    "justificativa da acao": "justificativa",
    "departamento unidade": "departamento",
    "departamento/unidade": "departamento",
    "tipo de acao": "tipo_de_acao",
    "nivel de prioridade": "nivel_de_prioridade",
    "responsavel executante": "responsavel",
    "responsavel\nexecutante": "responsavel",
    "data passagem": "data_passagem",
    "data previsao": "data_previsao",
    "data conclusao": "data_conclusao",
    "status": "status",
    "observacao detalhe da acao": "observacao",
    "observacao / detalhe da acao": "observacao",
}


# ---------------------------------------------------------------------------
# CRUD básico
# ---------------------------------------------------------------------------


def get_action_by_code(db: Session, action_code: str) -> LgpdAction:
    code = validate_action_code(action_code)
    stmt = select(LgpdAction).where(LgpdAction.action_code == code)
    action = db.scalars(stmt).one_or_none()
    if action is None:
        raise CartorioException(
            message=f"Ação LGPD {code} não encontrada.",
            status_code=404,
        )
    return action


def list_actions(
    db: Session,
    *,
    status: LgpdActionStatus | None = None,
    category: LgpdActionCategory | None = None,
    priority: LgpdActionPriority | None = None,
    action_type: LgpdActionType | None = None,
    responsible_party: str | None = None,
    department: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> Sequence[LgpdAction]:
    stmt = select(LgpdAction)
    if status is not None:
        stmt = stmt.where(LgpdAction.status == status)
    if category is not None:
        stmt = stmt.where(LgpdAction.category == category)
    if priority is not None:
        stmt = stmt.where(LgpdAction.priority == priority)
    if action_type is not None:
        stmt = stmt.where(LgpdAction.action_type == action_type)
    if responsible_party is not None:
        stmt = stmt.where(LgpdAction.responsible_party == responsible_party)
    if department is not None:
        stmt = stmt.where(LgpdAction.department == department)
    stmt = stmt.order_by(LgpdAction.action_code.asc())
    stmt = stmt.limit(limit).offset(offset)
    return db.scalars(stmt).all()


def update_action(
    db: Session,
    action_code: str,
    payload: LgpdActionUpdate,
) -> LgpdAction:
    action = get_action_by_code(db, action_code)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return action

    reason = data.pop("reason", None)
    new_status = data.get("status")
    updated_by = data.pop("updated_by", None) or "gestor"

    if new_status is not None and new_status != action.status:
        try:
            validate_status_transition(action.status, new_status)
        except ValueError as exc:
            raise CartorioException(message=str(exc), status_code=422) from exc

        history = LgpdActionStatusHistory(
            action_id=action.id,
            previous_status=action.status,
            new_status=new_status,
            changed_by=updated_by,
            reason=reason,
        )
        db.add(history)
        # Auto-preenche completed_date ao concluir, se não veio no payload.
        if (
            new_status == LgpdActionStatus.COMPLETED
            and "completed_date" not in data
            and action.completed_date is None
        ):
            action.completed_date = _dt.date.today()

    for key, value in data.items():
        setattr(action, key, value)
    action.updated_by = updated_by

    db.commit()
    db.refresh(action)
    return action


def list_status_history(db: Session, action_code: str) -> Sequence[LgpdActionStatusHistory]:
    action = get_action_by_code(db, action_code)
    stmt = (
        select(LgpdActionStatusHistory)
        .where(LgpdActionStatusHistory.action_id == action.id)
        .order_by(LgpdActionStatusHistory.changed_at.asc(), LgpdActionStatusHistory.id.asc())
    )
    return db.scalars(stmt).all()


# ---------------------------------------------------------------------------
# Importação CSV
# ---------------------------------------------------------------------------


def _normalize_header(raw: str) -> str:
    key = normalize_key(raw).replace("\r", " ").replace("\n", " ")
    while "  " in key:
        key = key.replace("  ", " ")
    return key.strip()


def _build_field_index(fieldnames: Iterable[str]) -> dict[str, str]:
    """Mapeia nome de coluna canônico → fieldname original do DictReader."""
    mapping: dict[str, str] = {}
    for raw in fieldnames:
        if raw is None:
            continue
        norm = _normalize_header(raw)
        canonical = _HEADER_ALIASES.get(norm)
        if canonical is None:
            # Tenta sem barras e com espaço unificado
            canonical = _HEADER_ALIASES.get(norm.replace("/", " "))
        if canonical is not None and canonical not in mapping:
            mapping[canonical] = raw
    return mapping


def _detect_header_line(content: str) -> int:
    """Retorna o offset (em caracteres) do início da linha de cabeçalho real.

    O export INOVA prefixa o CSV com uma linha `ListSchema={...}`. O cabeçalho
    real começa na primeira linha que contém `"ID Ação"` ou `"ID Acao"`.
    Se não encontrarmos, retornamos 0 (assume CSV "limpo").
    """
    needles = ('"ID Ação"', '"ID Acao"', "ID Ação,", "ID Acao,")
    earliest = -1
    for needle in needles:
        idx = content.find(needle)
        if idx != -1 and (earliest == -1 or idx < earliest):
            earliest = idx
    if earliest == -1:
        return 0
    # Volta ao início da linha
    line_start = content.rfind("\n", 0, earliest)
    return 0 if line_start == -1 else line_start + 1


def _row_to_action_kwargs(row: dict[str, Any], idx: dict[str, str]) -> dict[str, Any]:
    def _get(key: str) -> str | None:
        col = idx.get(key)
        if col is None:
            return None
        value = row.get(col)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    raw_status = _get("status")
    raw_action_code = _get("id_acao")
    if raw_action_code is None:
        raise ValueError("action_code (ID Ação) ausente")
    action_code = validate_action_code(raw_action_code)

    title_raw = _get("atividade_entregavel")
    if not title_raw:
        raise ValueError("title (Atividade/Entregável) ausente")

    return {
        "action_code": action_code,
        "title": (title_raw or "")[:300],
        "category": normalize_category(_get("categoria")),
        "description": strip_html(_get("acoes")),
        "justification": strip_html(_get("justificativa")),
        "department": _get("departamento"),
        "action_type": normalize_action_type(_get("tipo_de_acao")),
        "priority": normalize_priority(_get("nivel_de_prioridade")),
        "responsible_party": _get("responsavel"),
        "planned_date": parse_csv_date(_get("data_passagem")),
        "due_date": parse_csv_date(_get("data_previsao")),
        "completed_date": parse_csv_date(_get("data_conclusao")),
        "status": normalize_status(raw_status),
        "original_status": raw_status,
        "notes": strip_html(_get("observacao")),
    }


def import_actions_from_csv(
    db: Session,
    csv_bytes: bytes | str,
    *,
    created_by: str = "gestor",
) -> LgpdActionImportReport:
    """Importa o Plano de Ação CSV da INOVA. Idempotente por action_code.

    Comportamento:
    - Pula linhas com action_code já existente (não sobrescreve).
    - Linhas inválidas são reportadas em `errors` e não interrompem a importação.
    - Valida cabeçalho mínimo: rejeita CSV sem colunas obrigatórias.
    """
    if isinstance(csv_bytes, bytes):
        try:
            content = csv_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            content = csv_bytes.decode("latin-1")
    else:
        content = csv_bytes

    offset = _detect_header_line(content)
    payload = content[offset:]

    reader = csv.DictReader(io.StringIO(payload))
    if not reader.fieldnames:
        raise CartorioException(
            message="CSV vazio ou sem cabeçalho.",
            status_code=400,
        )

    idx = _build_field_index(reader.fieldnames)
    missing = _REQUIRED_COLUMNS - set(idx.keys())
    if missing:
        names = ", ".join(sorted(missing))
        raise CartorioException(
            message=f"CSV não contém colunas obrigatórias: {names}",
            status_code=400,
        )

    errors: list[LgpdActionImportRowError] = []
    duplicated: list[str] = []
    imported = 0
    skipped = 0
    total = 0

    # Carrega action_codes existentes para checagem rápida.
    existing_codes = set(db.scalars(select(LgpdAction.action_code)).all())

    # Linha 1 é o cabeçalho (após detect_header_line); dados começam em 2.
    for line_no, row in enumerate(reader, start=2):
        total += 1
        try:
            kwargs = _row_to_action_kwargs(row, idx)
        except ValueError as exc:
            errors.append(
                LgpdActionImportRowError(
                    line=line_no,
                    action_code=(row.get(idx.get("id_acao", "")) if idx.get("id_acao") else None),
                    error=str(exc),
                )
            )
            continue

        code = kwargs["action_code"]
        if code in existing_codes:
            duplicated.append(code)
            skipped += 1
            continue

        action = LgpdAction(**kwargs, created_by=created_by, updated_by=created_by)
        db.add(action)
        existing_codes.add(code)
        imported += 1

    db.commit()

    final_summary = _summary_counts(db)

    return LgpdActionImportReport(
        total_rows=total,
        imported_count=imported,
        skipped_count=skipped,
        error_count=len(errors),
        duplicated_action_codes=sorted(set(duplicated)),
        errors=errors,
        final_summary=final_summary,
    )


def _summary_counts(db: Session) -> dict[str, int]:
    actions = db.scalars(select(LgpdAction)).all()
    counts = Counter(a.status.value for a in actions)
    return {
        "total": len(actions),
        "pending": counts.get(LgpdActionStatus.PENDING.value, 0),
        "in_progress": counts.get(LgpdActionStatus.IN_PROGRESS.value, 0),
        "completed": counts.get(LgpdActionStatus.COMPLETED.value, 0),
    }


# ---------------------------------------------------------------------------
# Summary / Dashboard JSON
# ---------------------------------------------------------------------------


def compute_summary(db: Session) -> LgpdActionSummary:
    actions = db.scalars(select(LgpdAction)).all()
    total = len(actions)
    by_status: Counter[str] = Counter(a.status.value for a in actions)
    by_category: Counter[str] = Counter(a.category.value for a in actions)
    by_priority: Counter[str] = Counter(a.priority.value for a in actions)

    completed = by_status.get(LgpdActionStatus.COMPLETED.value, 0)
    pending = by_status.get(LgpdActionStatus.PENDING.value, 0)
    in_progress = by_status.get(LgpdActionStatus.IN_PROGRESS.value, 0)

    completion_percentage = round((completed / total) * 100, 2) if total else 0.0

    today = _dt.date.today()
    overdue_count = sum(
        1
        for a in actions
        if a.due_date is not None and a.due_date < today and a.status != LgpdActionStatus.COMPLETED
    )
    actions_without_due_date = sum(1 for a in actions if a.due_date is None)

    return LgpdActionSummary(
        total_actions=total,
        completed=completed,
        pending=pending,
        in_progress=in_progress,
        completion_percentage=completion_percentage,
        by_category=dict(by_category),
        by_priority=dict(by_priority),
        by_status=dict(by_status),
        overdue_count=overdue_count,
        actions_without_due_date=actions_without_due_date,
    )


# ---------------------------------------------------------------------------
# Exportação CSV
# ---------------------------------------------------------------------------


_EXPORT_COLUMNS = [
    "action_code",
    "title",
    "category",
    "priority",
    "action_type",
    "responsible_party",
    "department",
    "status",
    "original_status",
    "planned_date",
    "due_date",
    "completed_date",
    "notes",
]


def export_actions_csv(db: Session) -> str:
    actions = db.scalars(select(LgpdAction).order_by(LgpdAction.action_code.asc())).all()
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(_EXPORT_COLUMNS)
    for a in actions:
        writer.writerow(
            [
                a.action_code,
                a.title,
                a.category.value,
                a.priority.value,
                a.action_type.value,
                a.responsible_party or "",
                a.department or "",
                a.status.value,
                a.original_status or "",
                a.planned_date.isoformat() if a.planned_date else "",
                a.due_date.isoformat() if a.due_date else "",
                a.completed_date.isoformat() if a.completed_date else "",
                (a.notes or "").replace("\n", " ").replace("\r", " "),
            ]
        )
    return buf.getvalue()
