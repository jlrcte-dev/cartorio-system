"""Testes de histórico append-only do status indicativo."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.compliance import service
from app.modules.compliance.enums import (
    ComplianceLinkRiskLevel,
    ComplianceLinkSourceModule,
    ComplianceLinkSourceType,
    ComplianceRequirementStatusValue,
    RequirementClassification,
    RequirementSource,
    RequirementStage,
)
from app.modules.compliance.models import (
    ComplianceRequirement,
    ComplianceRequirementStatusHistory,
    RequirementFindingLink,
)


def _seed_req(db: Session, code: str = "HIST_1") -> ComplianceRequirement:
    req = ComplianceRequirement(
        code=code,
        source=RequirementSource.PROV_213,
        article_label="Art. Hist",
        article_text="Texto.",
        classification=RequirementClassification.OBRIGATORIO_PROVIMENTO,
        stage=RequirementStage.ETAPA_1,
    )
    db.add(req)
    db.flush()
    return req


def _add_link(db: Session, req: ComplianceRequirement, ref: str, level) -> None:
    db.add(
        RequirementFindingLink(
            requirement_id=req.id,
            source_module=ComplianceLinkSourceModule.AUDIT,
            source_type=ComplianceLinkSourceType.FINDING,
            source_ref=ref,
            risk_level=level,
        )
    )
    db.flush()


def test_first_compute_writes_history_with_null_previous(db_session: Session) -> None:
    req = _seed_req(db_session)
    service.recompute_requirement_status(db_session, req.code)
    rows = (
        db_session.query(ComplianceRequirementStatusHistory)
        .filter_by(requirement_id=req.id)
        .order_by(ComplianceRequirementStatusHistory.id)
        .all()
    )
    assert len(rows) == 1
    assert rows[0].previous_status is None
    assert rows[0].new_status == ComplianceRequirementStatusValue.EVIDENCE_PENDING
    assert rows[0].change_reason == "first_compute"


def test_history_entries_are_append_only_in_order(db_session: Session) -> None:
    req = _seed_req(db_session)
    service.recompute_requirement_status(db_session, req.code)
    _add_link(db_session, req, "AAA", ComplianceLinkRiskLevel.HIGH)
    service.recompute_requirement_status(db_session, req.code)
    _add_link(db_session, req, "BBB", ComplianceLinkRiskLevel.HIGH)
    service.recompute_requirement_status(db_session, req.code)

    rows = (
        db_session.query(ComplianceRequirementStatusHistory)
        .filter_by(requirement_id=req.id)
        .order_by(ComplianceRequirementStatusHistory.id)
        .all()
    )
    assert len(rows) == 3
    assert rows[0].previous_status is None
    assert rows[1].previous_status == ComplianceRequirementStatusValue.EVIDENCE_PENDING
    assert rows[1].new_status == ComplianceRequirementStatusValue.HAS_OPEN_FINDINGS
    assert rows[2].previous_status == ComplianceRequirementStatusValue.HAS_OPEN_FINDINGS
    assert rows[2].new_status == ComplianceRequirementStatusValue.HAS_OPEN_FINDINGS
    assert rows[2].change_reason == "counters_changed"


def test_redundant_recompute_does_not_append_history(db_session: Session) -> None:
    req = _seed_req(db_session)
    service.recompute_requirement_status(db_session, req.code)
    for _ in range(10):
        service.recompute_requirement_status(db_session, req.code)
    count = (
        db_session.query(ComplianceRequirementStatusHistory)
        .filter_by(requirement_id=req.id)
        .count()
    )
    assert count == 1


def test_get_status_history_via_service(db_session: Session) -> None:
    req = _seed_req(db_session, "HIST_GET")
    service.recompute_requirement_status(db_session, req.code)
    rows = service.get_status_history(db_session, req.code)
    assert len(rows) == 1
