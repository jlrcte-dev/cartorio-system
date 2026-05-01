from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import CartorioException
from app.modules.finance.enums import (
    SETTLED_STATUS_BY_TYPE,
    EntryDirection,
    EntryStatus,
    EntryType,
    ServiceArea,
)
from app.modules.finance.models import FinancialEntry
from app.modules.finance.rules import (
    resolve_direction,
    validate_payment_date_for_status,
    validate_status_for_type,
)
from app.modules.finance.schemas import (
    FinancialEntryCreate,
    FinancialEntryUpdate,
    MonthlySummary,
    ServiceAreaBucket,
    TypeBucket,
)

ZERO = Decimal("0.00")


def create_entry(db: Session, payload: FinancialEntryCreate) -> FinancialEntry:
    data = payload.model_dump()
    # updated_by espelha created_by no momento da criação
    data["updated_by"] = data["created_by"]
    entry = FinancialEntry(**data)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_entry(db: Session, entry_id: int) -> FinancialEntry:
    entry = db.get(FinancialEntry, entry_id)
    if entry is None:
        raise CartorioException(
            message=f"Lançamento financeiro {entry_id} não encontrado.",
            status_code=404,
        )
    return entry


def list_entries(
    db: Session,
    *,
    competence_month: str | None = None,
    entry_type: EntryType | None = None,
    service_area: ServiceArea | None = None,
    status: EntryStatus | None = None,
    limit: int = 200,
    offset: int = 0,
) -> Sequence[FinancialEntry]:
    stmt = select(FinancialEntry)
    if competence_month is not None:
        stmt = stmt.where(FinancialEntry.competence_month == competence_month)
    if entry_type is not None:
        stmt = stmt.where(FinancialEntry.entry_type == entry_type)
    if service_area is not None:
        stmt = stmt.where(FinancialEntry.service_area == service_area)
    if status is not None:
        stmt = stmt.where(FinancialEntry.status == status)
    stmt = stmt.order_by(FinancialEntry.date.desc(), FinancialEntry.id.desc())
    stmt = stmt.limit(limit).offset(offset)
    return db.scalars(stmt).all()


def update_entry(
    db: Session,
    entry_id: int,
    payload: FinancialEntryUpdate,
) -> FinancialEntry:
    entry = get_entry(db, entry_id)
    data = payload.model_dump(exclude_unset=True)

    if not data:
        return entry

    # entry_type e competence_month são imutáveis (não estão no schema de update).
    new_status = data.get("status", entry.status)
    new_direction = data.get("direction", entry.direction)
    new_payment_date = data.get("payment_date", entry.payment_date)

    try:
        validate_status_for_type(entry.entry_type, new_status)
        resolved_direction = resolve_direction(entry.entry_type, new_direction)
        validate_payment_date_for_status(new_status, new_payment_date)
    except ValueError as exc:
        raise CartorioException(message=str(exc), status_code=422) from exc

    data["direction"] = resolved_direction

    for key, value in data.items():
        setattr(entry, key, value)

    db.commit()
    db.refresh(entry)
    return entry


def compute_monthly_summary(db: Session, competence_month: str) -> MonthlySummary:
    stmt = select(FinancialEntry).where(FinancialEntry.competence_month == competence_month)
    entries = db.scalars(stmt).all()

    buckets: dict[EntryType, TypeBucket] = {t: TypeBucket() for t in EntryType}
    by_area: dict[str, ServiceAreaBucket] = {a.value: ServiceAreaBucket() for a in ServiceArea}

    total_revenues = ZERO
    total_expenses = ZERO
    total_repasses = ZERO
    total_adj_inflow = ZERO
    total_adj_outflow = ZERO

    pending_count = 0
    to_review_count = 0
    cancelled_count = 0

    for entry in entries:
        bucket = buckets[entry.entry_type]
        amount = Decimal(entry.amount)
        bucket.count += 1

        if entry.status == EntryStatus.CANCELLED:
            bucket.cancelled += amount
            cancelled_count += 1
            continue

        if entry.status == EntryStatus.TO_REVIEW:
            bucket.to_review += amount
            to_review_count += 1
            continue

        bucket.valid_total += amount
        if entry.status == EntryStatus.PENDING:
            bucket.pending += amount
            pending_count += 1
        elif entry.status in SETTLED_STATUS_BY_TYPE[entry.entry_type]:
            bucket.settled += amount

        if entry.entry_type == EntryType.RECEITA:
            total_revenues += amount
        elif entry.entry_type == EntryType.DESPESA:
            total_expenses += amount
        elif entry.entry_type == EntryType.REPASSE:
            total_repasses += amount
        elif entry.entry_type == EntryType.AJUSTE:
            if entry.direction == EntryDirection.INFLOW:
                total_adj_inflow += amount
            else:
                total_adj_outflow += amount

        area_bucket = by_area[entry.service_area.value]
        if entry.entry_type == EntryType.RECEITA:
            area_bucket.receita += amount
        elif entry.entry_type == EntryType.DESPESA:
            area_bucket.despesa += amount
        elif entry.entry_type == EntryType.REPASSE:
            area_bucket.repasse += amount
        elif entry.entry_type == EntryType.AJUSTE:
            if entry.direction == EntryDirection.INFLOW:
                area_bucket.ajuste_inflow += amount
            else:
                area_bucket.ajuste_outflow += amount

    result_estimate = (
        total_revenues + total_adj_inflow - total_expenses - total_repasses - total_adj_outflow
    )

    return MonthlySummary(
        competence_month=competence_month,
        total_revenues=total_revenues,
        total_expenses=total_expenses,
        total_repasses=total_repasses,
        total_adjustments_inflow=total_adj_inflow,
        total_adjustments_outflow=total_adj_outflow,
        result_estimate=result_estimate,
        receita=buckets[EntryType.RECEITA],
        despesa=buckets[EntryType.DESPESA],
        repasse=buckets[EntryType.REPASSE],
        ajuste=buckets[EntryType.AJUSTE],
        by_service_area=by_area,
        pending_count=pending_count,
        to_review_count=to_review_count,
        cancelled_count=cancelled_count,
        entry_count=len(entries),
    )
