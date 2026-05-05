from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.modules.lgpd.enums import (
    LgpdActionCategory,
    LgpdActionPriority,
    LgpdActionStatus,
    LgpdActionType,
)

_ENUM_KWARGS = {"native_enum": False}


class LgpdAction(Base):
    __tablename__ = "lgpd_actions"
    __table_args__ = (
        Index("ix_lgpd_actions_status", "status"),
        Index("ix_lgpd_actions_category", "category"),
        Index("ix_lgpd_actions_priority", "priority"),
        Index("ix_lgpd_actions_action_type", "action_type"),
        Index("ix_lgpd_actions_responsible_party", "responsible_party"),
        Index("ix_lgpd_actions_department", "department"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    action_code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[LgpdActionCategory] = mapped_column(
        Enum(LgpdActionCategory, name="lgpd_action_category_enum", length=24, **_ENUM_KWARGS),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action_type: Mapped[LgpdActionType] = mapped_column(
        Enum(LgpdActionType, name="lgpd_action_type_enum", length=24, **_ENUM_KWARGS),
        nullable=False,
    )
    priority: Mapped[LgpdActionPriority] = mapped_column(
        Enum(LgpdActionPriority, name="lgpd_action_priority_enum", length=16, **_ENUM_KWARGS),
        nullable=False,
    )
    responsible_party: Mapped[str | None] = mapped_column(String(100), nullable=True)
    planned_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[LgpdActionStatus] = mapped_column(
        Enum(LgpdActionStatus, name="lgpd_action_status_enum", length=24, **_ENUM_KWARGS),
        nullable=False,
        default=LgpdActionStatus.PENDING,
        server_default=LgpdActionStatus.PENDING.value,
    )
    original_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    history: Mapped[list[LgpdActionStatusHistory]] = relationship(
        "LgpdActionStatusHistory",
        back_populates="action",
        cascade="all, delete-orphan",
        order_by="LgpdActionStatusHistory.changed_at",
    )


class LgpdActionStatusHistory(Base):
    __tablename__ = "lgpd_action_status_history"
    __table_args__ = (
        Index("ix_lgpd_action_status_history_action_id", "action_id"),
        Index("ix_lgpd_action_status_history_changed_at", "changed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    action_id: Mapped[int] = mapped_column(
        ForeignKey("lgpd_actions.id", ondelete="CASCADE"),
        nullable=False,
    )
    previous_status: Mapped[LgpdActionStatus] = mapped_column(
        Enum(
            LgpdActionStatus,
            name="lgpd_action_history_prev_status_enum",
            length=24,
            **_ENUM_KWARGS,
        ),
        nullable=False,
    )
    new_status: Mapped[LgpdActionStatus] = mapped_column(
        Enum(
            LgpdActionStatus,
            name="lgpd_action_history_new_status_enum",
            length=24,
            **_ENUM_KWARGS,
        ),
        nullable=False,
    )
    changed_by: Mapped[str] = mapped_column(String(64), nullable=False, default="gestor")
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    action: Mapped[LgpdAction] = relationship("LgpdAction", back_populates="history")
