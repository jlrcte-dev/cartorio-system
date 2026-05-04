# NÃO usar `from __future__ import annotations` — Pydantic v2 exige avaliação
# em tempo real dos tipos para validação (D-18).
import datetime as _dt

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.audit.findings.enums import (
    AuditCategory,
    AuditImpact,
    AuditOrigin,
    AuditPriority,
    AuditProbability,
    AuditSeverity,
    AuditStatus,
)
from app.modules.audit.findings.rules import (
    validate_critical_priority,
    validate_status_transition_fields,
)


class AuditFindingCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    # --- Obrigatórios ---
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    category: AuditCategory
    origin: AuditOrigin
    severity: AuditSeverity
    probability: AuditProbability
    impact: AuditImpact
    priority: AuditPriority
    evidence_summary: str = Field(..., min_length=1)
    recommended_action: str = Field(..., min_length=1)

    # --- Opcionais ---
    status: AuditStatus = AuditStatus.OPEN
    finding_code: str | None = Field(default=None, max_length=32)
    evidence_source: str | None = Field(default=None, max_length=500)
    evidence_reference: str | None = Field(default=None, max_length=500)
    evidence_artifact_path: str | None = Field(default=None, max_length=1000)
    evidence_hash: str | None = Field(default=None, max_length=64)
    scanner_run_id: str | None = Field(default=None, max_length=36)
    related_file_path: str | None = Field(default=None, max_length=1000)
    related_entity_type: str | None = Field(default=None, max_length=64)
    related_entity_id: str | None = Field(default=None, max_length=64)
    cnj_requirement: str | None = Field(default=None, max_length=200)
    cnj_stage: str | None = Field(default=None, max_length=64)
    compliance_topic: str | None = Field(default=None, max_length=200)
    responsible_area: str | None = Field(default=None, max_length=100)
    assigned_to: str | None = Field(default=None, max_length=100)
    due_date: _dt.date | None = None
    resolution_summary: str | None = None
    resolution_evidence: str | None = None
    dismissed_reason: str | None = None
    created_by: str = Field(default="gestor", min_length=1, max_length=64)
    notes: str | None = None

    @field_validator("due_date", mode="after")
    @classmethod
    def _due_date_not_in_past(cls, v: _dt.date | None) -> _dt.date | None:
        if v is not None and v < _dt.date.today():
            raise ValueError("due_date não pode ser anterior à data de hoje")
        return v

    @model_validator(mode="after")
    def _check_business_rules(self) -> "AuditFindingCreate":
        validate_critical_priority(self.severity, self.priority, self.notes)
        if self.status != AuditStatus.OPEN:
            validate_status_transition_fields(
                status=self.status,
                resolution_summary=self.resolution_summary,
                resolution_evidence=self.resolution_evidence,
                dismissed_reason=self.dismissed_reason,
                notes=self.notes,
            )
        return self


class AuditFindingUpdate(BaseModel):
    """Atualização parcial de um achado.

    Status NÃO pode ser alterado via PATCH — use POST /findings/{id}/status.
    Campos de resolução também são gerenciados exclusivamente via /status.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    finding_code: str | None = Field(default=None, max_length=32)
    category: AuditCategory | None = None
    origin: AuditOrigin | None = None
    severity: AuditSeverity | None = None
    probability: AuditProbability | None = None
    impact: AuditImpact | None = None
    priority: AuditPriority | None = None
    evidence_summary: str | None = None
    recommended_action: str | None = None
    evidence_source: str | None = Field(default=None, max_length=500)
    evidence_reference: str | None = Field(default=None, max_length=500)
    evidence_artifact_path: str | None = Field(default=None, max_length=1000)
    evidence_hash: str | None = Field(default=None, max_length=64)
    scanner_run_id: str | None = Field(default=None, max_length=36)
    related_file_path: str | None = Field(default=None, max_length=1000)
    related_entity_type: str | None = Field(default=None, max_length=64)
    related_entity_id: str | None = Field(default=None, max_length=64)
    cnj_requirement: str | None = Field(default=None, max_length=200)
    cnj_stage: str | None = Field(default=None, max_length=64)
    compliance_topic: str | None = Field(default=None, max_length=200)
    responsible_area: str | None = Field(default=None, max_length=100)
    assigned_to: str | None = Field(default=None, max_length=100)
    due_date: _dt.date | None = None
    reviewed_at: _dt.datetime | None = None
    reviewed_by: str | None = Field(default=None, max_length=64)
    notes: str | None = None
    updated_by: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def _check_critical_rule(self) -> "AuditFindingUpdate":
        # Só valida se ambos severity e priority foram fornecidos no PATCH
        if self.severity is not None and self.priority is not None:
            validate_critical_priority(self.severity, self.priority, self.notes)
        return self


class AuditFindingStatusUpdate(BaseModel):
    """Payload para mudança de status de um achado."""

    model_config = ConfigDict(str_strip_whitespace=True)

    status: AuditStatus
    resolution_summary: str | None = None
    resolution_evidence: str | None = None
    dismissed_reason: str | None = None
    resolved_at: _dt.datetime | None = None
    notes: str | None = None
    updated_by: str = Field(default="gestor", min_length=1, max_length=64)

    @model_validator(mode="after")
    def _check_status_fields(self) -> "AuditFindingStatusUpdate":
        validate_status_transition_fields(
            status=self.status,
            resolution_summary=self.resolution_summary,
            resolution_evidence=self.resolution_evidence,
            dismissed_reason=self.dismissed_reason,
            notes=self.notes,
        )
        return self


class AuditFindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    category: AuditCategory
    origin: AuditOrigin
    severity: AuditSeverity
    probability: AuditProbability
    impact: AuditImpact
    priority: AuditPriority
    status: AuditStatus
    evidence_summary: str
    recommended_action: str
    finding_code: str | None
    evidence_source: str | None
    evidence_reference: str | None
    evidence_artifact_path: str | None
    evidence_hash: str | None
    scanner_run_id: str | None
    related_file_path: str | None
    related_entity_type: str | None
    related_entity_id: str | None
    cnj_requirement: str | None
    cnj_stage: str | None
    compliance_topic: str | None
    responsible_area: str | None
    assigned_to: str | None
    due_date: _dt.date | None
    resolved_at: _dt.datetime | None
    resolution_summary: str | None
    resolution_evidence: str | None
    dismissed_reason: str | None
    created_by: str
    updated_by: str
    reviewed_at: _dt.datetime | None
    reviewed_by: str | None
    notes: str | None
    created_at: _dt.datetime
    updated_at: _dt.datetime
