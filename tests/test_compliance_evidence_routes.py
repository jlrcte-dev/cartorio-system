"""Testes dos endpoints REST de ComplianceEvidence."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.modules.compliance.enums import (
    RequirementClassification,
    RequirementSource,
    RequirementStage,
)
from app.modules.compliance.models import (
    ComplianceEvidenceTemplate,
    ComplianceRequirement,
)


def _seed_requirement(db: Session, code: str = "RT_ART_5") -> ComplianceRequirement:
    req = ComplianceRequirement(
        code=code,
        source=RequirementSource.PROV_213,
        article_label="Art. 5 — Route Test",
        article_text="Texto de teste.",
        classification=RequirementClassification.OBRIGATORIO_PROVIMENTO,
        stage=RequirementStage.ETAPA_1,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def _seed_template(db: Session, requirement: ComplianceRequirement) -> ComplianceEvidenceTemplate:
    tpl = ComplianceEvidenceTemplate(
        requirement_id=requirement.id,
        description="Template de teste.",
        sort_order=1,
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


@pytest.fixture
def seeded_client(client: TestClient, test_engine):  # type: ignore[no-untyped-def]
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    with SessionLocal() as session:
        _seed_requirement(session, "RT_ART_5")
        _seed_requirement(session, "RT_ART_12")
    return client


@pytest.fixture
def seeded_client_with_template(client: TestClient, test_engine):  # type: ignore[no-untyped-def]
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    with SessionLocal() as session:
        req = _seed_requirement(session, "RT_ART_5")
        req2 = _seed_requirement(session, "RT_ART_12")
        _seed_template(session, req)
        _seed_template(session, req2)
    return client


def _evidence_payload(**overrides):  # type: ignore[no-untyped-def]
    base = {
        "requirement_code": "RT_ART_5",
        "title": "Evidência de rota",
        "description": "Descrição da evidência registrada via rota.",
        "evidence_type": "DOCUMENT",
        "status": "COLLECTED",
        "source_module": "MANUAL",
    }
    base.update(overrides)
    return base


class TestPostEvidence:
    def test_create_evidence_returns_201(self, seeded_client: TestClient) -> None:
        res = seeded_client.post("/api/v1/compliance/evidences", json=_evidence_payload())
        assert res.status_code == 201
        body = res.json()
        assert body["requirement_code"] == "RT_ART_5"
        assert body["title"] == "Evidência de rota"
        assert body["status"] == "COLLECTED"
        assert "id" in body

    def test_evidence_note_is_conservative(self, seeded_client: TestClient) -> None:
        res = seeded_client.post("/api/v1/compliance/evidences", json=_evidence_payload())
        assert res.status_code == 201
        body = res.json()
        assert "evidence_note" in body
        assert "não representa declaração automática" in body["evidence_note"]

    def test_create_with_nonexistent_requirement_returns_404(
        self, seeded_client: TestClient
    ) -> None:
        res = seeded_client.post(
            "/api/v1/compliance/evidences",
            json=_evidence_payload(requirement_code="NAO_EXISTE"),
        )
        assert res.status_code == 404

    def test_create_with_incompatible_template_returns_400(
        self, seeded_client_with_template: TestClient, test_engine
    ) -> None:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        with SessionLocal() as session:
            tpl = (
                session.query(ComplianceEvidenceTemplate)
                .join(ComplianceRequirement)
                .filter(ComplianceRequirement.code == "RT_ART_12")
                .first()
            )
            assert tpl is not None
            tpl_id = tpl.id

        res = seeded_client_with_template.post(
            "/api/v1/compliance/evidences",
            json=_evidence_payload(requirement_code="RT_ART_5", evidence_template_id=tpl_id),
        )
        assert res.status_code == 400


class TestGetEvidenceList:
    def test_list_empty(self, seeded_client: TestClient) -> None:
        res = seeded_client.get("/api/v1/compliance/evidences")
        assert res.status_code == 200
        assert res.json() == []

    def test_list_returns_created(self, seeded_client: TestClient) -> None:
        seeded_client.post("/api/v1/compliance/evidences", json=_evidence_payload())
        seeded_client.post(
            "/api/v1/compliance/evidences",
            json=_evidence_payload(requirement_code="RT_ART_12", title="Segunda evidência"),
        )
        res = seeded_client.get("/api/v1/compliance/evidences")
        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_filter_by_requirement_code(self, seeded_client: TestClient) -> None:
        seeded_client.post("/api/v1/compliance/evidences", json=_evidence_payload())
        seeded_client.post(
            "/api/v1/compliance/evidences",
            json=_evidence_payload(requirement_code="RT_ART_12", title="Outra"),
        )
        res = seeded_client.get(
            "/api/v1/compliance/evidences", params={"requirement_code": "RT_ART_5"}
        )
        assert res.status_code == 200
        body = res.json()
        assert len(body) == 1
        assert body[0]["requirement_code"] == "RT_ART_5"

    def test_filter_by_status(self, seeded_client: TestClient) -> None:
        seeded_client.post(
            "/api/v1/compliance/evidences",
            json=_evidence_payload(status="COLLECTED"),
        )
        seeded_client.post(
            "/api/v1/compliance/evidences",
            json=_evidence_payload(title="Aceita", status="ACCEPTED"),
        )
        res = seeded_client.get("/api/v1/compliance/evidences", params={"status": "ACCEPTED"})
        assert res.status_code == 200
        body = res.json()
        assert len(body) == 1
        assert body[0]["status"] == "ACCEPTED"

    def test_filter_by_source_module(self, seeded_client: TestClient) -> None:
        seeded_client.post(
            "/api/v1/compliance/evidences",
            json=_evidence_payload(source_module="MANUAL"),
        )
        seeded_client.post(
            "/api/v1/compliance/evidences",
            json=_evidence_payload(
                title="De auditoria",
                source_module="AUDIT",
                source_type="FINDING",
                source_ref="DIAG-001",
            ),
        )
        res = seeded_client.get("/api/v1/compliance/evidences", params={"source_module": "AUDIT"})
        assert res.status_code == 200
        body = res.json()
        assert len(body) == 1
        assert body[0]["source_module"] == "AUDIT"


class TestGetEvidenceDetail:
    def test_get_existing_returns_200(self, seeded_client: TestClient) -> None:
        created = seeded_client.post(
            "/api/v1/compliance/evidences", json=_evidence_payload()
        ).json()
        res = seeded_client.get(f"/api/v1/compliance/evidences/{created['id']}")
        assert res.status_code == 200
        body = res.json()
        assert body["id"] == created["id"]
        assert body["requirement_code"] == "RT_ART_5"
        assert "evidence_note" in body

    def test_get_nonexistent_returns_404(self, seeded_client: TestClient) -> None:
        res = seeded_client.get("/api/v1/compliance/evidences/99999")
        assert res.status_code == 404


class TestPatchEvidence:
    def test_patch_status(self, seeded_client: TestClient) -> None:
        created = seeded_client.post(
            "/api/v1/compliance/evidences", json=_evidence_payload()
        ).json()
        res = seeded_client.patch(
            f"/api/v1/compliance/evidences/{created['id']}",
            json={"status": "ACCEPTED"},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "ACCEPTED"

    def test_patch_notes(self, seeded_client: TestClient) -> None:
        created = seeded_client.post(
            "/api/v1/compliance/evidences", json=_evidence_payload()
        ).json()
        res = seeded_client.patch(
            f"/api/v1/compliance/evidences/{created['id']}",
            json={"notes": "Revisada em 06/05/2026."},
        )
        assert res.status_code == 200
        assert res.json()["notes"] == "Revisada em 06/05/2026."

    def test_patch_nonexistent_returns_404(self, seeded_client: TestClient) -> None:
        res = seeded_client.patch("/api/v1/compliance/evidences/99999", json={"status": "REJECTED"})
        assert res.status_code == 404


class TestDeleteEvidence:
    def test_delete_not_exists_returns_404_or_405(self, seeded_client: TestClient) -> None:
        created = seeded_client.post(
            "/api/v1/compliance/evidences", json=_evidence_payload()
        ).json()
        res = seeded_client.delete(f"/api/v1/compliance/evidences/{created['id']}")
        assert res.status_code in (404, 405)

    def test_delete_endpoint_not_registered(self) -> None:
        from app.modules.compliance.router import router

        for route in router.routes:
            methods = getattr(route, "methods", None) or set()
            path = getattr(route, "path", "")
            if "evidences" in path:
                assert "DELETE" not in methods, (
                    f"DELETE encontrado em {path} — proibido nesta sprint"
                )
