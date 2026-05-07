from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.compliance import service
from app.modules.compliance.enums import (
    ComplianceEvidenceSourceModule,
    ComplianceEvidenceStatus,
    ComplianceLinkRiskLevel,
    ComplianceLinkSourceModule,
    ComplianceLinkSourceType,
    ComplianceRequirementStatusValue,
    PolicyDocumentKind,
    RequirementClassification,
    RequirementSource,
    RequirementStage,
)
from app.modules.compliance.models import (
    ComplianceEvidence,
    ComplianceRequirementStatus,
    RequirementFindingLink,
)
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
    RequirementFindingLinkCreate,
    RequirementFindingLinkDetail,
    RequirementFindingLinkRead,
    RequirementFindingLinkUpdate,
    RequirementPolicyLinkRead,
    RequirementRead,
    RequirementStatusBulkRecomputeResult,
    RequirementStatusDetail,
    RequirementStatusRead,
    RequirementStatusRecomputeResult,
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


# ---------------------------------------------------------------------------
# RequirementFindingLink — vínculos entre requisitos e achados/sinais
# ---------------------------------------------------------------------------


def _link_to_read(link: RequirementFindingLink) -> RequirementFindingLinkRead:
    return RequirementFindingLinkRead.model_validate(
        {
            "id": link.id,
            "requirement_id": link.requirement_id,
            "requirement_code": link.requirement.code,
            "source_module": link.source_module,
            "source_type": link.source_type,
            "source_ref": link.source_ref,
            "title": link.title,
            "link_reason": link.link_reason,
            "risk_level": link.risk_level,
            "created_at": link.created_at,
            "updated_at": link.updated_at,
        }
    )


def _link_to_detail(link: RequirementFindingLink) -> RequirementFindingLinkDetail:
    return RequirementFindingLinkDetail.model_validate(
        {
            "id": link.id,
            "requirement_id": link.requirement_id,
            "requirement_code": link.requirement.code,
            "source_module": link.source_module,
            "source_type": link.source_type,
            "source_ref": link.source_ref,
            "title": link.title,
            "link_reason": link.link_reason,
            "risk_level": link.risk_level,
            "notes": link.notes,
            "created_at": link.created_at,
            "updated_at": link.updated_at,
        }
    )


@router.post("/requirement-links", response_model=RequirementFindingLinkDetail, status_code=201)
def create_finding_link(
    payload: RequirementFindingLinkCreate, db: DbSession
) -> RequirementFindingLinkDetail:
    link = service.create_finding_link(db, payload)
    db.commit()
    db.refresh(link)
    return _link_to_detail(link)


@router.get("/requirement-links", response_model=list[RequirementFindingLinkRead])
def list_finding_links(
    db: DbSession,
    requirement_code: str | None = None,
    source_module: ComplianceLinkSourceModule | None = None,
    source_type: ComplianceLinkSourceType | None = None,
    source_ref: str | None = None,
    risk_level: ComplianceLinkRiskLevel | None = None,
    limit: LimitQuery = 100,
    offset: OffsetQuery = 0,
) -> list[RequirementFindingLinkRead]:
    links = service.list_finding_links(
        db,
        requirement_code=requirement_code,
        source_module=source_module,
        source_type=source_type,
        source_ref=source_ref,
        risk_level=risk_level,
        limit=limit,
        offset=offset,
    )
    return [_link_to_read(lnk) for lnk in links]


@router.get("/requirement-links/{link_id}", response_model=RequirementFindingLinkDetail)
def get_finding_link(link_id: int, db: DbSession) -> RequirementFindingLinkDetail:
    link = service.get_finding_link(db, link_id)
    if link is None:
        raise HTTPException(status_code=404, detail=f"Link id={link_id} não encontrado.")
    return _link_to_detail(link)


@router.patch("/requirement-links/{link_id}", response_model=RequirementFindingLinkDetail)
def update_finding_link(
    link_id: int, payload: RequirementFindingLinkUpdate, db: DbSession
) -> RequirementFindingLinkDetail:
    link = service.update_finding_link(db, link_id, payload)
    db.commit()
    db.refresh(link)
    return _link_to_detail(link)


# ---------------------------------------------------------------------------
# ComplianceRequirementStatus — status indicativo
# ---------------------------------------------------------------------------


def _status_to_read(status: ComplianceRequirementStatus) -> RequirementStatusRead:
    return RequirementStatusRead.model_validate(
        {
            "id": status.id,
            "requirement_id": status.requirement_id,
            "requirement_code": status.requirement.code,
            "status": status.status,
            "evidence_count": status.evidence_count,
            "finding_link_count": status.finding_link_count,
            "high_risk_link_count": status.high_risk_link_count,
            "critical_risk_link_count": status.critical_risk_link_count,
            "last_evidence_at": status.last_evidence_at,
            "last_link_at": status.last_link_at,
            "human_review_required": status.human_review_required,
            "status_note": status.status_note,
            "computed_at": status.computed_at,
            "review_note": status.review_note,
            "reviewed_by": status.reviewed_by,
            "reviewed_at": status.reviewed_at,
            "created_at": status.created_at,
            "updated_at": status.updated_at,
        }
    )


def _status_to_detail(status: ComplianceRequirementStatus) -> RequirementStatusDetail:
    return RequirementStatusDetail.model_validate(_status_to_read(status).model_dump())


@router.get("/requirement-statuses", response_model=list[RequirementStatusRead])
def list_requirement_statuses(
    db: DbSession,
    status: ComplianceRequirementStatusValue | None = None,
    human_review_required: bool | None = None,
    requirement_code: str | None = None,
    source: RequirementSource | None = None,
    classification: RequirementClassification | None = None,
    limit: LimitQuery = 100,
    offset: OffsetQuery = 0,
) -> list[RequirementStatusRead]:
    statuses = service.list_requirement_statuses(
        db,
        status=status,
        human_review_required=human_review_required,
        requirement_code=requirement_code,
        source=source,
        classification=classification,
        limit=limit,
        offset=offset,
    )
    return [_status_to_read(s) for s in statuses]


@router.get(
    "/requirements/{code}/status", response_model=RequirementStatusDetail
)
def get_requirement_status(code: str, db: DbSession) -> RequirementStatusDetail:
    status = service.get_requirement_status(db, code)
    if status is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Status do requisito '{code}' ainda não foi computado. "
                "Execute o recompute para inicializar."
            ),
        )
    return _status_to_detail(status)


@router.post(
    "/requirement-statuses/recompute",
    response_model=RequirementStatusBulkRecomputeResult,
)
def bulk_recompute_requirement_statuses(
    db: DbSession,
) -> RequirementStatusBulkRecomputeResult:
    result = service.recompute_all_statuses(db)
    db.commit()
    return RequirementStatusBulkRecomputeResult.model_validate(result)


@router.post(
    "/requirements/{code}/status/recompute",
    response_model=RequirementStatusRecomputeResult,
)
def recompute_single_requirement_status(
    code: str, db: DbSession
) -> RequirementStatusRecomputeResult:
    status, mutated, change_reason = service.recompute_requirement_status(db, code)
    db.commit()
    db.refresh(status)
    return RequirementStatusRecomputeResult(
        requirement_code=code,
        mutated=mutated,
        status=status.status,
        change_reason=change_reason,
        history_entry_created=mutated,
    )
