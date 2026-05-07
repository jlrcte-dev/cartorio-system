# NÃO usar `from __future__ import annotations` — Pydantic v2 precisa avaliar
# os tipos em tempo real (ver decisão em finance.schemas e lgpd.schemas).
import datetime as _dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.modules.compliance.enums import (
    ComplianceEvidenceSourceModule,
    ComplianceEvidenceStatus,
    ComplianceEvidenceType,
    ComplianceLinkRiskLevel,
    ComplianceLinkSourceModule,
    ComplianceLinkSourceType,
    DeadlineUnit,
    PolicyDocumentKind,
    RequirementClassification,
    RequirementSource,
    RequirementStage,
    ServentiaClass,
)

CONSERVATIVE_SOURCE_NOTE = (
    "Requisito mapeado a partir da Matriz INOVA V1; não representa "
    "declaração automática de conformidade."
)


class DeadlineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    serventia_class: ServentiaClass
    value: int | None
    unit: DeadlineUnit
    stage_label: str
    notes: str | None


class EvidenceTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    description: str
    sort_order: int
    notes: str | None


class PolicyDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    title: str
    kind: PolicyDocumentKind
    classification: RequirementClassification
    inova_filename: str
    description: str | None


class RequirementPolicyLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    policy: PolicyDocumentRead
    policy_section_notes: str


class RequirementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    source: RequirementSource
    article_label: str
    article_text: str
    classification: RequirementClassification
    stage: RequirementStage
    notes: str | None

    @computed_field
    @property
    def mapping_status(self) -> Literal["MAPPED"]:
        return "MAPPED"


class RequirementDetail(RequirementRead):
    deadlines: list[DeadlineRead] = Field(default_factory=list)
    evidence_templates: list[EvidenceTemplateRead] = Field(default_factory=list)
    policies: list[RequirementPolicyLinkRead] = Field(default_factory=list)

    @computed_field
    @property
    def source_note(self) -> str:
        return CONSERVATIVE_SOURCE_NOTE


class PolicyRequirementLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    requirement: RequirementRead
    policy_section_notes: str


class PolicyDocumentDetail(PolicyDocumentRead):
    requirements: list[PolicyRequirementLinkRead] = Field(default_factory=list)


class EtapaSummary(BaseModel):
    stage: RequirementStage
    requirement_count: int
    policy_count: int


class ComplianceSummary(BaseModel):
    seed_version: str | None
    seed_name: str | None
    requirement_count: int
    policy_count: int
    requirement_policy_link_count: int
    deadline_count: int
    evidence_template_count: int
    by_source: dict[str, int]
    by_classification: dict[str, int]
    by_stage: dict[str, int]
    by_policy_kind: dict[str, int]
    c3_initial_deadline_days: int = 90
    c3_initial_deadline_note: str = (
        "Prazo de 90 dias para Etapas 1-2; data exata deve ser validada administrativamente."
    )
    c3_initial_deadline_reference_date: str | None = "23/05/2026"
    c3_initial_deadline_reference_note: str = (
        "Data informativa derivada do material analisado; validar antes de uso oficial."
    )
    conservative_note: str = CONSERVATIVE_SOURCE_NOTE


class SeedMetaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    seed_name: str
    seed_version: str
    source_document: str
    source_file_reference: str
    record_count_requirements: int
    record_count_policies: int
    record_count_requirement_policies: int
    record_count_deadlines: int
    record_count_evidence_templates: int
    data_checksum: str
    seeded_at: _dt.datetime
    seeded_by: str
    notes: str | None


CONSERVATIVE_EVIDENCE_NOTE = (
    "Evidência registrada para apoio à organização regulatória; "
    "não representa declaração automática de conformidade. "
    "Exige validação humana, jurídica ou administrativa."
)


class ComplianceEvidenceCreate(BaseModel):
    requirement_code: str = Field(..., description="Código do requisito normativo (ex: ART_5)")
    evidence_template_id: int | None = Field(
        None, description="Template sugerido pela Matriz INOVA (opcional)"
    )
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(..., min_length=1)
    evidence_type: ComplianceEvidenceType
    status: ComplianceEvidenceStatus = ComplianceEvidenceStatus.COLLECTED
    source_module: ComplianceEvidenceSourceModule = ComplianceEvidenceSourceModule.MANUAL
    source_type: str | None = Field(None, max_length=64)
    source_ref: str | None = Field(None, max_length=200)
    file_reference: str | None = Field(None, max_length=500)
    responsible_name: str | None = Field(None, max_length=200)
    collected_at: _dt.datetime | None = None
    notes: str | None = None


class ComplianceEvidenceUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = Field(None, min_length=1)
    evidence_type: ComplianceEvidenceType | None = None
    status: ComplianceEvidenceStatus | None = None
    source_module: ComplianceEvidenceSourceModule | None = None
    source_type: str | None = Field(None, max_length=64)
    source_ref: str | None = Field(None, max_length=200)
    file_reference: str | None = Field(None, max_length=500)
    responsible_name: str | None = Field(None, max_length=200)
    collected_at: _dt.datetime | None = None
    reviewed_at: _dt.datetime | None = None
    notes: str | None = None
    evidence_template_id: int | None = None

    @model_validator(mode="after")
    def required_fields_not_null_if_set(self) -> "ComplianceEvidenceUpdate":
        for field_name in ("title", "description"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(
                    f"'{field_name}' não pode ser null; omita o campo ou forneça uma string."
                )
        return self


class ComplianceEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    requirement_id: int
    requirement_code: str
    evidence_template_id: int | None
    title: str
    description: str
    evidence_type: ComplianceEvidenceType
    status: ComplianceEvidenceStatus
    source_module: ComplianceEvidenceSourceModule
    source_type: str | None
    source_ref: str | None
    file_reference: str | None
    responsible_name: str | None
    collected_at: _dt.datetime | None
    reviewed_at: _dt.datetime | None
    created_at: _dt.datetime
    updated_at: _dt.datetime

    @computed_field
    @property
    def evidence_note(self) -> str:
        return CONSERVATIVE_EVIDENCE_NOTE


class ComplianceEvidenceDetail(ComplianceEvidenceRead):
    notes: str | None


CONSERVATIVE_LINK_NOTE = (
    "Vínculo registrado para apoio à rastreabilidade regulatória; "
    "não representa declaração automática de conformidade. "
    "Exige validação humana, jurídica ou administrativa."
)


class RequirementFindingLinkCreate(BaseModel):
    requirement_code: str = Field(..., description="Código do requisito normativo (ex: ART_12)")
    source_module: ComplianceLinkSourceModule
    source_type: ComplianceLinkSourceType
    source_ref: str = Field(..., min_length=1, max_length=200)
    title: str | None = Field(None, max_length=300)
    link_reason: str | None = None
    risk_level: ComplianceLinkRiskLevel | None = None
    notes: str | None = None


class RequirementFindingLinkUpdate(BaseModel):
    source_module: ComplianceLinkSourceModule | None = None
    source_type: ComplianceLinkSourceType | None = None
    source_ref: str | None = Field(None, max_length=200)
    title: str | None = Field(None, max_length=300)
    link_reason: str | None = None
    risk_level: ComplianceLinkRiskLevel | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def required_fields_not_null_if_set(self) -> "RequirementFindingLinkUpdate":
        for field_name in ("source_module", "source_type", "source_ref"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(
                    f"'{field_name}' não pode ser null; omita o campo ou forneça um valor."
                )
        return self


class RequirementFindingLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    requirement_id: int
    requirement_code: str
    source_module: ComplianceLinkSourceModule
    source_type: ComplianceLinkSourceType
    source_ref: str
    title: str | None
    link_reason: str | None
    risk_level: ComplianceLinkRiskLevel | None
    created_at: _dt.datetime
    updated_at: _dt.datetime

    @computed_field
    @property
    def link_note(self) -> str:
        return CONSERVATIVE_LINK_NOTE


class RequirementFindingLinkDetail(RequirementFindingLinkRead):
    notes: str | None


__all__ = [
    "CONSERVATIVE_EVIDENCE_NOTE",
    "CONSERVATIVE_LINK_NOTE",
    "CONSERVATIVE_SOURCE_NOTE",
    "ComplianceEvidenceCreate",
    "ComplianceEvidenceDetail",
    "ComplianceEvidenceRead",
    "ComplianceEvidenceUpdate",
    "ComplianceSummary",
    "DeadlineRead",
    "EtapaSummary",
    "EvidenceTemplateRead",
    "PolicyDocumentDetail",
    "PolicyDocumentRead",
    "PolicyRequirementLinkRead",
    "RequirementDetail",
    "RequirementFindingLinkCreate",
    "RequirementFindingLinkDetail",
    "RequirementFindingLinkRead",
    "RequirementFindingLinkUpdate",
    "RequirementPolicyLinkRead",
    "RequirementRead",
    "SeedMetaRead",
]
