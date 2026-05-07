"""Testes de service: regras de cálculo, contadores, idempotência, campos humanos."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.compliance import service
from app.modules.compliance.enums import (
    ComplianceEvidenceStatus,
    ComplianceEvidenceType,
    ComplianceLinkRiskLevel,
    ComplianceLinkSourceModule,
    ComplianceLinkSourceType,
    ComplianceRequirementStatusValue,
    RequirementClassification,
    RequirementSource,
    RequirementStage,
)
from app.modules.compliance.models import (
    ComplianceEvidence,
    ComplianceRequirement,
    ComplianceRequirementStatusHistory,
    RequirementFindingLink,
)

PROHIBITED_TERMS = (
    "compliant",
    "conforme",
    "certified",
    "aprovado",
    "regular",
    "cumprido",
    "validado como conforme",
)


def _seed_requirement(db: Session, code: str = "SVC_ST_1") -> ComplianceRequirement:
    req = ComplianceRequirement(
        code=code,
        source=RequirementSource.PROV_213,
        article_label="Art. ST",
        article_text="Texto de teste de status.",
        classification=RequirementClassification.OBRIGATORIO_PROVIMENTO,
        stage=RequirementStage.ETAPA_1,
    )
    db.add(req)
    db.flush()
    return req


def _add_evidence(
    db: Session,
    req: ComplianceRequirement,
    *,
    title: str = "Ev",
    status: ComplianceEvidenceStatus = ComplianceEvidenceStatus.COLLECTED,
    collected_at: datetime | None = None,
) -> ComplianceEvidence:
    ev = ComplianceEvidence(
        requirement_id=req.id,
        title=title,
        description="desc",
        evidence_type=ComplianceEvidenceType.DOCUMENT,
        status=status,
        collected_at=collected_at,
    )
    db.add(ev)
    db.flush()
    return ev


def _add_link(
    db: Session,
    req: ComplianceRequirement,
    *,
    risk_level: ComplianceLinkRiskLevel | None,
    source_ref: str,
    source_module: ComplianceLinkSourceModule = ComplianceLinkSourceModule.AUDIT,
    source_type: ComplianceLinkSourceType = ComplianceLinkSourceType.FINDING,
) -> RequirementFindingLink:
    link = RequirementFindingLink(
        requirement_id=req.id,
        source_module=source_module,
        source_type=source_type,
        source_ref=source_ref,
        risk_level=risk_level,
    )
    db.add(link)
    db.flush()
    return link


def _assert_no_prohibited(text: str | None) -> None:
    if text is None:
        return
    lowered = text.lower()
    for term in PROHIBITED_TERMS:
        assert term not in lowered, f"status_note contém termo proibido: {term!r}"


# ---------------------------------------------------------------------------
# Regras de cálculo
# ---------------------------------------------------------------------------


def test_no_evidence_no_link_yields_evidence_pending(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    status, mutated, reason = service.recompute_requirement_status(db_session, req.code)
    assert mutated is True
    assert status.status == ComplianceRequirementStatusValue.EVIDENCE_PENDING
    assert status.human_review_required is False
    assert status.evidence_count == 0
    assert status.finding_link_count == 0
    assert reason == "first_compute"
    _assert_no_prohibited(status.status_note)


def test_evidence_only_yields_evidence_available(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    _add_evidence(db_session, req)
    status, _, _ = service.recompute_requirement_status(db_session, req.code)
    assert status.status == ComplianceRequirementStatusValue.EVIDENCE_AVAILABLE
    assert status.human_review_required is False
    assert status.evidence_count == 1
    _assert_no_prohibited(status.status_note)


def test_critical_link_yields_has_open_findings(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    _add_link(db_session, req, risk_level=ComplianceLinkRiskLevel.CRITICAL, source_ref="C1")
    status, _, _ = service.recompute_requirement_status(db_session, req.code)
    assert status.status == ComplianceRequirementStatusValue.HAS_OPEN_FINDINGS
    assert status.human_review_required is True
    assert status.critical_risk_link_count == 1


def test_high_link_yields_has_open_findings(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    _add_link(db_session, req, risk_level=ComplianceLinkRiskLevel.HIGH, source_ref="H1")
    status, _, _ = service.recompute_requirement_status(db_session, req.code)
    assert status.status == ComplianceRequirementStatusValue.HAS_OPEN_FINDINGS
    assert status.human_review_required is True
    assert status.high_risk_link_count == 1


def test_medium_link_no_evidence_yields_needs_human_review(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    _add_link(db_session, req, risk_level=ComplianceLinkRiskLevel.MEDIUM, source_ref="M1")
    status, _, _ = service.recompute_requirement_status(db_session, req.code)
    assert status.status == ComplianceRequirementStatusValue.NEEDS_HUMAN_REVIEW
    assert status.human_review_required is True


def test_low_link_no_evidence_yields_needs_human_review(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    _add_link(db_session, req, risk_level=ComplianceLinkRiskLevel.LOW, source_ref="L1")
    status, _, _ = service.recompute_requirement_status(db_session, req.code)
    assert status.status == ComplianceRequirementStatusValue.NEEDS_HUMAN_REVIEW


def test_info_link_no_evidence_yields_needs_human_review(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    _add_link(db_session, req, risk_level=ComplianceLinkRiskLevel.INFO, source_ref="I1")
    status, _, _ = service.recompute_requirement_status(db_session, req.code)
    assert status.status == ComplianceRequirementStatusValue.NEEDS_HUMAN_REVIEW


def test_null_risk_link_yields_needs_human_review(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    _add_link(db_session, req, risk_level=None, source_ref="N1")
    status, _, _ = service.recompute_requirement_status(db_session, req.code)
    assert status.status == ComplianceRequirementStatusValue.NEEDS_HUMAN_REVIEW
    assert status.finding_link_count == 1
    assert status.high_risk_link_count == 0
    assert status.critical_risk_link_count == 0


def test_medium_link_with_evidence_still_needs_human_review(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    _add_evidence(db_session, req)
    _add_link(db_session, req, risk_level=ComplianceLinkRiskLevel.MEDIUM, source_ref="M2")
    status, _, _ = service.recompute_requirement_status(db_session, req.code)
    assert status.status == ComplianceRequirementStatusValue.NEEDS_HUMAN_REVIEW


def test_high_dominates_medium(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    _add_link(db_session, req, risk_level=ComplianceLinkRiskLevel.MEDIUM, source_ref="MX")
    _add_link(db_session, req, risk_level=ComplianceLinkRiskLevel.HIGH, source_ref="HX")
    status, _, _ = service.recompute_requirement_status(db_session, req.code)
    assert status.status == ComplianceRequirementStatusValue.HAS_OPEN_FINDINGS
    assert status.high_risk_link_count == 1
    assert status.finding_link_count == 2


def test_all_evidences_count_including_rejected_and_expired(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    _add_evidence(db_session, req, status=ComplianceEvidenceStatus.COLLECTED, title="A")
    _add_evidence(db_session, req, status=ComplianceEvidenceStatus.REJECTED, title="B")
    _add_evidence(db_session, req, status=ComplianceEvidenceStatus.EXPIRED, title="C")
    status, _, _ = service.recompute_requirement_status(db_session, req.code)
    assert status.evidence_count == 3


# ---------------------------------------------------------------------------
# Contadores
# ---------------------------------------------------------------------------


def test_counters_use_real_sources(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    _add_link(db_session, req, risk_level=ComplianceLinkRiskLevel.CRITICAL, source_ref="C-A")
    _add_link(db_session, req, risk_level=ComplianceLinkRiskLevel.HIGH, source_ref="H-A")
    _add_link(db_session, req, risk_level=ComplianceLinkRiskLevel.MEDIUM, source_ref="M-A")
    _add_link(db_session, req, risk_level=None, source_ref="N-A")
    status, _, _ = service.recompute_requirement_status(db_session, req.code)
    assert status.finding_link_count == 4
    assert status.high_risk_link_count == 1
    assert status.critical_risk_link_count == 1


def test_last_evidence_uses_max_collected_or_created(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    older = datetime(2026, 1, 1, tzinfo=UTC)
    newer = datetime(2026, 5, 1, tzinfo=UTC)
    _add_evidence(db_session, req, title="A", collected_at=older)
    _add_evidence(db_session, req, title="B", collected_at=newer)
    status, _, _ = service.recompute_requirement_status(db_session, req.code)
    assert status.last_evidence_at is not None
    # SQLite descarta tzinfo no armazenamento; comparar valores absolutos.
    expected_naive = newer.replace(tzinfo=None)
    actual_naive = status.last_evidence_at.replace(tzinfo=None)
    assert actual_naive == expected_naive


def test_last_evidence_falls_back_to_created_at(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    _add_evidence(db_session, req, title="NoCollected")
    status, _, _ = service.recompute_requirement_status(db_session, req.code)
    assert status.last_evidence_at is not None


def test_last_link_uses_max_created_at(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    link1 = _add_link(db_session, req, risk_level=ComplianceLinkRiskLevel.LOW, source_ref="L-1")
    link2 = _add_link(db_session, req, risk_level=ComplianceLinkRiskLevel.LOW, source_ref="L-2")
    status, _, _ = service.recompute_requirement_status(db_session, req.code)
    assert status.last_link_at is not None
    assert status.last_link_at >= link1.created_at
    assert status.last_link_at >= link2.created_at


# ---------------------------------------------------------------------------
# Idempotência
# ---------------------------------------------------------------------------


def test_first_recompute_creates_history(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    service.recompute_requirement_status(db_session, req.code)
    history = (
        db_session.query(ComplianceRequirementStatusHistory)
        .filter_by(requirement_id=req.id)
        .all()
    )
    assert len(history) == 1
    assert history[0].previous_status is None
    assert history[0].change_reason == "first_compute"


def test_redundant_recompute_does_not_create_history(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    service.recompute_requirement_status(db_session, req.code)
    for _ in range(5):
        _, mutated, reason = service.recompute_requirement_status(db_session, req.code)
        assert mutated is False
        assert reason is None
    history = (
        db_session.query(ComplianceRequirementStatusHistory)
        .filter_by(requirement_id=req.id)
        .count()
    )
    assert history == 1


def test_redundant_recompute_does_not_change_computed_at(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    status, _, _ = service.recompute_requirement_status(db_session, req.code)
    first_computed_at = status.computed_at.replace(tzinfo=None)
    service.recompute_requirement_status(db_session, req.code)
    db_session.refresh(status)
    assert status.computed_at.replace(tzinfo=None) == first_computed_at


def test_redundant_recompute_does_not_change_updated_at(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    status, _, _ = service.recompute_requirement_status(db_session, req.code)
    db_session.commit()
    db_session.refresh(status)
    first_updated_at = status.updated_at
    service.recompute_requirement_status(db_session, req.code)
    db_session.commit()
    db_session.refresh(status)
    assert status.updated_at == first_updated_at


def test_status_change_creates_history(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    service.recompute_requirement_status(db_session, req.code)
    _add_link(db_session, req, risk_level=ComplianceLinkRiskLevel.CRITICAL, source_ref="X")
    _, mutated, reason = service.recompute_requirement_status(db_session, req.code)
    assert mutated is True
    assert reason in ("status_changed", "status_and_counters_changed")
    history = (
        db_session.query(ComplianceRequirementStatusHistory)
        .filter_by(requirement_id=req.id)
        .all()
    )
    assert len(history) == 2
    assert history[1].previous_status == ComplianceRequirementStatusValue.EVIDENCE_PENDING
    assert history[1].new_status == ComplianceRequirementStatusValue.HAS_OPEN_FINDINGS


def test_counter_only_change_creates_history(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    _add_link(db_session, req, risk_level=ComplianceLinkRiskLevel.HIGH, source_ref="H1")
    service.recompute_requirement_status(db_session, req.code)
    _add_link(db_session, req, risk_level=ComplianceLinkRiskLevel.HIGH, source_ref="H2")
    _, mutated, reason = service.recompute_requirement_status(db_session, req.code)
    assert mutated is True
    assert reason == "counters_changed"
    history = (
        db_session.query(ComplianceRequirementStatusHistory)
        .filter_by(requirement_id=req.id)
        .all()
    )
    assert len(history) == 2


def test_status_note_never_contains_prohibited_terms(db_session: Session) -> None:
    cases = [
        (lambda r: None, ComplianceRequirementStatusValue.EVIDENCE_PENDING),
        (
            lambda r: _add_evidence(db_session, r),
            ComplianceRequirementStatusValue.EVIDENCE_AVAILABLE,
        ),
        (
            lambda r: _add_link(
                db_session, r, risk_level=ComplianceLinkRiskLevel.CRITICAL, source_ref="C-pn"
            ),
            ComplianceRequirementStatusValue.HAS_OPEN_FINDINGS,
        ),
        (
            lambda r: _add_link(
                db_session, r, risk_level=ComplianceLinkRiskLevel.LOW, source_ref="L-pn"
            ),
            ComplianceRequirementStatusValue.NEEDS_HUMAN_REVIEW,
        ),
    ]
    for idx, (setup, expected) in enumerate(cases):
        req = _seed_requirement(db_session, code=f"SVC_PN_{idx}")
        setup(req)
        status, _, _ = service.recompute_requirement_status(db_session, req.code)
        assert status.status == expected
        _assert_no_prohibited(status.status_note)


# ---------------------------------------------------------------------------
# Campos humanos preservados
# ---------------------------------------------------------------------------


def test_recompute_does_not_mutate_human_fields(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    status, _, _ = service.recompute_requirement_status(db_session, req.code)
    db_session.flush()

    review_at = datetime.now(UTC)
    status.review_note = "Revisão prévia do gestor"
    status.reviewed_by = "Gestor X"
    status.reviewed_at = review_at
    db_session.flush()

    # Forçar mutação do status real
    _add_link(db_session, req, risk_level=ComplianceLinkRiskLevel.CRITICAL, source_ref="HUM-1")
    service.recompute_requirement_status(db_session, req.code)
    db_session.refresh(status)

    assert status.status == ComplianceRequirementStatusValue.HAS_OPEN_FINDINGS
    assert status.review_note == "Revisão prévia do gestor"
    assert status.reviewed_by == "Gestor X"
    # Tolerância: SQLite descarta tzinfo no armazenamento.
    assert status.reviewed_at is not None
    actual_naive = status.reviewed_at.replace(tzinfo=None)
    expected_naive = review_at.replace(tzinfo=None)
    assert abs((actual_naive - expected_naive).total_seconds()) < 1


# ---------------------------------------------------------------------------
# get / list / 404
# ---------------------------------------------------------------------------


def test_get_requirement_status_returns_none_if_not_computed(db_session: Session) -> None:
    req = _seed_requirement(db_session, "SVC_NOTYET")
    result = service.get_requirement_status(db_session, req.code)
    assert result is None


def test_get_requirement_status_404_if_code_missing(db_session: Session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        service.get_requirement_status(db_session, "NAO_EXISTE")
    assert exc_info.value.status_code == 404


def test_list_filters_by_status(db_session: Session) -> None:
    a = _seed_requirement(db_session, "SVC_LIST_A")
    b = _seed_requirement(db_session, "SVC_LIST_B")
    _add_evidence(db_session, a)
    _add_link(db_session, b, risk_level=ComplianceLinkRiskLevel.CRITICAL, source_ref="LB")
    service.recompute_requirement_status(db_session, a.code)
    service.recompute_requirement_status(db_session, b.code)

    only_open = service.list_requirement_statuses(
        db_session, status=ComplianceRequirementStatusValue.HAS_OPEN_FINDINGS
    )
    assert len(only_open) == 1
    assert only_open[0].requirement.code == "SVC_LIST_B"


def test_list_filters_by_human_review_required(db_session: Session) -> None:
    a = _seed_requirement(db_session, "SVC_HR_A")
    b = _seed_requirement(db_session, "SVC_HR_B")
    _add_evidence(db_session, a)
    _add_link(db_session, b, risk_level=ComplianceLinkRiskLevel.HIGH, source_ref="HRB")
    service.recompute_requirement_status(db_session, a.code)
    service.recompute_requirement_status(db_session, b.code)

    review = service.list_requirement_statuses(db_session, human_review_required=True)
    assert all(s.human_review_required for s in review)
    no_review = service.list_requirement_statuses(db_session, human_review_required=False)
    assert all(not s.human_review_required for s in no_review)


# ---------------------------------------------------------------------------
# Bulk recompute
# ---------------------------------------------------------------------------


def test_bulk_recompute_processes_all(db_session: Session) -> None:
    for i in range(3):
        _seed_requirement(db_session, code=f"SVC_BULK_{i}")
    result = service.recompute_all_statuses(db_session)
    assert result["processed"] == 3
    assert result["mutated"] == 3
    assert result["unchanged"] == 0
    assert result["failed"] == 0


def test_bulk_recompute_idempotent(db_session: Session) -> None:
    for i in range(3):
        _seed_requirement(db_session, code=f"SVC_BULK2_{i}")
    service.recompute_all_statuses(db_session)
    result = service.recompute_all_statuses(db_session)
    assert result["processed"] == 3
    assert result["mutated"] == 0
    assert result["unchanged"] == 3
