"""Testes dos endpoints REST do módulo compliance."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.modules.compliance.seed import run_seed


@pytest.fixture
def seeded_client(client: TestClient, test_engine) -> TestClient:  # type: ignore[no-untyped-def]
    """Cria um client com o seed matriz_v1 carregado no engine de testes."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    with SessionLocal() as session:
        run_seed(session)
        session.commit()
    return client


def test_list_requirements_returns_all(seeded_client: TestClient) -> None:
    res = seeded_client.get("/api/v1/compliance/requirements", params={"limit": 500})
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, list)
    assert len(body) >= 30
    first = body[0]
    assert "code" in first
    assert first["mapping_status"] == "MAPPED"


def test_list_requirements_filter_by_source(seeded_client: TestClient) -> None:
    res = seeded_client.get(
        "/api/v1/compliance/requirements",
        params={"source": "ANEXO_III", "limit": 500},
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body) >= 1
    assert all(item["source"] == "ANEXO_III" for item in body)


def test_list_requirements_filter_by_classification(seeded_client: TestClient) -> None:
    res = seeded_client.get(
        "/api/v1/compliance/requirements",
        params={"classification": "OBRIGATORIO_LGPD", "limit": 500},
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body) >= 1
    assert all(item["classification"] == "OBRIGATORIO_LGPD" for item in body)


def test_list_requirements_filter_by_stage(seeded_client: TestClient) -> None:
    res = seeded_client.get(
        "/api/v1/compliance/requirements",
        params={"stage": "ETAPA_5", "limit": 500},
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body) >= 1
    assert all(item["stage"] == "ETAPA_5" for item in body)


def test_get_requirement_detail(seeded_client: TestClient) -> None:
    res = seeded_client.get("/api/v1/compliance/requirements/ART_3_CAPUT")
    assert res.status_code == 200
    body = res.json()
    assert body["code"] == "ART_3_CAPUT"
    assert body["mapping_status"] == "MAPPED"
    assert body["source_note"].startswith("Requisito mapeado")
    assert len(body["deadlines"]) == 3
    assert any(
        d["serventia_class"] == "C3" and d["value"] == 90 and d["unit"] == "DIAS"
        for d in body["deadlines"]
    )
    assert len(body["evidence_templates"]) >= 3
    assert len(body["policies"]) >= 1
    assert "policy" in body["policies"][0]


def test_get_requirement_404(seeded_client: TestClient) -> None:
    res = seeded_client.get("/api/v1/compliance/requirements/DOES_NOT_EXIST")
    assert res.status_code == 404


def test_list_policies(seeded_client: TestClient) -> None:
    res = seeded_client.get("/api/v1/compliance/policies", params={"limit": 500})
    assert res.status_code == 200
    body = res.json()
    assert len(body) >= 30


def test_list_policies_filter_by_kind(seeded_client: TestClient) -> None:
    res = seeded_client.get(
        "/api/v1/compliance/policies",
        params={"kind": "PLANO", "limit": 500},
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body) >= 1
    assert all(item["kind"] == "PLANO" for item in body)


def test_get_policy_detail(seeded_client: TestClient) -> None:
    res = seeded_client.get("/api/v1/compliance/policies/PSI")
    assert res.status_code == 200
    body = res.json()
    assert body["code"] == "PSI"
    assert len(body["requirements"]) >= 5
    assert "requirement" in body["requirements"][0]


def test_get_policy_404(seeded_client: TestClient) -> None:
    res = seeded_client.get("/api/v1/compliance/policies/UNKNOWN_POLICY")
    assert res.status_code == 404


def test_etapas_summary(seeded_client: TestClient) -> None:
    res = seeded_client.get("/api/v1/compliance/etapas")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, list)
    assert len(body) >= 3
    for entry in body:
        assert "stage" in entry
        assert entry["requirement_count"] >= 1


def test_summary_endpoint(seeded_client: TestClient) -> None:
    res = seeded_client.get("/api/v1/compliance/summary")
    assert res.status_code == 200
    body = res.json()
    assert body["seed_name"] == "matriz_v1"
    assert body["seed_version"] == "V1.0_MAR2026"
    assert body["requirement_count"] >= 30
    assert body["policy_count"] >= 30
    assert body["c3_initial_deadline_days"] == 90
    assert "validar antes de uso" in body["c3_initial_deadline_reference_note"]
    assert "Matriz INOVA V1" in body["conservative_note"]


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/api/v1/compliance/requirements"),
        ("post", "/api/v1/compliance/policies"),
        ("patch", "/api/v1/compliance/requirements/ART_3_CAPUT"),
        ("put", "/api/v1/compliance/requirements/ART_3_CAPUT"),
        ("delete", "/api/v1/compliance/requirements/ART_3_CAPUT"),
        ("delete", "/api/v1/compliance/policies/PSI"),
    ],
)
def test_no_write_endpoints(seeded_client: TestClient, method: str, path: str) -> None:
    if method == "delete":
        res = seeded_client.delete(path)
    else:
        res = getattr(seeded_client, method)(path, json={})
    assert res.status_code in (404, 405), (
        f"{method.upper()} {path} deveria retornar 404/405; obtido {res.status_code}"
    )
