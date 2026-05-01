from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base
from app.modules.finance.enums import (
    EntryDirection,
    EntrySource,
    EntryStatus,
    EntryType,
    ServiceArea,
)


class FinancialCategory(Base):
    __tablename__ = "financial_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class FinancialEntry(Base):
    __tablename__ = "financial_entries"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_financial_entries_amount_positive"),
        Index(
            "ix_financial_entries_competence_type",
            "competence_month",
            "entry_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    entry_type: Mapped[EntryType] = mapped_column(
        Enum(EntryType, name="entry_type_enum", native_enum=False, length=16),
        nullable=False,
        index=True,
    )
    direction: Mapped[EntryDirection] = mapped_column(
        Enum(EntryDirection, name="entry_direction_enum", native_enum=False, length=16),
        nullable=False,
        index=True,
    )
    competence_month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    date: Mapped[date] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    service_area: Mapped[ServiceArea] = mapped_column(
        Enum(ServiceArea, name="service_area_enum", native_enum=False, length=16),
        nullable=False,
        default=ServiceArea.GERAL,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[EntryStatus] = mapped_column(
        Enum(EntryStatus, name="entry_status_enum", native_enum=False, length=16),
        nullable=False,
        default=EntryStatus.PENDING,
        index=True,
    )
    payment_date: Mapped[date | None] = mapped_column(nullable=True)
    source: Mapped[EntrySource] = mapped_column(
        Enum(EntrySource, name="entry_source_enum", native_enum=False, length=24),
        nullable=False,
        default=EntrySource.MANUAL,
    )
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_by: Mapped[str] = mapped_column(
        String(64), nullable=False, default="gestor", server_default="gestor"
    )
    updated_by: Mapped[str] = mapped_column(
        String(64), nullable=False, default="gestor", server_default="gestor"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
