"""Testes do schema relacional do módulo compliance."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.compliance.enums import (
    DeadlineUnit,
    PolicyDocumentKind,
    RequirementClassification,
    RequirementSource,
    RequirementStage,
    ServentiaClass,
)
from app.modules.compliance.models import (
    ComplianceEvidenceTemplate,
    CompliancePolicyDocument,
    ComplianceRequirement,
    ComplianceRequirementDeadline,
    ComplianceRequirementPolicy,
)
from app.modules.compliance.seed import run_seed


def _make_requirement(code: str = "REQ_TEST") -> ComplianceRequirement:
    return ComplianceRequirement(
        code=code,
        source=RequirementSource.MATRIZ_INOVA,
        article_label="Teste",
        article_text="Texto",
        classification=RequirementClassification.COMPLEMENTAR_GOVERNANCA,
        stage=RequirementStage.NAO_APLICAVEL,
    )


def _make_policy(code: str = "POL_TEST") -> CompliancePolicyDocument:
    return CompliancePolicyDocument(
        code=code,
        title="Política Teste",
        kind=PolicyDocumentKind.POLITICA,
        classification=RequirementClassification.COMPLEMENTAR_GOVERNANCA,
        inova_filename="test.docx",
    )


def test_requirement_relationships_after_seed(db_session: Session) -> None:
    run_seed(db_session)
    db_session.commit()

    req = db_session.scalar(
        select(ComplianceRequirement).where(ComplianceRequirement.code == "ART_3_CAPUT")
    )
    assert req is not None
    assert len(req.deadlines) == 3
    assert {d.serventia_class for d in req.deadlines} == {
        ServentiaClass.C1,
        ServentiaClass.C2,
        ServentiaClass.C3,
    }
    assert len(req.evidence_templates) >= 3
    assert len(req.policy_links) >= 1


def test_policy_relationships_after_seed(db_session: Session) -> None:
    run_seed(db_session)
    db_session.commit()

    psi = db_session.scalar(
        select(CompliancePolicyDocument).where(CompliancePolicyDocument.code == "PSI")
    )
    assert psi is not None
    assert len(psi.requirement_links) >= 5


def test_requirement_unique_code(db_session: Session) -> None:
    db_session.add(_make_requirement("DUPLICATE"))
    db_session.commit()
    db_session.add(_make_requirement("DUPLICATE"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_policy_unique_code(db_session: Session) -> None:
    db_session.add(_make_policy("POL_DUP"))
    db_session.commit()
    db_session.add(_make_policy("POL_DUP"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_requirement_policy_link_unique(db_session: Session) -> None:
    req = _make_requirement("REQ_LINK")
    pol = _make_policy("POL_LINK")
    db_session.add_all([req, pol])
    db_session.commit()

    db_session.add(
        ComplianceRequirementPolicy(
            requirement_id=req.id,
            policy_id=pol.id,
            policy_section_notes="seção 1",
        )
    )
    db_session.commit()

    db_session.add(
        ComplianceRequirementPolicy(
            requirement_id=req.id,
            policy_id=pol.id,
            policy_section_notes="seção 1",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_requirement_policy_distinct_section_notes_allowed(db_session: Session) -> None:
    req = _make_requirement("REQ_LINK2")
    pol = _make_policy("POL_LINK2")
    db_session.add_all([req, pol])
    db_session.commit()

    db_session.add(
        ComplianceRequirementPolicy(
            requirement_id=req.id,
            policy_id=pol.id,
            policy_section_notes="seção 1",
        )
    )
    db_session.add(
        ComplianceRequirementPolicy(
            requirement_id=req.id,
            policy_id=pol.id,
            policy_section_notes="seção 2",
        )
    )
    db_session.commit()


def test_deadline_unique_per_class(db_session: Session) -> None:
    req = _make_requirement("REQ_DEAD")
    db_session.add(req)
    db_session.commit()
    db_session.add(
        ComplianceRequirementDeadline(
            requirement_id=req.id,
            serventia_class=ServentiaClass.C3,
            value=90,
            unit=DeadlineUnit.DIAS,
            stage_label="Etapa 1",
        )
    )
    db_session.commit()
    db_session.add(
        ComplianceRequirementDeadline(
            requirement_id=req.id,
            serventia_class=ServentiaClass.C3,
            value=120,
            unit=DeadlineUnit.DIAS,
            stage_label="Etapa 1",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_evidence_template_unique_sort_order(db_session: Session) -> None:
    req = _make_requirement("REQ_EV")
    db_session.add(req)
    db_session.commit()
    db_session.add(
        ComplianceEvidenceTemplate(
            requirement_id=req.id,
            description="evidência 1",
            sort_order=1,
        )
    )
    db_session.commit()
    db_session.add(
        ComplianceEvidenceTemplate(
            requirement_id=req.id,
            description="evidência 1 duplicada",
            sort_order=1,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_enums_persist_correctly(db_session: Session) -> None:
    req = _make_requirement("REQ_ENUM")
    req.source = RequirementSource.LGPD
    req.classification = RequirementClassification.OBRIGATORIO_LGPD
    req.stage = RequirementStage.ETAPA_3_4
    db_session.add(req)
    db_session.commit()

    fetched = db_session.scalar(
        select(ComplianceRequirement).where(ComplianceRequirement.code == "REQ_ENUM")
    )
    assert fetched is not None
    assert fetched.source == RequirementSource.LGPD
    assert fetched.classification == RequirementClassification.OBRIGATORIO_LGPD
    assert fetched.stage == RequirementStage.ETAPA_3_4
