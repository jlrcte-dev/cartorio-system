"""Testes do service de ComplianceEvidence."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.compliance import service
from app.modules.compliance.enums import (
    ComplianceEvidenceSourceModule,
    ComplianceEvidenceStatus,
    ComplianceEvidenceType,
    RequirementClassification,
    RequirementSource,
    RequirementStage,
)
from app.modules.compliance.models import (
    ComplianceEvidenceTemplate,
    ComplianceRequirement,
)
from app.modules.compliance.schemas import ComplianceEvidenceCreate, ComplianceEvidenceUpdate


def _seed_requirement(db: Session, code: str = "SVC_ART_5") -> ComplianceRequirement:
    req = ComplianceRequirement(
        code=code,
        source=RequirementSource.PROV_213,
        article_label="Art. 5 — Service Test",
        article_text="Texto de teste.",
        classification=RequirementClassification.OBRIGATORIO_PROVIMENTO,
        stage=RequirementStage.ETAPA_1,
    )
    db.add(req)
    db.flush()
    return req


def _seed_template(db: Session, requirement: ComplianceRequirement) -> ComplianceEvidenceTemplate:
    tpl = ComplianceEvidenceTemplate(
        requirement_id=requirement.id,
        description="Template de evidência de teste.",
        sort_order=1,
    )
    db.add(tpl)
    db.flush()
    return tpl


def _create_payload(**overrides) -> ComplianceEvidenceCreate:  # type: ignore[no-untyped-def]
    defaults = dict(
        requirement_code="SVC_ART_5",
        title="Evidência de teste",
        description="Descrição da evidência de teste.",
        evidence_type=ComplianceEvidenceType.DOCUMENT,
        status=ComplianceEvidenceStatus.COLLECTED,
        source_module=ComplianceEvidenceSourceModule.MANUAL,
    )
    defaults.update(overrides)
    return ComplianceEvidenceCreate(**defaults)


class TestCreateEvidence:
    def test_create_with_valid_requirement_code(self, db_session: Session) -> None:
        _seed_requirement(db_session)
        payload = _create_payload()
        ev = service.create_evidence(db_session, payload)
        assert ev.id is not None
        assert ev.title == "Evidência de teste"
        assert ev.status == ComplianceEvidenceStatus.COLLECTED
        assert ev.source_module == ComplianceEvidenceSourceModule.MANUAL

    def test_create_with_nonexistent_requirement_raises_404(self, db_session: Session) -> None:
        payload = _create_payload(requirement_code="NAO_EXISTE")
        with pytest.raises(HTTPException) as exc_info:
            service.create_evidence(db_session, payload)
        assert exc_info.value.status_code == 404

    def test_create_with_compatible_template(self, db_session: Session) -> None:
        req = _seed_requirement(db_session)
        tpl = _seed_template(db_session, req)
        payload = _create_payload(evidence_template_id=tpl.id)
        ev = service.create_evidence(db_session, payload)
        assert ev.evidence_template_id == tpl.id

    def test_create_with_incompatible_template_raises_400(self, db_session: Session) -> None:
        _seed_requirement(db_session, "SVC_ART_5")
        req2 = _seed_requirement(db_session, "SVC_ART_12")
        tpl_other = _seed_template(db_session, req2)
        payload = _create_payload(
            requirement_code="SVC_ART_5",
            evidence_template_id=tpl_other.id,
        )
        with pytest.raises(HTTPException) as exc_info:
            service.create_evidence(db_session, payload)
        assert exc_info.value.status_code == 400
        assert str(req2.id) in exc_info.value.detail

    def test_create_with_nonexistent_template_raises_400(self, db_session: Session) -> None:
        _seed_requirement(db_session)
        payload = _create_payload(evidence_template_id=99999)
        with pytest.raises(HTTPException) as exc_info:
            service.create_evidence(db_session, payload)
        assert exc_info.value.status_code == 400


class TestListEvidences:
    def _create_three(self, db: Session) -> None:
        _seed_requirement(db, "LIST_ART_1")
        _seed_requirement(db, "LIST_ART_2")
        service.create_evidence(
            db,
            _create_payload(
                requirement_code="LIST_ART_1",
                status=ComplianceEvidenceStatus.COLLECTED,
            ),
        )
        service.create_evidence(
            db,
            _create_payload(
                requirement_code="LIST_ART_1",
                status=ComplianceEvidenceStatus.ACCEPTED,
            ),
        )
        service.create_evidence(
            db,
            _create_payload(
                requirement_code="LIST_ART_2",
                status=ComplianceEvidenceStatus.COLLECTED,
                source_module=ComplianceEvidenceSourceModule.AUDIT,
            ),
        )

    def test_list_all(self, db_session: Session) -> None:
        self._create_three(db_session)
        results = service.list_evidences(db_session)
        assert len(results) == 3

    def test_filter_by_requirement_code(self, db_session: Session) -> None:
        self._create_three(db_session)
        results = service.list_evidences(db_session, requirement_code="LIST_ART_1")
        assert len(results) == 2
        assert all(ev.requirement.code == "LIST_ART_1" for ev in results)

    def test_filter_by_status(self, db_session: Session) -> None:
        self._create_three(db_session)
        results = service.list_evidences(db_session, status=ComplianceEvidenceStatus.ACCEPTED)
        assert len(results) == 1
        assert results[0].status == ComplianceEvidenceStatus.ACCEPTED

    def test_filter_by_source_module(self, db_session: Session) -> None:
        self._create_three(db_session)
        results = service.list_evidences(
            db_session, source_module=ComplianceEvidenceSourceModule.AUDIT
        )
        assert len(results) == 1
        assert results[0].source_module == ComplianceEvidenceSourceModule.AUDIT


class TestGetEvidence:
    def test_get_existing(self, db_session: Session) -> None:
        _seed_requirement(db_session)
        ev = service.create_evidence(db_session, _create_payload())
        found = service.get_evidence(db_session, ev.id)
        assert found is not None
        assert found.id == ev.id

    def test_get_nonexistent_returns_none(self, db_session: Session) -> None:
        result = service.get_evidence(db_session, 99999)
        assert result is None


class TestUpdateEvidence:
    def test_update_status(self, db_session: Session) -> None:
        _seed_requirement(db_session)
        ev = service.create_evidence(db_session, _create_payload())
        updated = service.update_evidence(
            db_session,
            ev.id,
            ComplianceEvidenceUpdate(status=ComplianceEvidenceStatus.ACCEPTED),
        )
        assert updated.status == ComplianceEvidenceStatus.ACCEPTED

    def test_update_notes(self, db_session: Session) -> None:
        _seed_requirement(db_session)
        ev = service.create_evidence(db_session, _create_payload())
        updated = service.update_evidence(
            db_session,
            ev.id,
            ComplianceEvidenceUpdate(notes="Revisada em 06/05/2026."),
        )
        assert updated.notes == "Revisada em 06/05/2026."

    def test_update_nonexistent_raises_404(self, db_session: Session) -> None:
        with pytest.raises(HTTPException) as exc_info:
            service.update_evidence(
                db_session,
                99999,
                ComplianceEvidenceUpdate(status=ComplianceEvidenceStatus.REJECTED),
            )
        assert exc_info.value.status_code == 404

    def test_update_with_incompatible_template_raises_400(self, db_session: Session) -> None:
        _seed_requirement(db_session, "UPD_ART_5")
        req2 = _seed_requirement(db_session, "UPD_ART_12")
        tpl_other = _seed_template(db_session, req2)

        ev = service.create_evidence(db_session, _create_payload(requirement_code="UPD_ART_5"))
        with pytest.raises(HTTPException) as exc_info:
            service.update_evidence(
                db_session,
                ev.id,
                ComplianceEvidenceUpdate(evidence_template_id=tpl_other.id),
            )
        assert exc_info.value.status_code == 400

    def test_update_does_not_change_requirement_id(self, db_session: Session) -> None:
        _seed_requirement(db_session)
        ev = service.create_evidence(db_session, _create_payload())
        original_req_id = ev.requirement_id
        service.update_evidence(
            db_session,
            ev.id,
            ComplianceEvidenceUpdate(title="Novo título"),
        )
        assert ev.requirement_id == original_req_id
