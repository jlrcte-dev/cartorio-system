from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.compliance import service
from app.modules.compliance.enums import (
    PolicyDocumentKind,
    RequirementClassification,
    RequirementSource,
    RequirementStage,
)
from app.modules.compliance.schemas import (
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
