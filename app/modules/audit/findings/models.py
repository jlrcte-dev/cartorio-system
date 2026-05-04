from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base
from app.modules.audit.findings.enums import (
    AuditCategory,
    AuditImpact,
    AuditOrigin,
    AuditPriority,
    AuditProbability,
    AuditSeverity,
    AuditStatus,
)

_ENUM_KWARGS = {"native_enum": False}


class AuditFinding(Base):
    __tablename__ = "audit_findings"
    __table_args__ = (
        Index("ix_audit_findings_status", "status"),
        Index("ix_audit_findings_severity", "severity"),
        Index("ix_audit_findings_category", "category"),
        Index("ix_audit_findings_priority", "priority"),
        Index("ix_audit_findings_origin", "origin"),
        Index("ix_audit_findings_scanner_run_id", "scanner_run_id"),
        Index("ix_audit_findings_due_date", "due_date"),
        Index("ix_audit_findings_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # --- Campos obrigatórios ---
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[AuditCategory] = mapped_column(
        Enum(AuditCategory, name="audit_category_enum", length=32, **_ENUM_KWARGS),
        nullable=False,
    )
    origin: Mapped[AuditOrigin] = mapped_column(
        Enum(AuditOrigin, name="audit_origin_enum", length=32, **_ENUM_KWARGS),
        nullable=False,
    )
    severity: Mapped[AuditSeverity] = mapped_column(
        Enum(AuditSeverity, name="audit_severity_enum", length=24, **_ENUM_KWARGS),
        nullable=False,
    )
    probability: Mapped[AuditProbability] = mapped_column(
        Enum(AuditProbability, name="audit_probability_enum", length=24, **_ENUM_KWARGS),
        nullable=False,
    )
    impact: Mapped[AuditImpact] = mapped_column(
        Enum(AuditImpact, name="audit_impact_enum", length=24, **_ENUM_KWARGS),
        nullable=False,
    )
    priority: Mapped[AuditPriority] = mapped_column(
        Enum(AuditPriority, name="audit_priority_enum", length=24, **_ENUM_KWARGS),
        nullable=False,
    )
    status: Mapped[AuditStatus] = mapped_column(
        Enum(AuditStatus, name="audit_status_enum", length=24, **_ENUM_KWARGS),
        nullable=False,
        default=AuditStatus.OPEN,
        server_default=AuditStatus.OPEN.value,
    )
    evidence_summary: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)

    # --- Código de identificação (opcional, fornecido pelo usuário) ---
    finding_code: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # --- Evidência ---
    evidence_source: Mapped[str | None] = mapped_column(String(500), nullable=True)
    evidence_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    evidence_artifact_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    evidence_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scanner_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # --- Relacionamentos ---
    related_file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    related_entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    related_entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # --- CNJ/Conformidade ---
    cnj_requirement: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cnj_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    compliance_topic: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # --- Responsabilidade e prazo ---
    responsible_area: Mapped[str | None] = mapped_column(String(100), nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # --- Resolução ---
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    dismissed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Auditoria interna ---
    created_by: Mapped[str] = mapped_column(
        String(64), nullable=False, default="gestor", server_default="gestor"
    )
    updated_by: Mapped[str] = mapped_column(
        String(64), nullable=False, default="gestor", server_default="gestor"
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

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
