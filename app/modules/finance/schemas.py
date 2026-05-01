import datetime as _dt
import re
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.finance.enums import (
    EntryDirection,
    EntrySource,
    EntryStatus,
    EntryType,
    ServiceArea,
)
from app.modules.finance.rules import (
    resolve_direction,
    validate_payment_date_for_status,
    validate_status_for_type,
)

COMPETENCE_MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _validate_competence_month(value: str) -> str:
    if not COMPETENCE_MONTH_PATTERN.match(value):
        raise ValueError("competence_month deve estar no formato YYYY-MM")
    return value


class FinancialEntryBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    entry_type: EntryType
    direction: EntryDirection | None = None
    competence_month: str = Field(..., description="Competência no formato YYYY-MM")
    date: _dt.date
    description: str = Field(..., min_length=1, max_length=500)
    category: str | None = Field(default=None, max_length=64)
    service_area: ServiceArea = ServiceArea.GERAL
    amount: Decimal = Field(..., gt=0, max_digits=14, decimal_places=2)
    status: EntryStatus = EntryStatus.PENDING
    payment_date: _dt.date | None = None
    source: EntrySource = EntrySource.MANUAL
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("competence_month")
    @classmethod
    def _check_competence_month(cls, value: str) -> str:
        return _validate_competence_month(value)

    @model_validator(mode="after")
    def _check_consistency(self) -> "FinancialEntryBase":
        self.direction = resolve_direction(self.entry_type, self.direction)
        validate_status_for_type(self.entry_type, self.status)
        validate_payment_date_for_status(self.status, self.payment_date)
        return self


class FinancialEntryCreate(FinancialEntryBase):
    created_by: str = Field(default="gestor", min_length=1, max_length=64)


class FinancialEntryUpdate(BaseModel):
    """Schema de atualização parcial.

    Campos imutáveis após criação (proibidos aqui): `entry_type` e
    `competence_month`. Para corrigir, cancele e recrie o lançamento.

    Regras especiais:
    - `amount` é opcional (pode ser omitido), mas não admite `null` explícito.
      Para zerar/anular um lançamento, use `status=CANCELLED`.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    description: str | None = Field(default=None, min_length=1, max_length=500)
    category: str | None = Field(default=None, max_length=64)
    service_area: ServiceArea | None = None
    amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    status: EntryStatus | None = None
    payment_date: _dt.date | None = None
    source: EntrySource | None = None
    notes: str | None = Field(default=None, max_length=2000)
    date: _dt.date | None = None
    direction: EntryDirection | None = None
    updated_by: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def _reject_null_amount(self) -> "FinancialEntryUpdate":
        if "amount" in self.model_fields_set and self.amount is None:
            raise ValueError("amount não pode ser nulo (omita o campo para mantê-lo)")
        return self


class FinancialEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entry_type: EntryType
    direction: EntryDirection
    competence_month: str
    date: _dt.date
    description: str
    category: str | None
    service_area: ServiceArea
    amount: Decimal
    status: EntryStatus
    payment_date: _dt.date | None
    source: EntrySource
    notes: str | None
    created_by: str
    updated_by: str
    created_at: _dt.datetime
    updated_at: _dt.datetime


class TypeBucket(BaseModel):
    count: int = 0
    valid_total: Decimal = Decimal("0.00")
    pending: Decimal = Decimal("0.00")
    settled: Decimal = Decimal("0.00")
    to_review: Decimal = Decimal("0.00")
    cancelled: Decimal = Decimal("0.00")


class ServiceAreaBucket(BaseModel):
    receita: Decimal = Decimal("0.00")
    despesa: Decimal = Decimal("0.00")
    repasse: Decimal = Decimal("0.00")
    ajuste_inflow: Decimal = Decimal("0.00")
    ajuste_outflow: Decimal = Decimal("0.00")


class MonthlySummary(BaseModel):
    competence_month: str
    total_revenues: Decimal
    total_expenses: Decimal
    total_repasses: Decimal
    total_adjustments_inflow: Decimal
    total_adjustments_outflow: Decimal
    result_estimate: Decimal
    receita: TypeBucket
    despesa: TypeBucket
    repasse: TypeBucket
    ajuste: TypeBucket
    by_service_area: dict[str, ServiceAreaBucket]
    pending_count: int
    to_review_count: int
    cancelled_count: int
    entry_count: int
