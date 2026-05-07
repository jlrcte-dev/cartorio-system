from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.modules.compliance.enums import (
    ComplianceEvidenceSourceModule,
    ComplianceEvidenceStatus,
    ComplianceEvidenceType,
    DeadlineUnit,
    PolicyDocumentKind,
    RequirementClassification,
    RequirementSource,
    RequirementStage,
    ServentiaClass,
)

_ENUM_KWARGS = {"native_enum": False}


class ComplianceRequirement(Base):
    """Requisito normativo mapeado a partir da Matriz INOVA V1.

    Não persistir status de conformidade. O campo `mapping_status` no schema
    é apenas calculado.
    """

    __tablename__ = "compliance_requirements"
    __table_args__ = (
        Index("ix_compliance_requirements_source", "source"),
        Index("ix_compliance_requirements_classification", "classification"),
        Index("ix_compliance_requirements_stage", "stage"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    source: Mapped[RequirementSource] = mapped_column(
        Enum(
            RequirementSource,
            name="compliance_requirement_source_enum",
            length=24,
            **_ENUM_KWARGS,
        ),
        nullable=False,
    )
    article_label: Mapped[str] = mapped_column(String(120), nullable=False)
    article_text: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[RequirementClassification] = mapped_column(
        Enum(
            RequirementClassification,
            name="compliance_requirement_classification_enum",
            length=32,
            **_ENUM_KWARGS,
        ),
        nullable=False,
    )
    stage: Mapped[RequirementStage] = mapped_column(
        Enum(
            RequirementStage,
            name="compliance_requirement_stage_enum",
            length=24,
            **_ENUM_KWARGS,
        ),
        nullable=False,
    )
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

    deadlines: Mapped[list[ComplianceRequirementDeadline]] = relationship(
        "ComplianceRequirementDeadline",
        back_populates="requirement",
        cascade="all, delete-orphan",
        order_by="ComplianceRequirementDeadline.serventia_class",
    )
    evidence_templates: Mapped[list[ComplianceEvidenceTemplate]] = relationship(
        "ComplianceEvidenceTemplate",
        back_populates="requirement",
        cascade="all, delete-orphan",
        order_by="ComplianceEvidenceTemplate.sort_order",
    )
    policy_links: Mapped[list[ComplianceRequirementPolicy]] = relationship(
        "ComplianceRequirementPolicy",
        back_populates="requirement",
        cascade="all, delete-orphan",
    )
    evidences: Mapped[list[ComplianceEvidence]] = relationship(
        "ComplianceEvidence",
        back_populates="requirement",
        cascade="all, delete-orphan",
        order_by="ComplianceEvidence.id",
    )


class CompliancePolicyDocument(Base):
    """Política/procedimento/documento indicado pela Matriz INOVA V1."""

    __tablename__ = "compliance_policies"
    __table_args__ = (
        Index("ix_compliance_policies_kind", "kind"),
        Index("ix_compliance_policies_classification", "classification"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    kind: Mapped[PolicyDocumentKind] = mapped_column(
        Enum(
            PolicyDocumentKind,
            name="compliance_policy_kind_enum",
            length=24,
            **_ENUM_KWARGS,
        ),
        nullable=False,
    )
    classification: Mapped[RequirementClassification] = mapped_column(
        Enum(
            RequirementClassification,
            name="compliance_policy_classification_enum",
            length=32,
            **_ENUM_KWARGS,
        ),
        nullable=False,
    )
    inova_filename: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

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

    requirement_links: Mapped[list[ComplianceRequirementPolicy]] = relationship(
        "ComplianceRequirementPolicy",
        back_populates="policy",
        cascade="all, delete-orphan",
    )


class ComplianceRequirementPolicy(Base):
    """Vínculo N:N entre requisito e política, com observação de seção."""

    __tablename__ = "compliance_requirement_policies"
    __table_args__ = (
        UniqueConstraint(
            "requirement_id",
            "policy_id",
            "policy_section_notes",
            name="uq_compliance_req_policy",
        ),
        Index("ix_compliance_req_policy_requirement_id", "requirement_id"),
        Index("ix_compliance_req_policy_policy_id", "policy_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    requirement_id: Mapped[int] = mapped_column(
        ForeignKey("compliance_requirements.id", ondelete="CASCADE"),
        nullable=False,
    )
    policy_id: Mapped[int] = mapped_column(
        ForeignKey("compliance_policies.id", ondelete="CASCADE"),
        nullable=False,
    )
    policy_section_notes: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    requirement: Mapped[ComplianceRequirement] = relationship(
        "ComplianceRequirement", back_populates="policy_links"
    )
    policy: Mapped[CompliancePolicyDocument] = relationship(
        "CompliancePolicyDocument", back_populates="requirement_links"
    )


class ComplianceRequirementDeadline(Base):
    """Prazo estimado por classe de serventia (C1/C2/C3)."""

    __tablename__ = "compliance_requirement_deadlines"
    __table_args__ = (
        UniqueConstraint(
            "requirement_id",
            "serventia_class",
            name="uq_compliance_req_deadline_class",
        ),
        Index("ix_compliance_req_deadline_requirement_id", "requirement_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    requirement_id: Mapped[int] = mapped_column(
        ForeignKey("compliance_requirements.id", ondelete="CASCADE"),
        nullable=False,
    )
    serventia_class: Mapped[ServentiaClass] = mapped_column(
        Enum(
            ServentiaClass,
            name="compliance_serventia_class_enum",
            length=4,
            **_ENUM_KWARGS,
        ),
        nullable=False,
    )
    value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit: Mapped[DeadlineUnit] = mapped_column(
        Enum(
            DeadlineUnit,
            name="compliance_deadline_unit_enum",
            length=24,
            **_ENUM_KWARGS,
        ),
        nullable=False,
    )
    stage_label: Mapped[str] = mapped_column(String(64), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    requirement: Mapped[ComplianceRequirement] = relationship(
        "ComplianceRequirement", back_populates="deadlines"
    )


class ComplianceEvidenceTemplate(Base):
    """Evidência sugerida pela Matriz INOVA V1.

    NÃO representa evidência real coletada da serventia. Apenas o que a matriz
    sugere como demonstração de cumprimento futuro do requisito.
    """

    __tablename__ = "compliance_evidence_templates"
    __table_args__ = (
        UniqueConstraint(
            "requirement_id",
            "sort_order",
            name="uq_compliance_evidence_template_order",
        ),
        Index("ix_compliance_evidence_template_requirement_id", "requirement_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    requirement_id: Mapped[int] = mapped_column(
        ForeignKey("compliance_requirements.id", ondelete="CASCADE"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    requirement: Mapped[ComplianceRequirement] = relationship(
        "ComplianceRequirement", back_populates="evidence_templates"
    )


class ComplianceEvidence(Base):
    """Evidência regulatória real registrada para apoio à organização de conformidade.

    Não representa declaração automática de conformidade. Exige validação
    humana, jurídica ou administrativa antes de qualquer uso oficial.

    Integração com outros módulos ocorre exclusivamente por referência fraca
    (source_module / source_type / source_ref). Não há FK cruzada com audit,
    retention ou lgpd — ADR-001 e ADR-002.
    """

    __tablename__ = "compliance_evidences"
    __table_args__ = (
        Index("ix_compliance_evidences_requirement_id", "requirement_id"),
        Index("ix_compliance_evidences_template_id", "evidence_template_id"),
        Index("ix_compliance_evidences_status", "status"),
        Index("ix_compliance_evidences_source", "source_module"),
        Index("ix_compliance_evidences_collected_at", "collected_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    requirement_id: Mapped[int] = mapped_column(
        ForeignKey("compliance_requirements.id", ondelete="CASCADE"),
        nullable=False,
    )
    evidence_template_id: Mapped[int | None] = mapped_column(
        ForeignKey("compliance_evidence_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_type: Mapped[ComplianceEvidenceType] = mapped_column(
        Enum(
            ComplianceEvidenceType,
            name="compliance_evidence_type_enum",
            length=24,
            **_ENUM_KWARGS,
        ),
        nullable=False,
    )
    status: Mapped[ComplianceEvidenceStatus] = mapped_column(
        Enum(
            ComplianceEvidenceStatus,
            name="compliance_evidence_status_enum",
            length=24,
            **_ENUM_KWARGS,
        ),
        nullable=False,
        default=ComplianceEvidenceStatus.COLLECTED,
    )
    source_module: Mapped[ComplianceEvidenceSourceModule] = mapped_column(
        Enum(
            ComplianceEvidenceSourceModule,
            name="compliance_evidence_source_module_enum",
            length=16,
            **_ENUM_KWARGS,
        ),
        nullable=False,
        default=ComplianceEvidenceSourceModule.MANUAL,
    )
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    file_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    responsible_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    requirement: Mapped[ComplianceRequirement] = relationship(
        "ComplianceRequirement", back_populates="evidences"
    )
    template: Mapped[ComplianceEvidenceTemplate | None] = relationship(
        "ComplianceEvidenceTemplate", foreign_keys=[evidence_template_id]
    )


class ComplianceSeedMeta(Base):
    """Metadados de seed da Matriz INOVA. Versionamento e checksum."""

    __tablename__ = "compliance_seed_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seed_name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    seed_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_document: Mapped[str] = mapped_column(String(300), nullable=False)
    source_file_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    record_count_requirements: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    record_count_policies: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    record_count_requirement_policies: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    record_count_deadlines: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    record_count_evidence_templates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    seeded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    seeded_by: Mapped[str] = mapped_column(String(64), nullable=False, default="gestor")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
