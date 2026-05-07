"""Testes de rotas REST para ComplianceRequirementStatus."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.compliance.enums import (
    ComplianceLinkRiskLevel,
    ComplianceLinkSourceModule,
    ComplianceLinkSourceType,
    RequirementClassification,
    RequirementSource,
    RequirementStage,
)
from app.modules.compliance.models import (
    ComplianceRequirement,
    RequirementFindingLink,
)

LIST_BASE = "/api/v1/compliance/requirement-statuses"
BULK_RECOMPUTE = "/api/v1/compliance/requirement-statuses/recompute"


def _seed_req(db: Session, code: str = "RT_ST_1") -> ComplianceRequirement:
    req = ComplianceRequirement(
        code=code,
        source=RequirementSource.PROV_213,
        article_label="Art. ST",
        article_text="Texto.",
        classification=RequirementClassification.OBRIGATORIO_PROVIMENTO,
        stage=RequirementStage.ETAPA_1,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
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
    db.commit()


# ---------------------------------------------------------------------------
# Listagem
# ---------------------------------------------------------------------------


def test_list_returns_200_empty(client: TestClient) -> None:
    resp = client.get(LIST_BASE)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_returns_status_with_disclaimer(
    client: TestClient, db_session: Session
) -> None:
    _seed_req(db_session, "RT_DISC")
    client.post("/api/v1/compliance/requirements/RT_DISC/status/recompute")

    resp = client.get(LIST_BASE)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert "disclaimer" in body[0]
    assert "indicativo" in body[0]["disclaimer"].lower()


def test_list_pagination_limit_too_high_returns_422(client: TestClient) -> None:
    resp = client.get(LIST_BASE, params={"limit": 9999})
    assert resp.status_code == 422


def test_list_pagination_limit_too_low_returns_422(client: TestClient) -> None:
    resp = client.get(LIST_BASE, params={"limit": 0})
    assert resp.status_code == 422


def test_list_pagination_offset_negative_returns_422(client: TestClient) -> None:
    resp = client.get(LIST_BASE, params={"offset": -1})
    assert resp.status_code == 422


def test_list_filter_by_status(client: TestClient, db_session: Session) -> None:
    _seed_req(db_session, "RT_FA")
    b = _seed_req(db_session, "RT_FB")
    _add_link(db_session, b, "FB-CRIT", ComplianceLinkRiskLevel.CRITICAL)
    client.post("/api/v1/compliance/requirements/RT_FA/status/recompute")
    client.post("/api/v1/compliance/requirements/RT_FB/status/recompute")

    resp = client.get(LIST_BASE, params={"status": "HAS_OPEN_FINDINGS"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["requirement_code"] == "RT_FB"


def test_list_filter_by_human_review_required(client: TestClient, db_session: Session) -> None:
    _seed_req(db_session, "RT_HRA")
    b = _seed_req(db_session, "RT_HRB")
    _add_link(db_session, b, "HRB-MED", ComplianceLinkRiskLevel.MEDIUM)
    client.post("/api/v1/compliance/requirements/RT_HRA/status/recompute")
    client.post("/api/v1/compliance/requirements/RT_HRB/status/recompute")

    resp = client.get(LIST_BASE, params={"human_review_required": "true"})
    assert resp.status_code == 200
    body = resp.json()
    assert all(item["human_review_required"] is True for item in body)
    assert len(body) == 1


# ---------------------------------------------------------------------------
# GET por requisito
# ---------------------------------------------------------------------------


def test_get_status_by_code_404_if_requirement_missing(client: TestClient) -> None:
    resp = client.get("/api/v1/compliance/requirements/NAO_EXISTE/status")
    assert resp.status_code == 404


def test_get_status_by_code_404_if_not_yet_computed(
    client: TestClient, db_session: Session
) -> None:
    _seed_req(db_session, "RT_NOTYET")
    resp = client.get("/api/v1/compliance/requirements/RT_NOTYET/status")
    assert resp.status_code == 404


def test_get_status_by_code_returns_disclaimer(
    client: TestClient, db_session: Session
) -> None:
    _seed_req(db_session, "RT_GET_OK")
    client.post("/api/v1/compliance/requirements/RT_GET_OK/status/recompute")
    resp = client.get("/api/v1/compliance/requirements/RT_GET_OK/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["requirement_code"] == "RT_GET_OK"
    assert "disclaimer" in body
    assert "conformidade" in body["disclaimer"].lower()


# ---------------------------------------------------------------------------
# POST recompute
# ---------------------------------------------------------------------------


def test_post_recompute_creates_status(client: TestClient, db_session: Session) -> None:
    _seed_req(db_session, "RT_RC")
    resp = client.post("/api/v1/compliance/requirements/RT_RC/status/recompute")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mutated"] is True
    assert body["status"] == "EVIDENCE_PENDING"
    assert body["history_entry_created"] is True
    assert "disclaimer" in body


def test_post_recompute_idempotent_returns_mutated_false(
    client: TestClient, db_session: Session
) -> None:
    _seed_req(db_session, "RT_RC_IDEMP")
    client.post("/api/v1/compliance/requirements/RT_RC_IDEMP/status/recompute")
    resp = client.post("/api/v1/compliance/requirements/RT_RC_IDEMP/status/recompute")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mutated"] is False
    assert body["history_entry_created"] is False


def test_post_recompute_404_for_unknown_requirement(client: TestClient) -> None:
    resp = client.post("/api/v1/compliance/requirements/NAO_EXISTE/status/recompute")
    assert resp.status_code == 404


def test_post_bulk_recompute_returns_processed_mutated_unchanged(
    client: TestClient, db_session: Session
) -> None:
    for i in range(3):
        _seed_req(db_session, f"RT_BULK_{i}")
    resp = client.post(BULK_RECOMPUTE)
    assert resp.status_code == 200
    body = resp.json()
    assert body["processed"] == 3
    assert body["mutated"] == 3
    assert body["unchanged"] == 0
    assert body["failed"] == 0
    assert "disclaimer" in body

    resp2 = client.post(BULK_RECOMPUTE)
    body2 = resp2.json()
    assert body2["processed"] == 3
    assert body2["mutated"] == 0
    assert body2["unchanged"] == 3
