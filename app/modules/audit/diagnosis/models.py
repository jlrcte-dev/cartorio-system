from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.audit.findings.enums import (
    AuditCategory,
    AuditImpact,
    AuditOrigin,
    AuditPriority,
    AuditProbability,
    AuditSeverity,
)

DIAGNOSIS_VERSION = "1.0.0"


class DiagnosisCandidate(BaseModel):
    """A candidate audit finding derived exclusively from file-system metadata.

    SAFETY: no field holds file content — only names, paths, sizes, timestamps.
    """

    candidate_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    category: AuditCategory
    origin: AuditOrigin = AuditOrigin.SCANNER
    severity: AuditSeverity
    probability: AuditProbability
    impact: AuditImpact
    priority: AuditPriority
    status: Literal["CANDIDATE"] = "CANDIDATE"
    evidence_summary: str
    evidence_reference: str = ""
    scanner_run_id: str
    related_file_path: str = ""
    related_parent_path: str = ""
    related_extension: str = ""
    related_size_bytes: int | None = None
    related_modified_at: str = ""
    recommended_action: str
    rule_id: str
    rule_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str = ""


class DiagnosisResult(BaseModel):
    """Complete output of one DocumentDiagnosis run."""

    diagnosis_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_name: str
    scanner_run_id: str
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    inventory_path: str
    total_files_analyzed: int
    total_candidates: int
    candidates: list[DiagnosisCandidate]
