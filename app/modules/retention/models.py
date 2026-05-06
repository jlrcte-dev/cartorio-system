from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base
from app.modules.retention.enums import RetentionPhaseKind

_ENUM_KWARGS = {"native_enum": False}


class RetentionRule(Base):
    """Regra normativa de temporalidade extraída de provimento.

    Apenas representa o que a norma diz. Não autoriza descarte por si só.
    """

    __tablename__ = "retention_rules"
    __table_args__ = (
        UniqueConstraint("codigo", "documento", name="uq_retention_rules_codigo_documento"),
        Index("ix_retention_rules_codigo", "codigo"),
        Index("ix_retention_rules_assunto", "assunto"),
        Index("ix_retention_rules_source_norm", "source_norm"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    codigo: Mapped[str] = mapped_column(String(32), nullable=False)
    assunto: Mapped[str] = mapped_column(String(200), nullable=False)
    documento: Mapped[str] = mapped_column(String(300), nullable=False)

    fase_corrente_text: Mapped[str] = mapped_column(String(64), nullable=False)
    fase_corrente_kind: Mapped[RetentionPhaseKind] = mapped_column(
        Enum(
            RetentionPhaseKind,
            name="retention_phase_kind_enum",
            length=16,
            **_ENUM_KWARGS,
        ),
        nullable=False,
    )
    fase_corrente_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fase_corrente_months: Mapped[int | None] = mapped_column(Integer, nullable=True)

    fase_intermediaria_text: Mapped[str | None] = mapped_column(String(64), nullable=True)

    eliminacao: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    guarda_permanente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requer_microfilmagem: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requer_digitalizacao: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_legal: Mapped[str | None] = mapped_column(Text, nullable=True)
    alteracoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_norm: Mapped[str] = mapped_column(String(64), nullable=False)
    source_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_file: Mapped[str] = mapped_column(String(500), nullable=False)
    source_code: Mapped[str] = mapped_column(String(32), nullable=False)
    source_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

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
