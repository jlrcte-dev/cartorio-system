from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_body(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    body = response.json()
    assert body["status"] == "ok"
    assert "app" in body
    assert "version" in body
