# NÃO usar `from __future__ import annotations` — Pydantic v2 precisa avaliar
# os tipos em tempo real para validação (ver decisão em finance.schemas).
import datetime as _dt

from pydantic import BaseModel, ConfigDict, Field

from app.modules.lgpd.enums import (
    LgpdActionCategory,
    LgpdActionPriority,
    LgpdActionStatus,
    LgpdActionType,
)
from app.modules.lgpd.rules import validate_action_code


class LgpdActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action_code: str
    title: str
    category: LgpdActionCategory
    description: str | None
    justification: str | None
    department: str | None
    action_type: LgpdActionType
    priority: LgpdActionPriority
    responsible_party: str | None
    planned_date: _dt.date | None
    due_date: _dt.date | None
    completed_date: _dt.date | None
    status: LgpdActionStatus
    original_status: str | None
    notes: str | None
    created_by: str
    updated_by: str
    created_at: _dt.datetime
    updated_at: _dt.datetime


class LgpdActionUpdate(BaseModel):
    """Atualização parcial.

    Campos imutáveis: `id`, `action_code`. A transição de status é validada
    no service e gera entrada em LgpdActionStatusHistory.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=300)
    category: LgpdActionCategory | None = None
    description: str | None = None
    justification: str | None = None
    department: str | None = Field(default=None, max_length=100)
    action_type: LgpdActionType | None = None
    priority: LgpdActionPriority | None = None
    responsible_party: str | None = Field(default=None, max_length=100)
    planned_date: _dt.date | None = None
    due_date: _dt.date | None = None
    completed_date: _dt.date | None = None
    status: LgpdActionStatus | None = None
    notes: str | None = None
    reason: str | None = Field(default=None, max_length=1000)
    updated_by: str | None = Field(default=None, min_length=1, max_length=64)


class LgpdActionStatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action_id: int
    previous_status: LgpdActionStatus
    new_status: LgpdActionStatus
    changed_by: str
    changed_at: _dt.datetime
    reason: str | None


# --- Importação CSV --------------------------------------------------------


class LgpdActionImportRowError(BaseModel):
    line: int
    action_code: str | None
    error: str


class LgpdActionImportReport(BaseModel):
    total_rows: int
    imported_count: int
    skipped_count: int
    error_count: int
    duplicated_action_codes: list[str]
    errors: list[LgpdActionImportRowError]
    final_summary: dict[str, int]


# --- Summary ---------------------------------------------------------------


class LgpdActionSummary(BaseModel):
    total_actions: int
    completed: int
    pending: int
    in_progress: int
    completion_percentage: float
    by_category: dict[str, int]
    by_priority: dict[str, int]
    by_status: dict[str, int]
    overdue_count: int
    actions_without_due_date: int


__all__ = [
    "LgpdActionRead",
    "LgpdActionUpdate",
    "LgpdActionStatusHistoryRead",
    "LgpdActionImportReport",
    "LgpdActionImportRowError",
    "LgpdActionSummary",
    "validate_action_code",
]
