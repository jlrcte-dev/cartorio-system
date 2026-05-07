"""Testes de model para ComplianceEvidence."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.compliance.enums import (
    ComplianceEvidenceSourceModule,
    ComplianceEvidenceStatus,
    ComplianceEvidenceType,
    RequirementClassification,
    RequirementSource,
    RequirementStage,
)
from app.modules.compliance.models import (
    ComplianceEvidence,
    ComplianceEvidenceTemplate,
    ComplianceRequirement,
)


def _make_requirement(db: Session, code: str = "ART_5_TEST") -> ComplianceRequirement:
    req = ComplianceRequirement(
        code=code,
        source=RequirementSource.PROV_213,
        article_label="Art. 5 — Teste",
        article_text="Texto de teste do artigo 5.",
        classification=RequirementClassification.OBRIGATORIO_PROVIMENTO,
        stage=RequirementStage.ETAPA_1,
    )
    db.add(req)
    db.flush()
    return req


def _make_template(db: Session, requirement: ComplianceRequirement) -> ComplianceEvidenceTemplate:
    tpl = ComplianceEvidenceTemplate(
        requirement_id=requirement.id,
        description="Ata de reunião assinada pela DPO.",
        sort_order=1,
    )
    db.add(tpl)
    db.flush()
    return tpl


def test_evidence_can_be_created_linked_to_requirement(db_session: Session) -> None:
    req = _make_requirement(db_session)
    ev = ComplianceEvidence(
        requirement_id=req.id,
        title="Ata de reunião DPO",
        description="Reunião realizada em 01/05/2026.",
        evidence_type=ComplianceEvidenceType.MEETING_MINUTES,
        status=ComplianceEvidenceStatus.COLLECTED,
        source_module=ComplianceEvidenceSourceModule.MANUAL,
    )
    db_session.add(ev)
    db_session.flush()

    assert ev.id is not None
    assert ev.requirement_id == req.id
    assert ev.evidence_template_id is None


def test_evidence_can_be_created_with_compatible_template(db_session: Session) -> None:
    req = _make_requirement(db_session)
    tpl = _make_template(db_session, req)

    ev = ComplianceEvidence(
        requirement_id=req.id,
        evidence_template_id=tpl.id,
        title="Ata referenciando template",
        description="Evidência vinculada ao template sugerido.",
        evidence_type=ComplianceEvidenceType.MEETING_MINUTES,
        status=ComplianceEvidenceStatus.COLLECTED,
        source_module=ComplianceEvidenceSourceModule.MANUAL,
    )
    db_session.add(ev)
    db_session.flush()

    assert ev.evidence_template_id == tpl.id
    assert ev.template is not None
    assert ev.template.id == tpl.id


def test_evidence_relationship_to_requirement(db_session: Session) -> None:
    req = _make_requirement(db_session)
    ev = ComplianceEvidence(
        requirement_id=req.id,
        title="Política interna de DPO",
        description="Política aprovada em reunião.",
        evidence_type=ComplianceEvidenceType.POLICY,
        status=ComplianceEvidenceStatus.UNDER_REVIEW,
        source_module=ComplianceEvidenceSourceModule.MANUAL,
    )
    db_session.add(ev)
    db_session.flush()

    assert ev.requirement is not None
    assert ev.requirement.code == "ART_5_TEST"


def test_enums_persist_correctly(db_session: Session) -> None:
    req = _make_requirement(db_session)
    ev = ComplianceEvidence(
        requirement_id=req.id,
        title="Log de sistema",
        description="Log gerado pelo sistema de acesso.",
        evidence_type=ComplianceEvidenceType.LOG,
        status=ComplianceEvidenceStatus.ACCEPTED,
        source_module=ComplianceEvidenceSourceModule.SYSTEM,
        source_type="ACCESS_LOG",
        source_ref="LOG-2026-001",
    )
    db_session.add(ev)
    db_session.flush()
    db_session.expire(ev)

    fetched = db_session.get(ComplianceEvidence, ev.id)
    assert fetched is not None
    assert fetched.evidence_type == ComplianceEvidenceType.LOG
    assert fetched.status == ComplianceEvidenceStatus.ACCEPTED
    assert fetched.source_module == ComplianceEvidenceSourceModule.SYSTEM
    assert fetched.source_ref == "LOG-2026-001"


def test_evidence_weak_reference_fields(db_session: Session) -> None:
    """Referência fraca para audit não cria FK real — só campos de texto."""
    req = _make_requirement(db_session)
    ev = ComplianceEvidence(
        requirement_id=req.id,
        title="Finding de auditoria referenciado",
        description="Diagnóstico DIAG-004 como referência de evidência.",
        evidence_type=ComplianceEvidenceType.REPORT,
        status=ComplianceEvidenceStatus.UNDER_REVIEW,
        source_module=ComplianceEvidenceSourceModule.AUDIT,
        source_type="FINDING",
        source_ref="DIAG-004",
    )
    db_session.add(ev)
    db_session.flush()

    assert ev.source_module == ComplianceEvidenceSourceModule.AUDIT
    assert ev.source_type == "FINDING"
    assert ev.source_ref == "DIAG-004"


def test_multiple_evidences_for_same_requirement(db_session: Session) -> None:
    req = _make_requirement(db_session)
    for i in range(3):
        ev = ComplianceEvidence(
            requirement_id=req.id,
            title=f"Evidência {i}",
            description=f"Descrição da evidência {i}.",
            evidence_type=ComplianceEvidenceType.DOCUMENT,
            status=ComplianceEvidenceStatus.COLLECTED,
            source_module=ComplianceEvidenceSourceModule.MANUAL,
        )
        db_session.add(ev)
    db_session.flush()

    db_session.refresh(req)
    assert len(req.evidences) == 3
