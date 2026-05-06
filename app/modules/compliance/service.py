"""Service read-only do módulo compliance.

Não consome `audit`, `lgpd` ou `retention`. Não tem operações de escrita
(escrita só via `seed.run_seed`).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.compliance.enums import (
    PolicyDocumentKind,
    RequirementClassification,
    RequirementSource,
    RequirementStage,
)
from app.modules.compliance.models import (
    ComplianceEvidenceTemplate,
    CompliancePolicyDocument,
    ComplianceRequirement,
    ComplianceRequirementDeadline,
    ComplianceRequirementPolicy,
    ComplianceSeedMeta,
)
from app.modules.compliance.schemas import ComplianceSummary, EtapaSummary
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
