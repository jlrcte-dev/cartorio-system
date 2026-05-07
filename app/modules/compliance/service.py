"""Service do módulo compliance.

Não consome `audit`, `lgpd` ou `retention`. Integração com outros módulos
ocorre exclusivamente por referência fraca (source_module/source_type/source_ref).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

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
    ComplianceEvidenceTemplate,
    CompliancePolicyDocument,
    ComplianceRequirement,
    ComplianceRequirementDeadline,
    ComplianceRequirementPolicy,
    ComplianceRequirementStatus,
    ComplianceRequirementStatusHistory,
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


# ---------------------------------------------------------------------------
# ComplianceRequirementStatus — recompute indicativo
# ---------------------------------------------------------------------------


_PROHIBITED_TERMS_IN_NOTE = (
    "compliant",
    "conforme",
    "certified",
    "aprovado",
    "regular",
    "cumprido",
    "validado como conforme",
)


_BULK_RECOMPUTE_BATCH_SIZE = 100


@dataclass(frozen=True)
class _RequirementSourceCounts:
    evidence_count: int
    finding_link_count: int
    high_risk_link_count: int
    critical_risk_link_count: int
    last_evidence_at: datetime | None
    last_link_at: datetime | None


def _count_requirement_status_sources(
    db: Session, requirement_id: int
) -> _RequirementSourceCounts:
    """Lê fontes primárias da verdade (compliance_evidences e finding_links).

    Não consulta tabelas fora do módulo compliance.
    """

    ev_row = db.execute(
        select(
            func.count(ComplianceEvidence.id),
            func.max(
                func.coalesce(ComplianceEvidence.collected_at, ComplianceEvidence.created_at)
            ),
        ).where(ComplianceEvidence.requirement_id == requirement_id)
    ).one()
    evidence_count = int(ev_row[0] or 0)
    last_evidence_at = ev_row[1]

    high_case = case(
        (RequirementFindingLink.risk_level == ComplianceLinkRiskLevel.HIGH, 1),
        else_=0,
    )
    crit_case = case(
        (RequirementFindingLink.risk_level == ComplianceLinkRiskLevel.CRITICAL, 1),
        else_=0,
    )
    link_row = db.execute(
        select(
            func.count(RequirementFindingLink.id),
            func.coalesce(func.sum(high_case), 0),
            func.coalesce(func.sum(crit_case), 0),
            func.max(RequirementFindingLink.created_at),
        ).where(RequirementFindingLink.requirement_id == requirement_id)
    ).one()
    finding_link_count = int(link_row[0] or 0)
    high_risk_link_count = int(link_row[1] or 0)
    critical_risk_link_count = int(link_row[2] or 0)
    last_link_at = link_row[3]

    return _RequirementSourceCounts(
        evidence_count=evidence_count,
        finding_link_count=finding_link_count,
        high_risk_link_count=high_risk_link_count,
        critical_risk_link_count=critical_risk_link_count,
        last_evidence_at=last_evidence_at,
        last_link_at=last_link_at,
    )


def _compute_requirement_status_value(
    counts: _RequirementSourceCounts,
) -> tuple[ComplianceRequirementStatusValue, bool]:
    """Aplica a regra de cálculo determinística.

    Retorna (status, human_review_required). UNDER_REVIEW não é emitido nesta
    sprint — fica reservado para futura revisão humana.
    """

    if counts.critical_risk_link_count > 0 or counts.high_risk_link_count > 0:
        return ComplianceRequirementStatusValue.HAS_OPEN_FINDINGS, True
    if counts.finding_link_count > 0:
        return ComplianceRequirementStatusValue.NEEDS_HUMAN_REVIEW, True
    if counts.evidence_count > 0:
        return ComplianceRequirementStatusValue.EVIDENCE_AVAILABLE, False
    return ComplianceRequirementStatusValue.EVIDENCE_PENDING, False


def _build_status_note(
    counts: _RequirementSourceCounts,
    status_value: ComplianceRequirementStatusValue,
) -> str:
    """Texto curto, determinístico, conservador. Nunca usa termos proibidos."""

    if status_value == ComplianceRequirementStatusValue.HAS_OPEN_FINDINGS:
        note = (
            f"{counts.critical_risk_link_count} achado(s) de risco CRITICAL e "
            f"{counts.high_risk_link_count} de risco HIGH. "
            "Revisão humana obrigatória."
        )
    elif status_value == ComplianceRequirementStatusValue.NEEDS_HUMAN_REVIEW:
        note = (
            f"{counts.finding_link_count} achado(s) de risco MEDIUM/LOW/INFO. "
            "Revisão humana indicada."
        )
    elif status_value == ComplianceRequirementStatusValue.EVIDENCE_AVAILABLE:
        note = (
            f"{counts.evidence_count} evidência(s) registrada(s); "
            "sem achados vinculados. Status indicativo, sujeito a revisão humana."
        )
    else:
        note = "Sem evidência registrada e sem achado vinculado. Status indicativo."

    note = note[:500]
    lowered = note.lower()
    for term in _PROHIBITED_TERMS_IN_NOTE:
        if term in lowered:
            raise RuntimeError(
                f"status_note contém termo proibido '{term}'. "
                "Revisar _build_status_note — nunca declarar conformidade."
            )
    return note


def _record_status_history_if_mutated(
    db: Session,
    requirement_id: int,
    previous_status: ComplianceRequirementStatusValue | None,
    new_status: ComplianceRequirementStatusValue,
    counts: _RequirementSourceCounts,
    human_review_required: bool,
    change_reason: str,
    computed_at: datetime,
) -> None:
    history = ComplianceRequirementStatusHistory(
        requirement_id=requirement_id,
        previous_status=previous_status,
        new_status=new_status,
        evidence_count=counts.evidence_count,
        finding_link_count=counts.finding_link_count,
        high_risk_link_count=counts.high_risk_link_count,
        critical_risk_link_count=counts.critical_risk_link_count,
        human_review_required=human_review_required,
        change_reason=change_reason,
        computed_at=computed_at,
    )
    db.add(history)


def _create_initial_status(
    db: Session,
    requirement: ComplianceRequirement,
    counts: _RequirementSourceCounts,
    status_value: ComplianceRequirementStatusValue,
    human_review_required: bool,
    note: str,
    now: datetime,
) -> tuple[ComplianceRequirementStatus, bool]:
    """Cria status inicial mitigando race com savepoint.

    Não usa lock distribuído ou advisory lock; em caso de IntegrityError
    (corrida simultânea), faz rollback do savepoint e relê o registro
    persistido por outra transação. Retorna (status, was_created).
    """

    status = ComplianceRequirementStatus(
        requirement_id=requirement.id,
        status=status_value,
        evidence_count=counts.evidence_count,
        finding_link_count=counts.finding_link_count,
        high_risk_link_count=counts.high_risk_link_count,
        critical_risk_link_count=counts.critical_risk_link_count,
        last_evidence_at=counts.last_evidence_at,
        last_link_at=counts.last_link_at,
        human_review_required=human_review_required,
        status_note=note,
        computed_at=now,
    )
    try:
        with db.begin_nested():
            db.add(status)
            db.flush()
    except IntegrityError:
        existing = db.scalar(
            select(ComplianceRequirementStatus).where(
                ComplianceRequirementStatus.requirement_id == requirement.id
            )
        )
        if existing is None:
            raise
        return existing, False
    return status, True


def _apply_recompute(
    db: Session,
    requirement: ComplianceRequirement,
    *,
    now: datetime | None = None,
) -> tuple[ComplianceRequirementStatus, bool, str | None]:
    """Recomputa o status indicativo do requisito.

    Retorna (status, mutated, change_reason). Estritamente idempotente:
    chamadas redundantes não criam history, não tocam computed_at,
    updated_at ou status_note, e não marcam o objeto como dirty.
    """

    if now is None:
        now = datetime.now(UTC)

    counts = _count_requirement_status_sources(db, requirement.id)
    status_value, human_review_required = _compute_requirement_status_value(counts)
    note = _build_status_note(counts, status_value)

    existing = db.scalar(
        select(ComplianceRequirementStatus).where(
            ComplianceRequirementStatus.requirement_id == requirement.id
        )
    )

    if existing is None:
        status, was_created = _create_initial_status(
            db, requirement, counts, status_value, human_review_required, note, now
        )
        if was_created:
            _record_status_history_if_mutated(
                db,
                requirement_id=requirement.id,
                previous_status=None,
                new_status=status_value,
                counts=counts,
                human_review_required=human_review_required,
                change_reason="first_compute",
                computed_at=now,
            )
            db.flush()
            return status, True, "first_compute"
        # Outro request criou o registro entre nossa leitura e nossa escrita
        # (race). Continuamos com a lógica de comparação para garantir
        # idempotência.
        existing = status

    previous_status = existing.status
    status_changed = existing.status != status_value
    counters_changed = (
        existing.evidence_count != counts.evidence_count
        or existing.finding_link_count != counts.finding_link_count
        or existing.high_risk_link_count != counts.high_risk_link_count
        or existing.critical_risk_link_count != counts.critical_risk_link_count
    )
    human_review_changed = existing.human_review_required != human_review_required

    mutated = status_changed or counters_changed or human_review_changed

    if not mutated:
        # last_evidence_at e last_link_at não disparam histórico isoladamente
        # nesta sprint. Com os contadores e status inalterados, nenhum campo
        # do objeto é tocado — preserva updated_at e idempotência absoluta.
        return existing, False, None

    if existing.status != status_value:
        existing.status = status_value
    if existing.evidence_count != counts.evidence_count:
        existing.evidence_count = counts.evidence_count
    if existing.finding_link_count != counts.finding_link_count:
        existing.finding_link_count = counts.finding_link_count
    if existing.high_risk_link_count != counts.high_risk_link_count:
        existing.high_risk_link_count = counts.high_risk_link_count
    if existing.critical_risk_link_count != counts.critical_risk_link_count:
        existing.critical_risk_link_count = counts.critical_risk_link_count
    if existing.last_evidence_at != counts.last_evidence_at:
        existing.last_evidence_at = counts.last_evidence_at
    if existing.last_link_at != counts.last_link_at:
        existing.last_link_at = counts.last_link_at
    if existing.human_review_required != human_review_required:
        existing.human_review_required = human_review_required
    if existing.status_note != note:
        existing.status_note = note
    existing.computed_at = now

    if status_changed and counters_changed:
        change_reason = "status_and_counters_changed"
    elif status_changed:
        change_reason = "status_changed"
    else:
        change_reason = "counters_changed"

    _record_status_history_if_mutated(
        db,
        requirement_id=requirement.id,
        previous_status=previous_status,
        new_status=status_value,
        counts=counts,
        human_review_required=human_review_required,
        change_reason=change_reason,
        computed_at=now,
    )
    db.flush()
    return existing, True, change_reason


def get_requirement_status(
    db: Session, requirement_code: str
) -> ComplianceRequirementStatus | None:
    """Lê o status persistido do requisito. Retorna None se ainda não computado.

    Levanta 404 se o requirement_code não existir.
    """

    req = db.scalar(
        select(ComplianceRequirement).where(ComplianceRequirement.code == requirement_code)
    )
    if req is None:
        raise HTTPException(
            status_code=404,
            detail=f"Requisito '{requirement_code}' não encontrado.",
        )
    return db.scalar(
        select(ComplianceRequirementStatus)
        .where(ComplianceRequirementStatus.requirement_id == req.id)
        .options(selectinload(ComplianceRequirementStatus.requirement))
    )


def list_requirement_statuses(
    db: Session,
    *,
    status: ComplianceRequirementStatusValue | None = None,
    human_review_required: bool | None = None,
    requirement_code: str | None = None,
    source: RequirementSource | None = None,
    classification: RequirementClassification | None = None,
    limit: int = 100,
    offset: int = 0,
) -> Sequence[ComplianceRequirementStatus]:
    stmt = (
        select(ComplianceRequirementStatus)
        .join(ComplianceRequirementStatus.requirement)
        .options(selectinload(ComplianceRequirementStatus.requirement))
        .order_by(ComplianceRequirementStatus.id)
    )
    if status is not None:
        stmt = stmt.where(ComplianceRequirementStatus.status == status)
    if human_review_required is not None:
        stmt = stmt.where(
            ComplianceRequirementStatus.human_review_required == human_review_required
        )
    if requirement_code is not None:
        stmt = stmt.where(ComplianceRequirement.code == requirement_code)
    if source is not None:
        stmt = stmt.where(ComplianceRequirement.source == source)
    if classification is not None:
        stmt = stmt.where(ComplianceRequirement.classification == classification)
    stmt = stmt.limit(limit).offset(offset)
    return db.scalars(stmt).all()


def recompute_requirement_status(
    db: Session, requirement_code: str
) -> tuple[ComplianceRequirementStatus, bool, str | None]:
    req = db.scalar(
        select(ComplianceRequirement).where(ComplianceRequirement.code == requirement_code)
    )
    if req is None:
        raise HTTPException(
            status_code=404,
            detail=f"Requisito '{requirement_code}' não encontrado.",
        )
    return _apply_recompute(db, req)


def recompute_all_statuses(
    db: Session,
    *,
    batch_size: int = _BULK_RECOMPUTE_BATCH_SIZE,
) -> dict[str, int | list[str]]:
    """Recompute em massa, processado por lotes, com isolamento por requisito.

    Cada requisito é processado dentro de seu próprio savepoint para que
    falhas isoladas (ex.: corrupção pontual em fontes) não invalidem todo
    o lote. Não há commit interno: o commit fica a cargo do chamador
    (router), preservando o padrão transacional do módulo.
    """

    processed = 0
    mutated = 0
    unchanged = 0
    failed = 0
    failed_codes: list[str] = []

    offset = 0
    while True:
        requirements = list(
            db.scalars(
                select(ComplianceRequirement)
                .order_by(ComplianceRequirement.id)
                .limit(batch_size)
                .offset(offset)
            ).all()
        )
        if not requirements:
            break

        for req in requirements:
            processed += 1
            try:
                with db.begin_nested():
                    _, was_mutated, _ = _apply_recompute(db, req)
                if was_mutated:
                    mutated += 1
                else:
                    unchanged += 1
            except Exception:
                failed += 1
                failed_codes.append(req.code)

        offset += batch_size

    return {
        "processed": processed,
        "mutated": mutated,
        "unchanged": unchanged,
        "failed": failed,
        "failed_codes": failed_codes,
    }


def get_status_history(
    db: Session, requirement_code: str, *, limit: int = 100, offset: int = 0
) -> Sequence[ComplianceRequirementStatusHistory]:
    """Lê o histórico append-only de mutações do status para um requisito."""

    req = db.scalar(
        select(ComplianceRequirement).where(ComplianceRequirement.code == requirement_code)
    )
    if req is None:
        raise HTTPException(
            status_code=404,
            detail=f"Requisito '{requirement_code}' não encontrado.",
        )
    stmt = (
        select(ComplianceRequirementStatusHistory)
        .where(ComplianceRequirementStatusHistory.requirement_id == req.id)
        .order_by(ComplianceRequirementStatusHistory.id)
        .limit(limit)
        .offset(offset)
    )
    return db.scalars(stmt).all()
