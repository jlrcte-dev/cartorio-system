"""Testes de model para RequirementFindingLink."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.compliance.enums import (
    ComplianceLinkRiskLevel,
    ComplianceLinkSourceModule,
    ComplianceLinkSourceType,
    RequirementClassification,
    RequirementSource,
    RequirementStage,
)
from app.modules.compliance.models import ComplianceRequirement, RequirementFindingLink


def _make_requirement(db: Session, code: str = "MDL_ART_12") -> ComplianceRequirement:
    req = ComplianceRequirement(
        code=code,
        source=RequirementSource.PROV_213,
        article_label="Art. 12 — Model Test",
        article_text="Texto de teste para model.",
        classification=RequirementClassification.OBRIGATORIO_PROVIMENTO,
        stage=RequirementStage.ETAPA_1,
    )
    db.add(req)
    db.flush()
    return req


def test_create_finding_link_minimal(db_session: Session) -> None:
    req = _make_requirement(db_session)
    link = RequirementFindingLink(
        requirement_id=req.id,
        source_module=ComplianceLinkSourceModule.AUDIT,
        source_type=ComplianceLinkSourceType.FINDING,
        source_ref="DIAG-004",
    )
    db_session.add(link)
    db_session.flush()

    assert link.id is not None
    assert link.requirement_id == req.id
    assert link.source_module == ComplianceLinkSourceModule.AUDIT
    assert link.source_type == ComplianceLinkSourceType.FINDING
    assert link.source_ref == "DIAG-004"
    assert link.title is None
    assert link.link_reason is None
    assert link.risk_level is None
    assert link.notes is None


def test_create_finding_link_full(db_session: Session) -> None:
    req = _make_requirement(db_session)
    link = RequirementFindingLink(
        requirement_id=req.id,
        source_module=ComplianceLinkSourceModule.RETENTION,
        source_type=ComplianceLinkSourceType.SIGNAL,
        source_ref="TEMP-002",
        title="Sinal de retenção relacionado ao art. 12",
        link_reason="Documento retido sem prazo definido viola o requisito.",
        risk_level=ComplianceLinkRiskLevel.HIGH,
        notes="Verificar com equipe jurídica.",
    )
    db_session.add(link)
    db_session.flush()

    assert link.title == "Sinal de retenção relacionado ao art. 12"
    assert link.link_reason is not None
    assert link.risk_level == ComplianceLinkRiskLevel.HIGH
    assert link.notes is not None


def test_finding_link_relationship_to_requirement(db_session: Session) -> None:
    req = _make_requirement(db_session)
    link = RequirementFindingLink(
        requirement_id=req.id,
        source_module=ComplianceLinkSourceModule.LGPD,
        source_type=ComplianceLinkSourceType.ACTION,
        source_ref="AC-01",
    )
    db_session.add(link)
    db_session.flush()
    db_session.refresh(link)

    assert link.requirement is not None
    assert link.requirement.code == req.code


def test_requirement_has_finding_links_collection(db_session: Session) -> None:
    req = _make_requirement(db_session)
    for ref in ["DIAG-001", "DIAG-002", "DIAG-003"]:
        link = RequirementFindingLink(
            requirement_id=req.id,
            source_module=ComplianceLinkSourceModule.AUDIT,
            source_type=ComplianceLinkSourceType.DIAGNOSIS,
            source_ref=ref,
        )
        db_session.add(link)
    db_session.flush()
    db_session.refresh(req)

    assert len(req.finding_links) == 3
    refs = {lnk.source_ref for lnk in req.finding_links}
    assert refs == {"DIAG-001", "DIAG-002", "DIAG-003"}


def test_multiple_links_same_requirement(db_session: Session) -> None:
    req = _make_requirement(db_session)
    modules = [
        (ComplianceLinkSourceModule.AUDIT, ComplianceLinkSourceType.FINDING, "DIAG-004"),
        (ComplianceLinkSourceModule.RETENTION, ComplianceLinkSourceType.SIGNAL, "TEMP-002"),
        (ComplianceLinkSourceModule.LGPD, ComplianceLinkSourceType.ACTION, "AC-01"),
    ]
    for mod, typ, ref in modules:
        db_session.add(
            RequirementFindingLink(
                requirement_id=req.id,
                source_module=mod,
                source_type=typ,
                source_ref=ref,
            )
        )
    db_session.flush()
    db_session.refresh(req)

    assert len(req.finding_links) == 3


def test_finding_link_source_ref_is_weak_reference(db_session: Session) -> None:
    """source_ref é string livre — não há FK para tabelas externas."""
    req = _make_requirement(db_session)
    link = RequirementFindingLink(
        requirement_id=req.id,
        source_module=ComplianceLinkSourceModule.EXTERNAL,
        source_type=ComplianceLinkSourceType.DOCUMENT,
        source_ref="DOC-EXTERNO-9999",
    )
    db_session.add(link)
    db_session.flush()
    assert link.source_ref == "DOC-EXTERNO-9999"


def test_finding_link_cascade_delete(db_session: Session) -> None:
    req = _make_requirement(db_session)
    link = RequirementFindingLink(
        requirement_id=req.id,
        source_module=ComplianceLinkSourceModule.AUDIT,
        source_type=ComplianceLinkSourceType.FINDING,
        source_ref="DIAG-999",
    )
    db_session.add(link)
    db_session.flush()
    link_id = link.id

    db_session.delete(req)
    db_session.flush()

    from sqlalchemy import select

    remaining = db_session.scalar(
        select(RequirementFindingLink).where(RequirementFindingLink.id == link_id)
    )
    assert remaining is None


def test_all_risk_levels(db_session: Session) -> None:
    req = _make_requirement(db_session)
    for level in ComplianceLinkRiskLevel:
        link = RequirementFindingLink(
            requirement_id=req.id,
            source_module=ComplianceLinkSourceModule.MANUAL,
            source_type=ComplianceLinkSourceType.MANUAL_NOTE,
            source_ref=f"NOTE-{level.value}",
            risk_level=level,
        )
        db_session.add(link)
    db_session.flush()
    db_session.refresh(req)
    assert len(req.finding_links) == len(list(ComplianceLinkRiskLevel))


# ---------------------------------------------------------------------------
# Unicidade: uq_compliance_requirement_finding_link_source
# ---------------------------------------------------------------------------


def test_duplicate_link_raises_integrity_error(db_session: Session) -> None:
    req = _make_requirement(db_session)
    kwargs = dict(
        requirement_id=req.id,
        source_module=ComplianceLinkSourceModule.AUDIT,
        source_type=ComplianceLinkSourceType.FINDING,
        source_ref="DIAG-DUP",
    )
    db_session.add(RequirementFindingLink(**kwargs))
    db_session.flush()

    db_session.add(RequirementFindingLink(**kwargs))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_same_source_ref_different_requirement_is_allowed(db_session: Session) -> None:
    req_a = _make_requirement(db_session, "UQ_REQ_A")
    req_b = _make_requirement(db_session, "UQ_REQ_B")
    db_session.add(RequirementFindingLink(
        requirement_id=req_a.id,
        source_module=ComplianceLinkSourceModule.AUDIT,
        source_type=ComplianceLinkSourceType.FINDING,
        source_ref="SHARED-REF",
    ))
    db_session.add(RequirementFindingLink(
        requirement_id=req_b.id,
        source_module=ComplianceLinkSourceModule.AUDIT,
        source_type=ComplianceLinkSourceType.FINDING,
        source_ref="SHARED-REF",
    ))
    db_session.flush()  # deve passar sem IntegrityError


def test_same_requirement_source_ref_different_source_type_is_allowed(db_session: Session) -> None:
    req = _make_requirement(db_session)
    db_session.add(RequirementFindingLink(
        requirement_id=req.id,
        source_module=ComplianceLinkSourceModule.AUDIT,
        source_type=ComplianceLinkSourceType.FINDING,
        source_ref="SAME-REF",
    ))
    db_session.add(RequirementFindingLink(
        requirement_id=req.id,
        source_module=ComplianceLinkSourceModule.AUDIT,
        source_type=ComplianceLinkSourceType.DIAGNOSIS,
        source_ref="SAME-REF",
    ))
    db_session.flush()  # source_type diferente → não é duplicata


def test_same_requirement_source_ref_different_source_module_is_allowed(
    db_session: Session,
) -> None:
    req = _make_requirement(db_session)
    db_session.add(RequirementFindingLink(
        requirement_id=req.id,
        source_module=ComplianceLinkSourceModule.AUDIT,
        source_type=ComplianceLinkSourceType.FINDING,
        source_ref="SAME-REF",
    ))
    db_session.add(RequirementFindingLink(
        requirement_id=req.id,
        source_module=ComplianceLinkSourceModule.RETENTION,
        source_type=ComplianceLinkSourceType.FINDING,
        source_ref="SAME-REF",
    ))
    db_session.flush()  # source_module diferente → não é duplicata
