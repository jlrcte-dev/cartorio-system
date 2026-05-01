from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.finance import service
from app.modules.finance.enums import EntryStatus, EntryType, ServiceArea
from app.modules.finance.schemas import (
    FinancialEntryCreate,
    FinancialEntryRead,
    FinancialEntryUpdate,
    MonthlySummary,
)

router = APIRouter(prefix="/finance", tags=["finance"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/entries",
    response_model=FinancialEntryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_entry(
    payload: FinancialEntryCreate,
    db: DbSession,
) -> FinancialEntryRead:
    entry = service.create_entry(db, payload)
    return FinancialEntryRead.model_validate(entry)


_COMPETENCE_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"

CompetenceQuery = Annotated[str | None, Query(pattern=_COMPETENCE_PATTERN)]
StatusQuery = Annotated[EntryStatus | None, Query(alias="status")]
LimitQuery = Annotated[int, Query(ge=1, le=1000)]
OffsetQuery = Annotated[int, Query(ge=0)]
CompetenceRequiredQuery = Annotated[str, Query(pattern=_COMPETENCE_PATTERN)]


@router.get("/entries", response_model=list[FinancialEntryRead])
def list_entries(
    db: DbSession,
    competence_month: CompetenceQuery = None,
    entry_type: EntryType | None = None,
    service_area: ServiceArea | None = None,
    entry_status: StatusQuery = None,
    limit: LimitQuery = 200,
    offset: OffsetQuery = 0,
) -> list[FinancialEntryRead]:
    entries = service.list_entries(
        db,
        competence_month=competence_month,
        entry_type=entry_type,
        service_area=service_area,
        status=entry_status,
        limit=limit,
        offset=offset,
    )
    return [FinancialEntryRead.model_validate(e) for e in entries]


@router.get("/entries/{entry_id}", response_model=FinancialEntryRead)
def get_entry(entry_id: int, db: DbSession) -> FinancialEntryRead:
    entry = service.get_entry(db, entry_id)
    return FinancialEntryRead.model_validate(entry)


@router.patch("/entries/{entry_id}", response_model=FinancialEntryRead)
def update_entry(
    entry_id: int,
    payload: FinancialEntryUpdate,
    db: DbSession,
) -> FinancialEntryRead:
    entry = service.update_entry(db, entry_id, payload)
    return FinancialEntryRead.model_validate(entry)


@router.get("/monthly-summary", response_model=MonthlySummary)
def monthly_summary(
    db: DbSession,
    competence_month: CompetenceRequiredQuery,
) -> MonthlySummary:
    return service.compute_monthly_summary(db, competence_month)
