"""Testes de rotas para RequirementFindingLink."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.compliance.enums import (
    RequirementClassification,
    RequirementSource,
    RequirementStage,
)
from app.modules.compliance.models import ComplianceRequirement

_BASE = "/api/v1/compliance/requirement-links"


def _seed_requirement(db: Session, code: str = "RT_ART_12") -> ComplianceRequirement:
    req = ComplianceRequirement(
        code=code,
        source=RequirementSource.PROV_213,
        article_label="Art. 12 — Route Test",
        article_text="Texto de teste de rota.",
        classification=RequirementClassification.OBRIGATORIO_PROVIMENTO,
        stage=RequirementStage.ETAPA_1,
    )
    db.add(req)
    db.commit()
    return req


def _create_link(
    client: TestClient,
    requirement_code: str = "RT_ART_12",
    source_module: str = "AUDIT",
    source_type: str = "FINDING",
    source_ref: str = "DIAG-004",
    **kwargs,
) -> dict:
    payload = dict(
        requirement_code=requirement_code,
        source_module=source_module,
        source_type=source_type,
        source_ref=source_ref,
        **kwargs,
    )
    resp = client.post(_BASE, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# POST
# ---------------------------------------------------------------------------


def test_post_creates_link_201(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session)
    data = _create_link(client)
    assert data["id"] is not None
    assert data["source_module"] == "AUDIT"
    assert data["source_type"] == "FINDING"
    assert data["source_ref"] == "DIAG-004"
    assert data["requirement_code"] == "RT_ART_12"


def test_post_includes_link_note(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session)
    data = _create_link(client)
    assert "link_note" in data
    assert "conformidade" in data["link_note"].lower()


def test_post_with_all_optional_fields(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session)
    data = _create_link(
        client,
        title="Título do vínculo",
        link_reason="Razão de negócio.",
        risk_level="HIGH",
        notes="Observação interna.",
    )
    assert data["title"] == "Título do vínculo"
    assert data["link_reason"] == "Razão de negócio."
    assert data["risk_level"] == "HIGH"
    assert data["notes"] == "Observação interna."


def test_post_nonexistent_requirement_returns_404(client: TestClient) -> None:
    resp = client.post(
        _BASE,
        json={
            "requirement_code": "NAO_EXISTE_XYZ",
            "source_module": "AUDIT",
            "source_type": "FINDING",
            "source_ref": "DIAG-001",
        },
    )
    assert resp.status_code == 404


def test_post_missing_required_fields_422(client: TestClient) -> None:
    resp = client.post(_BASE, json={"requirement_code": "RT_ART_12"})
    assert resp.status_code == 422


def test_post_empty_source_ref_422(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session)
    resp = client.post(
        _BASE,
        json={
            "requirement_code": "RT_ART_12",
            "source_module": "AUDIT",
            "source_type": "FINDING",
            "source_ref": "",
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET list
# ---------------------------------------------------------------------------


def test_get_list_200(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session)
    _create_link(client, source_ref="LIST-001")
    _create_link(client, source_ref="LIST-002")
    resp = client.get(_BASE)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2


def test_get_list_filter_requirement_code(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session, "REQ_FILTER_A")
    _seed_requirement(db_session, "REQ_FILTER_B")
    _create_link(client, requirement_code="REQ_FILTER_A", source_ref="FA-1")
    _create_link(client, requirement_code="REQ_FILTER_B", source_ref="FB-1")

    resp = client.get(_BASE, params={"requirement_code": "REQ_FILTER_A"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["requirement_code"] == "REQ_FILTER_A" for item in data)


def test_get_list_filter_source_module(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session)
    _create_link(client, source_module="AUDIT", source_ref="MOD-A")
    _create_link(client, source_module="RETENTION", source_type="SIGNAL", source_ref="MOD-R")

    resp = client.get(_BASE, params={"source_module": "RETENTION"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["source_module"] == "RETENTION" for item in data)


def test_get_list_filter_source_type(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session)
    _create_link(client, source_type="FINDING", source_ref="TY-F")
    _create_link(client, source_module="LGPD", source_type="ACTION", source_ref="TY-A")

    resp = client.get(_BASE, params={"source_type": "ACTION"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["source_type"] == "ACTION" for item in data)


def test_get_list_filter_risk_level(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session)
    _create_link(client, source_ref="RL-H", risk_level="HIGH")
    _create_link(client, source_ref="RL-L", risk_level="LOW")

    resp = client.get(_BASE, params={"risk_level": "HIGH"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["risk_level"] == "HIGH" for item in data)


# ---------------------------------------------------------------------------
# GET detail
# ---------------------------------------------------------------------------


def test_get_detail_200(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session)
    created = _create_link(client, notes="Detalhe note.")
    resp = client.get(f"{_BASE}/{created['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == created["id"]
    assert data["notes"] == "Detalhe note."


def test_get_detail_404(client: TestClient) -> None:
    resp = client.get(f"{_BASE}/999999")
    assert resp.status_code == 404


def test_get_detail_has_link_note(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session)
    created = _create_link(client)
    resp = client.get(f"{_BASE}/{created['id']}")
    assert resp.status_code == 200
    assert "link_note" in resp.json()


# ---------------------------------------------------------------------------
# PATCH
# ---------------------------------------------------------------------------


def test_patch_updates_notes_200(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session)
    created = _create_link(client)
    resp = client.patch(f"{_BASE}/{created['id']}", json={"notes": "Nota atualizada."})
    assert resp.status_code == 200
    assert resp.json()["notes"] == "Nota atualizada."


def test_patch_updates_risk_level(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session)
    created = _create_link(client)
    resp = client.patch(f"{_BASE}/{created['id']}", json={"risk_level": "CRITICAL"})
    assert resp.status_code == 200
    assert resp.json()["risk_level"] == "CRITICAL"


def test_patch_clears_risk_level(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session)
    created = _create_link(client, risk_level="HIGH")
    resp = client.patch(f"{_BASE}/{created['id']}", json={"risk_level": None})
    assert resp.status_code == 200
    assert resp.json()["risk_level"] is None


def test_patch_updates_link_reason(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session)
    created = _create_link(client)
    resp = client.patch(f"{_BASE}/{created['id']}", json={"link_reason": "Nova razão."})
    assert resp.status_code == 200
    assert resp.json()["link_reason"] == "Nova razão."


def test_patch_404(client: TestClient) -> None:
    resp = client.patch(f"{_BASE}/999999", json={"notes": "x"})
    assert resp.status_code == 404


def test_patch_rejects_explicit_null_source_module(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session)
    created = _create_link(client)
    resp = client.patch(f"{_BASE}/{created['id']}", json={"source_module": None})
    assert resp.status_code == 422


def test_patch_rejects_explicit_null_source_type(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session)
    created = _create_link(client)
    resp = client.patch(f"{_BASE}/{created['id']}", json={"source_type": None})
    assert resp.status_code == 422


def test_patch_rejects_explicit_null_source_ref(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session)
    created = _create_link(client)
    resp = client.patch(f"{_BASE}/{created['id']}", json={"source_ref": None})
    assert resp.status_code == 422


def test_patch_does_not_change_requirement(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session)
    created = _create_link(client)
    original_req_id = created["requirement_id"]
    resp = client.patch(f"{_BASE}/{created['id']}", json={"notes": "algo"})
    assert resp.status_code == 200
    assert resp.json()["requirement_id"] == original_req_id


# ---------------------------------------------------------------------------
# Unicidade — POST duplicado retorna 400
# ---------------------------------------------------------------------------


def test_post_duplicate_returns_400(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session)
    _create_link(client, source_ref="UNIQUE-001")
    resp = client.post(
        _BASE,
        json={
            "requirement_code": "RT_ART_12",
            "source_module": "AUDIT",
            "source_type": "FINDING",
            "source_ref": "UNIQUE-001",
        },
    )
    assert resp.status_code == 400
    assert "mesma origem" in resp.json()["detail"]


def test_post_same_source_ref_different_requirement_allowed(
    client: TestClient, db_session: Session
) -> None:
    _seed_requirement(db_session, "UQ_RT_A")
    _seed_requirement(db_session, "UQ_RT_B")
    _create_link(client, requirement_code="UQ_RT_A", source_ref="CROSS-001")
    resp = client.post(
        _BASE,
        json={
            "requirement_code": "UQ_RT_B",
            "source_module": "AUDIT",
            "source_type": "FINDING",
            "source_ref": "CROSS-001",
        },
    )
    assert resp.status_code == 201


def test_post_same_requirement_different_source_type_allowed(
    client: TestClient, db_session: Session
) -> None:
    _seed_requirement(db_session)
    _create_link(client, source_type="FINDING", source_ref="MULTI-T")
    resp = client.post(
        _BASE,
        json={
            "requirement_code": "RT_ART_12",
            "source_module": "AUDIT",
            "source_type": "DIAGNOSIS",
            "source_ref": "MULTI-T",
        },
    )
    assert resp.status_code == 201


def test_post_same_requirement_different_source_module_allowed(
    client: TestClient, db_session: Session
) -> None:
    _seed_requirement(db_session)
    _create_link(client, source_module="AUDIT", source_ref="MULTI-M")
    resp = client.post(
        _BASE,
        json={
            "requirement_code": "RT_ART_12",
            "source_module": "LGPD",
            "source_type": "ACTION",
            "source_ref": "MULTI-M",
        },
    )
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# DELETE ausente
# ---------------------------------------------------------------------------


def test_delete_not_allowed(client: TestClient, db_session: Session) -> None:
    _seed_requirement(db_session)
    created = _create_link(client)
    resp = client.delete(f"{_BASE}/{created['id']}")
    assert resp.status_code in (404, 405)


def test_delete_list_not_allowed(client: TestClient) -> None:
    resp = client.delete(_BASE)
    assert resp.status_code in (404, 405)
