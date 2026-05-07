"""Service do módulo compliance.

Não consome `audit`, `lgpd` ou `retention`. Integração com outros módulos
ocorre exclusivamente por referência fraca (source_module/source_type/source_ref).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.compliance.enums import (
    ComplianceEvidenceSourceModule,
    ComplianceEvidenceStatus,
    ComplianceLinkRiskLevel,
    ComplianceLinkSourceModule,
    ComplianceLinkSourceType,
    PolicyDocumentKind,
    RequirementClassification,
    RequirementSource,
    RequirementStage,
)
from app.modules.compliance.models import (
    ComplianceEvidence,
    ComplianceEvidenceTemplate,
    CompliancePolicyDocument,
    ComplianceRequirement,
    ComplianceRequirementDeadline,
    ComplianceRequirementPolicy,
    ComplianceSeedMeta,
    RequirementFindingLink,
)
from app.modules.compliance.schemas import (
    ComplianceEvidenceCreate,
    ComplianceEvidenceUpdate,
    ComplianceSummary,
    EtapaSummary,
    RequirementFindingLinkCreate,
    RequirementFindingLinkUpdate,
)
from app.modules.compliance.seed_data import SEED_META


def get_requirements(
    db: Session,
    *,
    source: RequirementSource | None = None,
    classification: RequirementClassification | None = None,
    stage: RequirementStage | None = None,
    limit: int = 200,
    offset: int = 0,
) -> Sequence[ComplianceRequirement]:
    stmt = select(ComplianceRequirement).order_by(ComplianceRequirement.code)
    if source is not None:
        stmt = stmt.where(ComplianceRequirement.source == source)
    if classification is not None:
        stmt = stmt.where(ComplianceRequirement.classification == classification)
    if stage is not None:
        stmt = stmt.where(ComplianceRequirement.stage == stage)
    stmt = stmt.limit(limit).offset(offset)
    return db.scalars(stmt).all()


def get_requirement(db: Session, code: str) -> ComplianceRequirement | None:
    stmt = (
        select(ComplianceRequirement)
        .where(ComplianceRequirement.code == code)
        .options(
            selectinload(ComplianceRequirement.deadlines),
            selectinload(ComplianceRequirement.evidence_templates),
            selectinload(ComplianceRequirement.policy_links).selectinload(
                ComplianceRequirementPolicy.policy
            ),
        )
    )
    return db.scalar(stmt)


def get_policies(
    db: Session,
    *,
    kind: PolicyDocumentKind | None = None,
    classification: RequirementClassification | None = None,
    limit: int = 200,
    offset: int = 0,
) -> Sequence[CompliancePolicyDocument]:
    stmt = select(CompliancePolicyDocument).order_by(CompliancePolicyDocument.code)
    if kind is not None:
        stmt = stmt.where(CompliancePolicyDocument.kind == kind)
    if classification is not None:
        stmt = stmt.where(CompliancePolicyDocument.classification == classification)
    stmt = stmt.limit(limit).offset(offset)
    return db.scalars(stmt).all()


def get_policy(db: Session, code: str) -> CompliancePolicyDocument | None:
    stmt = (
        select(CompliancePolicyDocument)
        .where(CompliancePolicyDocument.code == code)
        .options(
            selectinload(CompliancePolicyDocument.requirement_links).selectinload(
                ComplianceRequirementPolicy.requirement
            ),
        )
    )
    return db.scalar(stmt)


def get_etapas_summary(db: Session) -> list[EtapaSummary]:
    """Resumo por etapa: requisitos por etapa e políticas distintas associadas."""

    requirements = db.scalars(
        select(ComplianceRequirement).options(selectinload(ComplianceRequirement.policy_links))
    ).all()

    by_stage_reqs: Counter[RequirementStage] = Counter()
    by_stage_policy_ids: dict[RequirementStage, set[int]] = {}
    for req in requirements:
        by_stage_reqs[req.stage] += 1
        bucket = by_stage_policy_ids.setdefault(req.stage, set())
        for link in req.policy_links:
            bucket.add(link.policy_id)

    return [
        EtapaSummary(
            stage=stage,
            requirement_count=by_stage_reqs[stage],
            policy_count=len(by_stage_policy_ids.get(stage, set())),
        )
        for stage in sorted(by_stage_reqs, key=lambda s: s.value)
    ]


def get_summary(db: Session) -> ComplianceSummary:
    requirements = db.scalars(select(ComplianceRequirement)).all()
    policies = db.scalars(select(CompliancePolicyDocument)).all()
    rp_count = db.scalar(select(func.count()).select_from(ComplianceRequirementPolicy)) or 0
    deadline_count = db.scalar(select(func.count()).select_from(ComplianceRequirementDeadline)) or 0
    evidence_count = db.scalar(select(func.count()).select_from(ComplianceEvidenceTemplate)) or 0

    by_source: Counter[str] = Counter()
    by_classification: Counter[str] = Counter()
    by_stage: Counter[str] = Counter()
    for req in requirements:
        by_source[req.source.value] += 1
        by_classification[req.classification.value] += 1
        by_stage[req.stage.value] += 1

    by_policy_kind: Counter[str] = Counter()
    for pol in policies:
        by_policy_kind[pol.kind.value] += 1

    meta = db.scalar(
        select(ComplianceSeedMeta).where(ComplianceSeedMeta.seed_name == SEED_META["seed_name"])
    )

    return ComplianceSummary(
        seed_version=meta.seed_version if meta is not None else None,
        seed_name=meta.seed_name if meta is not None else None,
        requirement_count=len(requirements),
        policy_count=len(policies),
        requirement_policy_link_count=int(rp_count),
        deadline_count=int(deadline_count),
        evidence_template_count=int(evidence_count),
        by_source=dict(by_source),
        by_classification=dict(by_classification),
        by_stage=dict(by_stage),
        by_policy_kind=dict(by_policy_kind),
    )


def get_seed_meta(db: Session) -> ComplianceSeedMeta | None:
    return db.scalar(
        select(ComplianceSeedMeta).where(ComplianceSeedMeta.seed_name == SEED_META["seed_name"])
    )


# ---------------------------------------------------------------------------
# ComplianceEvidence — escrita e leitura
# ---------------------------------------------------------------------------


def _resolve_requirement(db: Session, requirement_code: str) -> ComplianceRequirement:
    req = db.scalar(
        select(ComplianceRequirement).where(ComplianceRequirement.code == requirement_code)
    )
    if req is None:
        raise HTTPException(
            status_code=404,
            detail=f"Requisito '{requirement_code}' não encontrado.",
        )
    return req


def _validate_template(
    db: Session, template_id: int, requirement_id: int
) -> ComplianceEvidenceTemplate:
    tpl = db.scalar(
        select(ComplianceEvidenceTemplate).where(ComplianceEvidenceTemplate.id == template_id)
    )
    if tpl is None:
        raise HTTPException(
            status_code=400,
            detail=f"Template de evidência id={template_id} não encontrado.",
        )
    if tpl.requirement_id != requirement_id:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Template id={template_id} pertence ao requisito id={tpl.requirement_id}, "
                f"mas a evidência está sendo registrada para o requisito id={requirement_id}. "
                "Utilize um template compatível com o requisito informado."
            ),
        )
    return tpl


def create_evidence(db: Session, payload: ComplianceEvidenceCreate) -> ComplianceEvidence:
    req = _resolve_requirement(db, payload.requirement_code)
    if payload.evidence_template_id is not None:
        _validate_template(db, payload.evidence_template_id, req.id)

    evidence = ComplianceEvidence(
        requirement_id=req.id,
        evidence_template_id=payload.evidence_template_id,
        title=payload.title,
        description=payload.description,
        evidence_type=payload.evidence_type,
        status=payload.status,
        source_module=payload.source_module,
        source_type=payload.source_type,
        source_ref=payload.source_ref,
        file_reference=payload.file_reference,
        responsible_name=payload.responsible_name,
        collected_at=payload.collected_at,
        notes=payload.notes,
    )
    db.add(evidence)
    db.flush()
    db.refresh(evidence)
    return evidence


def list_evidences(
    db: Session,
    *,
    requirement_code: str | None = None,
    status: ComplianceEvidenceStatus | None = None,
    source_module: ComplianceEvidenceSourceModule | None = None,
    limit: int = 100,
    offset: int = 0,
) -> Sequence[ComplianceEvidence]:
    stmt = (
        select(ComplianceEvidence)
        .join(ComplianceEvidence.requirement)
        .options(selectinload(ComplianceEvidence.requirement))
        .order_by(ComplianceEvidence.id)
    )
    if requirement_code is not None:
        stmt = stmt.where(ComplianceRequirement.code == requirement_code)
    if status is not None:
        stmt = stmt.where(ComplianceEvidence.status == status)
    if source_module is not None:
        stmt = stmt.where(ComplianceEvidence.source_module == source_module)
    stmt = stmt.limit(limit).offset(offset)
    return db.scalars(stmt).all()


def get_evidence(db: Session, evidence_id: int) -> ComplianceEvidence | None:
    return db.scalar(
        select(ComplianceEvidence)
        .where(ComplianceEvidence.id == evidence_id)
        .options(selectinload(ComplianceEvidence.requirement))
    )


def update_evidence(
    db: Session, evidence_id: int, payload: ComplianceEvidenceUpdate
) -> ComplianceEvidence:
    evidence = get_evidence(db, evidence_id)
    if evidence is None:
        raise HTTPException(
            status_code=404,
            detail=f"Evidência id={evidence_id} não encontrada.",
        )

    if payload.evidence_template_id is not None:
        _validate_template(db, payload.evidence_template_id, evidence.requirement_id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(evidence, field, value)

    db.flush()
    db.refresh(evidence)
    return evidence


# ---------------------------------------------------------------------------
# RequirementFindingLink — escrita e leitura
# ---------------------------------------------------------------------------


def _check_duplicate_link(
    db: Session,
    requirement_id: int,
    source_module: ComplianceLinkSourceModule,
    source_type: ComplianceLinkSourceType,
    source_ref: str,
) -> None:
    existing = db.scalar(
        select(RequirementFindingLink).where(
            RequirementFindingLink.requirement_id == requirement_id,
            RequirementFindingLink.source_module == source_module,
            RequirementFindingLink.source_type == source_type,
            RequirementFindingLink.source_ref == source_ref,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=400,
            detail="Já existe vínculo para este requisito com a mesma origem.",
        )


def create_finding_link(
    db: Session, payload: RequirementFindingLinkCreate
) -> RequirementFindingLink:
    req = _resolve_requirement(db, payload.requirement_code)
    _check_duplicate_link(
        db, req.id, payload.source_module, payload.source_type, payload.source_ref
    )
    link = RequirementFindingLink(
        requirement_id=req.id,
        source_module=payload.source_module,
        source_type=payload.source_type,
        source_ref=payload.source_ref,
        title=payload.title,
        link_reason=payload.link_reason,
        risk_level=payload.risk_level,
        notes=payload.notes,
    )
    db.add(link)
    db.flush()
    db.refresh(link)
    return link


def list_finding_links(
    db: Session,
    *,
    requirement_code: str | None = None,
    source_module: ComplianceLinkSourceModule | None = None,
    source_type: ComplianceLinkSourceType | None = None,
    source_ref: str | None = None,
    risk_level: ComplianceLinkRiskLevel | None = None,
    limit: int = 100,
    offset: int = 0,
) -> Sequence[RequirementFindingLink]:
    stmt = (
        select(RequirementFindingLink)
        .join(RequirementFindingLink.requirement)
        .options(selectinload(RequirementFindingLink.requirement))
        .order_by(RequirementFindingLink.id)
    )
    if requirement_code is not None:
        stmt = stmt.where(ComplianceRequirement.code == requirement_code)
    if source_module is not None:
        stmt = stmt.where(RequirementFindingLink.source_module == source_module)
    if source_type is not None:
        stmt = stmt.where(RequirementFindingLink.source_type == source_type)
    if source_ref is not None:
        stmt = stmt.where(RequirementFindingLink.source_ref == source_ref)
    if risk_level is not None:
        stmt = stmt.where(RequirementFindingLink.risk_level == risk_level)
    stmt = stmt.limit(limit).offset(offset)
    return db.scalars(stmt).all()


def get_finding_link(db: Session, link_id: int) -> RequirementFindingLink | None:
    return db.scalar(
        select(RequirementFindingLink)
        .where(RequirementFindingLink.id == link_id)
        .options(selectinload(RequirementFindingLink.requirement))
    )


def update_finding_link(
    db: Session, link_id: int, payload: RequirementFindingLinkUpdate
) -> RequirementFindingLink:
    link = get_finding_link(db, link_id)
    if link is None:
        raise HTTPException(
            status_code=404,
            detail=f"Link id={link_id} não encontrado.",
        )
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(link, field, value)
    db.flush()
    db.refresh(link)
    return link
