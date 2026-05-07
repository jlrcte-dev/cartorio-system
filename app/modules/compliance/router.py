from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.compliance import service
from app.modules.compliance.enums import (
    ComplianceEvidenceSourceModule,
    ComplianceEvidenceStatus,
    PolicyDocumentKind,
    RequirementClassification,
    RequirementSource,
    RequirementStage,
)
from app.modules.compliance.models import ComplianceEvidence
from app.modules.compliance.schemas import (
    ComplianceEvidenceCreate,
    ComplianceEvidenceDetail,
    ComplianceEvidenceRead,
    ComplianceEvidenceUpdate,
    ComplianceSummary,
    EtapaSummary,
    PolicyDocumentDetail,
    PolicyDocumentRead,
    PolicyRequirementLinkRead,
    RequirementDetail,
    RequirementPolicyLinkRead,
    RequirementRead,
)

router = APIRouter(prefix="/compliance", tags=["compliance"])

DbSession = Annotated[Session, Depends(get_db)]
LimitQuery = Annotated[int, Query(ge=1, le=500)]
OffsetQuery = Annotated[int, Query(ge=0)]


@router.get("/requirements", response_model=list[RequirementRead])
def list_requirements(
    db: DbSession,
    source: RequirementSource | None = None,
    classification: RequirementClassification | None = None,
    stage: RequirementStage | None = None,
    limit: LimitQuery = 200,
    offset: OffsetQuery = 0,
) -> list[RequirementRead]:
    requirements = service.get_requirements(
        db,
        source=source,
        classification=classification,
        stage=stage,
        limit=limit,
        offset=offset,
    )
    return [RequirementRead.model_validate(r) for r in requirements]


@router.get("/requirements/{code}", response_model=RequirementDetail)
def get_requirement(code: str, db: DbSession) -> RequirementDetail:
    req = service.get_requirement(db, code)
    if req is None:
        raise HTTPException(status_code=404, detail=f"Requirement '{code}' não encontrado")
    return RequirementDetail.model_validate(
        {
            "id": req.id,
            "code": req.code,
            "source": req.source,
            "article_label": req.article_label,
            "article_text": req.article_text,
            "classification": req.classification,
            "stage": req.stage,
            "notes": req.notes,
            "deadlines": [d for d in req.deadlines],
            "evidence_templates": [e for e in req.evidence_templates],
            "policies": [
                RequirementPolicyLinkRead(
                    id=link.id,
                    policy=PolicyDocumentRead.model_validate(link.policy),
                    policy_section_notes=link.policy_section_notes,
                )
                for link in req.policy_links
            ],
        }
    )


@router.get("/policies", response_model=list[PolicyDocumentRead])
def list_policies(
    db: DbSession,
    kind: PolicyDocumentKind | None = None,
    classification: RequirementClassification | None = None,
    limit: LimitQuery = 200,
    offset: OffsetQuery = 0,
) -> list[PolicyDocumentRead]:
    policies = service.get_policies(
        db,
        kind=kind,
        classification=classification,
        limit=limit,
        offset=offset,
    )
    return [PolicyDocumentRead.model_validate(p) for p in policies]


@router.get("/policies/{code}", response_model=PolicyDocumentDetail)
def get_policy(code: str, db: DbSession) -> PolicyDocumentDetail:
    pol = service.get_policy(db, code)
    if pol is None:
        raise HTTPException(status_code=404, detail=f"Policy '{code}' não encontrada")
    return PolicyDocumentDetail.model_validate(
        {
            "id": pol.id,
            "code": pol.code,
            "title": pol.title,
            "kind": pol.kind,
            "classification": pol.classification,
            "inova_filename": pol.inova_filename,
            "description": pol.description,
            "requirements": [
                PolicyRequirementLinkRead(
                    id=link.id,
                    requirement=RequirementRead.model_validate(link.requirement),
                    policy_section_notes=link.policy_section_notes,
                )
                for link in pol.requirement_links
            ],
        }
    )


