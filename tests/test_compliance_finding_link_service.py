"""Testes do service de RequirementFindingLink."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.compliance import service
from app.modules.compliance.enums import (
    ComplianceLinkRiskLevel,
    ComplianceLinkSourceModule,
    ComplianceLinkSourceType,
    RequirementClassification,
    RequirementSource,
    RequirementStage,
)
from app.modules.compliance.models import ComplianceRequirement
from app.modules.compliance.schemas import (
    RequirementFindingLinkCreate,
    RequirementFindingLinkUpdate,
)


def _seed_requirement(db: Session, code: str = "SVC_LINK_ART_12") -> ComplianceRequirement:
    req = ComplianceRequirement(
        code=code,
        source=RequirementSource.PROV_213,
        article_label="Art. 12 — Service Link Test",
        article_text="Texto de teste de vínculo.",
        classification=RequirementClassification.OBRIGATORIO_PROVIMENTO,
        stage=RequirementStage.ETAPA_1,
    )
    db.add(req)
    db.flush()
    return req


def _base_payload(**kwargs) -> RequirementFindingLinkCreate:
    defaults = dict(
        requirement_code="SVC_LINK_ART_12",
        source_module=ComplianceLinkSourceModule.AUDIT,
        source_type=ComplianceLinkSourceType.FINDING,
        source_ref="DIAG-004",
    )
    defaults.update(kwargs)
    return RequirementFindingLinkCreate(**defaults)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def test_create_link_existing_requirement(db_session: Session) -> None:
    _seed_requirement(db_session)
    payload = _base_payload()
    link = service.create_finding_link(db_session, payload)

    assert link.id is not None
    assert link.source_module == ComplianceLinkSourceModule.AUDIT
    assert link.source_type == ComplianceLinkSourceType.FINDING
    assert link.source_ref == "DIAG-004"


def test_create_link_nonexistent_requirement_raises_404(db_session: Session) -> None:
    payload = _base_payload(requirement_code="NAO_EXISTE")
    with pytest.raises(HTTPException) as exc_info:
        service.create_finding_link(db_session, payload)
    assert exc_info.value.status_code == 404


def test_create_link_with_all_optional_fields(db_session: Session) -> None:
    _seed_requirement(db_session)
    payload = _base_payload(
        title="Achado relevante",
        link_reason="Impacto direto no requisito.",
        risk_level=ComplianceLinkRiskLevel.HIGH,
        notes="Verificar urgente.",
    )
    link = service.create_finding_link(db_session, payload)

    assert link.title == "Achado relevante"
    assert link.link_reason == "Impacto direto no requisito."
    assert link.risk_level == ComplianceLinkRiskLevel.HIGH
    assert link.notes == "Verificar urgente."


def test_create_link_retention_module(db_session: Session) -> None:
    _seed_requirement(db_session)
    payload = _base_payload(
        source_module=ComplianceLinkSourceModule.RETENTION,
        source_type=ComplianceLinkSourceType.SIGNAL,
        source_ref="TEMP-002",
    )
    link = service.create_finding_link(db_session, payload)
    assert link.source_module == ComplianceLinkSourceModule.RETENTION


def test_create_link_lgpd_module(db_session: Session) -> None:
    _seed_requirement(db_session)
    payload = _base_payload(
        source_module=ComplianceLinkSourceModule.LGPD,
        source_type=ComplianceLinkSourceType.ACTION,
        source_ref="AC-01",
    )
    link = service.create_finding_link(db_session, payload)
    assert link.source_module == ComplianceLinkSourceModule.LGPD


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def test_list_links_no_filter(db_session: Session) -> None:
    _seed_requirement(db_session)
    for ref in ["X-001", "X-002", "X-003"]:
        db_session.add(
            service.create_finding_link(
                db_session,
                _base_payload(source_ref=ref),
            )
        )
    links = service.list_finding_links(db_session)
    assert len(links) >= 3


def test_list_links_filter_by_requirement_code(db_session: Session) -> None:
    _seed_requirement(db_session, "REQ_A")
    _seed_requirement(db_session, "REQ_B")
    service.create_finding_link(
        db_session, RequirementFindingLinkCreate(
            requirement_code="REQ_A",
            source_module=ComplianceLinkSourceModule.AUDIT,
            source_type=ComplianceLinkSourceType.FINDING,
            source_ref="A-001",
        )
    )
    service.create_finding_link(
        db_session, RequirementFindingLinkCreate(
            requirement_code="REQ_B",
            source_module=ComplianceLinkSourceModule.AUDIT,
            source_type=ComplianceLinkSourceType.FINDING,
            source_ref="B-001",
        )
    )

    result = service.list_finding_links(db_session, requirement_code="REQ_A")
    assert all(lnk.requirement.code == "REQ_A" for lnk in result)
    assert len(result) == 1


def test_list_links_filter_by_source_module(db_session: Session) -> None:
    _seed_requirement(db_session)
    service.create_finding_link(db_session, _base_payload(
        source_module=ComplianceLinkSourceModule.AUDIT, source_ref="A-1"
    ))
    service.create_finding_link(db_session, _base_payload(
        source_module=ComplianceLinkSourceModule.RETENTION,
        source_type=ComplianceLinkSourceType.SIGNAL,
        source_ref="R-1",
    ))

    result = service.list_finding_links(
        db_session, source_module=ComplianceLinkSourceModule.RETENTION
    )
    assert all(lnk.source_module == ComplianceLinkSourceModule.RETENTION for lnk in result)


def test_list_links_filter_by_source_type(db_session: Session) -> None:
    _seed_requirement(db_session)
    service.create_finding_link(db_session, _base_payload(
        source_type=ComplianceLinkSourceType.FINDING, source_ref="F-1"
    ))
    service.create_finding_link(db_session, _base_payload(
        source_module=ComplianceLinkSourceModule.LGPD,
        source_type=ComplianceLinkSourceType.ACTION,
        source_ref="AC-2",
    ))

    result = service.list_finding_links(
        db_session, source_type=ComplianceLinkSourceType.ACTION
    )
    assert all(lnk.source_type == ComplianceLinkSourceType.ACTION for lnk in result)


def test_list_links_filter_by_source_ref(db_session: Session) -> None:
    _seed_requirement(db_session)
    service.create_finding_link(db_session, _base_payload(source_ref="TARGET-REF"))
    service.create_finding_link(db_session, _base_payload(source_ref="OTHER-REF"))

    result = service.list_finding_links(db_session, source_ref="TARGET-REF")
    assert len(result) == 1
    assert result[0].source_ref == "TARGET-REF"


def test_list_links_filter_by_risk_level(db_session: Session) -> None:
    _seed_requirement(db_session)
    service.create_finding_link(db_session, _base_payload(
        source_ref="H-1", risk_level=ComplianceLinkRiskLevel.HIGH
    ))
    service.create_finding_link(db_session, _base_payload(
        source_ref="L-1", risk_level=ComplianceLinkRiskLevel.LOW
    ))

    result = service.list_finding_links(db_session, risk_level=ComplianceLinkRiskLevel.HIGH)
    assert all(lnk.risk_level == ComplianceLinkRiskLevel.HIGH for lnk in result)


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


def test_get_link_existing(db_session: Session) -> None:
    _seed_requirement(db_session)
    created = service.create_finding_link(db_session, _base_payload())
    fetched = service.get_finding_link(db_session, created.id)
    assert fetched is not None
    assert fetched.id == created.id


def test_get_link_nonexistent_returns_none(db_session: Session) -> None:
    result = service.get_finding_link(db_session, 999_999)
    assert result is None


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


def test_update_link_notes(db_session: Session) -> None:
    _seed_requirement(db_session)
    link = service.create_finding_link(db_session, _base_payload())

    updated = service.update_finding_link(
        db_session, link.id, RequirementFindingLinkUpdate(notes="Nova nota.")
    )
    assert updated.notes == "Nova nota."


def test_update_link_risk_level(db_session: Session) -> None:
    _seed_requirement(db_session)
    link = service.create_finding_link(db_session, _base_payload())

    updated = service.update_finding_link(
        db_session,
        link.id,
        RequirementFindingLinkUpdate(risk_level=ComplianceLinkRiskLevel.CRITICAL),
    )
    assert updated.risk_level == ComplianceLinkRiskLevel.CRITICAL


def test_update_link_link_reason(db_session: Session) -> None:
    _seed_requirement(db_session)
    link = service.create_finding_link(db_session, _base_payload())

    updated = service.update_finding_link(
        db_session,
        link.id,
        RequirementFindingLinkUpdate(link_reason="Razão atualizada."),
    )
    assert updated.link_reason == "Razão atualizada."


def test_update_link_does_not_change_requirement(db_session: Session) -> None:
    _seed_requirement(db_session)
    link = service.create_finding_link(db_session, _base_payload())
    original_req_id = link.requirement_id

    # PATCH só pode alterar campos permitidos; requirement_id não existe no update schema
    service.update_finding_link(
        db_session, link.id, RequirementFindingLinkUpdate(notes="Mudei nota.")
    )
    assert link.requirement_id == original_req_id


def test_update_link_nonexistent_raises_404(db_session: Session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        service.update_finding_link(
            db_session, 999_999, RequirementFindingLinkUpdate(notes="x")
        )
    assert exc_info.value.status_code == 404


def test_update_link_rejects_null_source_module(db_session: Session) -> None:
    with pytest.raises(ValueError):
        RequirementFindingLinkUpdate(source_module=None)


def test_update_link_rejects_null_source_type(db_session: Session) -> None:
    with pytest.raises(ValueError):
        RequirementFindingLinkUpdate(source_type=None)


def test_update_link_rejects_null_source_ref(db_session: Session) -> None:
    with pytest.raises(ValueError):
        RequirementFindingLinkUpdate(source_ref=None)


def test_update_link_allows_clearing_risk_level(db_session: Session) -> None:
    _seed_requirement(db_session)
    link = service.create_finding_link(
        db_session, _base_payload(risk_level=ComplianceLinkRiskLevel.HIGH)
    )
    updated = service.update_finding_link(
        db_session, link.id, RequirementFindingLinkUpdate(risk_level=None)
    )
    assert updated.risk_level is None


def test_update_link_source_ref(db_session: Session) -> None:
    _seed_requirement(db_session)
    link = service.create_finding_link(db_session, _base_payload(source_ref="OLD-REF"))

    updated = service.update_finding_link(
        db_session,
        link.id,
        RequirementFindingLinkUpdate(source_ref="NEW-REF"),
    )
    assert updated.source_ref == "NEW-REF"


# ---------------------------------------------------------------------------
# Unicidade — service retorna 400 em duplicata
# ---------------------------------------------------------------------------


def test_create_duplicate_link_raises_400(db_session: Session) -> None:
    _seed_requirement(db_session)
    service.create_finding_link(db_session, _base_payload(source_ref="DUP-SVC"))
    with pytest.raises(HTTPException) as exc_info:
        service.create_finding_link(db_session, _base_payload(source_ref="DUP-SVC"))
    assert exc_info.value.status_code == 400
    assert "mesma origem" in exc_info.value.detail


def test_same_source_ref_different_requirement_allowed_in_service(db_session: Session) -> None:
    _seed_requirement(db_session, "SVC_UQ_A")
    _seed_requirement(db_session, "SVC_UQ_B")
    service.create_finding_link(db_session, RequirementFindingLinkCreate(
        requirement_code="SVC_UQ_A",
        source_module=ComplianceLinkSourceModule.AUDIT,
        source_type=ComplianceLinkSourceType.FINDING,
        source_ref="SHARED",
    ))
    link_b = service.create_finding_link(db_session, RequirementFindingLinkCreate(
        requirement_code="SVC_UQ_B",
        source_module=ComplianceLinkSourceModule.AUDIT,
        source_type=ComplianceLinkSourceType.FINDING,
        source_ref="SHARED",
    ))
    assert link_b.id is not None


def test_same_requirement_different_source_type_allowed_in_service(db_session: Session) -> None:
    _seed_requirement(db_session)
    service.create_finding_link(db_session, _base_payload(
        source_type=ComplianceLinkSourceType.FINDING, source_ref="MULTI-TYPE"
    ))
    link2 = service.create_finding_link(db_session, _base_payload(
        source_type=ComplianceLinkSourceType.DIAGNOSIS, source_ref="MULTI-TYPE"
    ))
    assert link2.id is not None


def test_same_requirement_different_source_module_allowed_in_service(db_session: Session) -> None:
    _seed_requirement(db_session)
    service.create_finding_link(db_session, _base_payload(
        source_module=ComplianceLinkSourceModule.AUDIT, source_ref="MULTI-MOD"
    ))
    link2 = service.create_finding_link(db_session, _base_payload(
        source_module=ComplianceLinkSourceModule.LGPD,
        source_type=ComplianceLinkSourceType.ACTION,
        source_ref="MULTI-MOD",
    ))
    assert link2.id is not None
