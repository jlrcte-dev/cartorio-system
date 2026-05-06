# NÃO usar `from __future__ import annotations` — Pydantic v2 precisa avaliar
# os tipos em tempo real (ver decisão em finance.schemas e lgpd.schemas).
import datetime as _dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.modules.compliance.enums import (
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


__all__ = [
    "CONSERVATIVE_SOURCE_NOTE",
    "ComplianceSummary",
    "DeadlineRead",
    "EtapaSummary",
    "EvidenceTemplateRead",
    "PolicyDocumentDetail",
    "PolicyDocumentRead",
    "PolicyRequirementLinkRead",
    "RequirementDetail",
    "RequirementPolicyLinkRead",
    "RequirementRead",
    "SeedMetaRead",
]