@router.get("/etapas", response_model=list[EtapaSummary])
def list_etapas(db: DbSession) -> list[EtapaSummary]:
    return service.get_etapas_summary(db)


@router.get("/summary", response_model=ComplianceSummary)
def summary(db: DbSession) -> ComplianceSummary:
    return service.get_summary(db)


# ---------------------------------------------------------------------------
# Evidências regulatórias reais — ComplianceEvidence MVP
# ---------------------------------------------------------------------------


def _evidence_to_read(ev: ComplianceEvidence) -> ComplianceEvidenceRead:
    return ComplianceEvidenceRead.model_validate(
        {
            "id": ev.id,
            "requirement_id": ev.requirement_id,
            "requirement_code": ev.requirement.code,
            "evidence_template_id": ev.evidence_template_id,
            "title": ev.title,
            "description": ev.description,
            "evidence_type": ev.evidence_type,
            "status": ev.status,
            "source_module": ev.source_module,
            "source_type": ev.source_type,
            "source_ref": ev.source_ref,
            "file_reference": ev.file_reference,
            "responsible_name": ev.responsible_name,
            "collected_at": ev.collected_at,
            "reviewed_at": ev.reviewed_at,
            "created_at": ev.created_at,
            "updated_at": ev.updated_at,
        }
    )


def _evidence_to_detail(ev: ComplianceEvidence) -> ComplianceEvidenceDetail:
    return ComplianceEvidenceDetail.model_validate(
        {
            "id": ev.id,
            "requirement_id": ev.requirement_id,
            "requirement_code": ev.requirement.code,
            "evidence_template_id": ev.evidence_template_id,
            "title": ev.title,
            "description": ev.description,
            "evidence_type": ev.evidence_type,
            "status": ev.status,
            "source_module": ev.source_module,
            "source_type": ev.source_type,
            "source_ref": ev.source_ref,
            "file_reference": ev.file_reference,
            "responsible_name": ev.responsible_name,
            "collected_at": ev.collected_at,
            "reviewed_at": ev.reviewed_at,
            "notes": ev.notes,
            "created_at": ev.created_at,
            "updated_at": ev.updated_at,
        }
    )


@router.post("/evidences", response_model=ComplianceEvidenceDetail, status_code=201)
def create_evidence(payload: ComplianceEvidenceCreate, db: DbSession) -> ComplianceEvidenceDetail:
    ev = service.create_evidence(db, payload)
    db.commit()
    db.refresh(ev)
    return _evidence_to_detail(ev)


@router.get("/evidences", response_model=list[ComplianceEvidenceRead])
def list_evidences(
    db: DbSession,
    requirement_code: str | None = None,
    status: ComplianceEvidenceStatus | None = None,
    source_module: ComplianceEvidenceSourceModule | None = None,
    limit: LimitQuery = 100,
    offset: OffsetQuery = 0,
) -> list[ComplianceEvidenceRead]:
    evidences = service.list_evidences(
        db,
        requirement_code=requirement_code,
        status=status,
        source_module=source_module,
        limit=limit,
        offset=offset,
    )
    return [_evidence_to_read(ev) for ev in evidences]


@router.get("/evidences/{evidence_id}", response_model=ComplianceEvidenceDetail)
def get_evidence(evidence_id: int, db: DbSession) -> ComplianceEvidenceDetail:
    ev = service.get_evidence(db, evidence_id)
    if ev is None:
        raise HTTPException(status_code=404, detail=f"Evidência id={evidence_id} não encontrada.")
    return _evidence_to_detail(ev)


@router.patch("/evidences/{evidence_id}", response_model=ComplianceEvidenceDetail)
def update_evidence(
    evidence_id: int, payload: ComplianceEvidenceUpdate, db: DbSession
) -> ComplianceEvidenceDetail:
    ev = service.update_evidence(db, evidence_id, payload)
    db.commit()
    db.refresh(ev)
    return _evidence_to_detail(ev)
