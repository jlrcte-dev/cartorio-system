from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient


def _payload(**overrides):
    base = {
        "entry_type": "RECEITA",
        "competence_month": "2026-04",
        "date": "2026-04-15",
        "description": "Emolumentos RI - protocolo 3724",
        "category": "emolumentos",
        "service_area": "RI",
        "amount": "150.50",
        "status": "RECEIVED",
        "payment_date": "2026-04-15",
        "notes": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Criação básica
# ---------------------------------------------------------------------------
def test_create_receita_201_default_source_and_direction(client: TestClient) -> None:
    response = client.post("/api/v1/finance/entries", json=_payload())
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["entry_type"] == "RECEITA"
    assert body["status"] == "RECEIVED"
    assert body["amount"] == "150.50"
    assert body["competence_month"] == "2026-04"
    assert body["service_area"] == "RI"
    assert body["source"] == "MANUAL"
    assert body["direction"] == "INFLOW"
    assert body["created_by"] == "gestor"
    assert body["updated_by"] == "gestor"
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


def test_create_despesa_forces_outflow(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(
            entry_type="DESPESA",
            description="Conta de energia",
            category="energia",
            service_area="GERAL",
            amount="789.30",
            status="PAID",
        ),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["entry_type"] == "DESPESA"
    assert body["direction"] == "OUTFLOW"


def test_create_repasse_forces_outflow(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(
            entry_type="REPASSE",
            description="ISS competência 04/2026",
            category="iss",
            service_area="GERAL",
            amount="1200.00",
            status="PENDING",
            payment_date=None,
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["direction"] == "OUTFLOW"


def test_create_receita_forces_inflow(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(direction="INFLOW"),
    )
    assert response.status_code == 201
    assert response.json()["direction"] == "INFLOW"


def test_create_receita_with_outflow_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(direction="OUTFLOW"),
    )
    assert response.status_code == 422


def test_create_ajuste_inflow(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(
            entry_type="AJUSTE",
            direction="INFLOW",
            description="Estorno de conta paga indevidamente",
            status="RECEIVED",
        ),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["entry_type"] == "AJUSTE"
    assert body["direction"] == "INFLOW"


def test_create_ajuste_outflow(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(
            entry_type="AJUSTE",
            direction="OUTFLOW",
            description="Reclassificação contábil",
            status="PAID",
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["direction"] == "OUTFLOW"


def test_create_ajuste_without_direction_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(entry_type="AJUSTE", status="PAID"),
    )
    assert response.status_code == 422


def test_create_with_explicit_source(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(source="ENGEGRAPH_EXPORT"),
    )
    assert response.status_code == 201
    assert response.json()["source"] == "ENGEGRAPH_EXPORT"


def test_create_invalid_source_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(source="INVALID_SOURCE"),
    )
    assert response.status_code == 422


def test_create_invalid_direction_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(direction="SIDEWAYS"),
    )
    assert response.status_code == 422


def test_create_with_explicit_created_by(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(created_by="marcia"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["created_by"] == "marcia"
    assert body["updated_by"] == "marcia"


# ---------------------------------------------------------------------------
# Validação de tipo / status / amount / competência
# ---------------------------------------------------------------------------
def test_create_invalid_entry_type_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(entry_type="INVALIDO"),
    )
    assert response.status_code == 422


def test_create_negative_amount_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(amount="-10.00"),
    )
    assert response.status_code == 422


def test_create_zero_amount_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(amount="0"),
    )
    assert response.status_code == 422


def test_create_invalid_competence_month_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(competence_month="2026/04"),
    )
    assert response.status_code == 422


def test_create_status_paid_in_receita_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(entry_type="RECEITA", status="PAID"),
    )
    assert response.status_code == 422


def test_create_status_received_in_despesa_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(entry_type="DESPESA", status="RECEIVED"),
    )
    assert response.status_code == 422


def test_create_despesa_to_review_allowed(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(
            entry_type="DESPESA",
            status="TO_REVIEW",
            description="Boleto de origem desconhecida",
            payment_date=None,
        ),
    )
    assert response.status_code == 201
    assert response.json()["status"] == "TO_REVIEW"


# ---------------------------------------------------------------------------
# Regra payment_date × status
# ---------------------------------------------------------------------------
def test_create_paid_without_payment_date_fails(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(
            entry_type="DESPESA",
            status="PAID",
            payment_date=None,
            description="Energia paga sem data",
        ),
    )
    assert response.status_code == 422


def test_create_received_without_payment_date_fails(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(status="RECEIVED", payment_date=None),
    )
    assert response.status_code == 422


def test_create_pending_with_payment_date_fails(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(
            entry_type="DESPESA",
            status="PENDING",
            payment_date="2026-04-15",
            description="Boleto pendente com data preenchida",
        ),
    )
    assert response.status_code == 422


def test_create_to_review_with_payment_date_fails(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(
            entry_type="DESPESA",
            status="TO_REVIEW",
            payment_date="2026-04-15",
            description="Em revisão com data",
        ),
    )
    assert response.status_code == 422


def test_create_cancelled_with_payment_date_fails(client: TestClient) -> None:
    response = client.post(
        "/api/v1/finance/entries",
        json=_payload(
            entry_type="DESPESA",
            status="CANCELLED",
            payment_date="2026-04-15",
            description="Cancelado com data",
        ),
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Listagem e get
# ---------------------------------------------------------------------------
def test_list_filters_by_competence(client: TestClient) -> None:
    client.post("/api/v1/finance/entries", json=_payload(competence_month="2026-04"))
    client.post(
        "/api/v1/finance/entries",
        json=_payload(competence_month="2026-03", date="2026-03-10", payment_date="2026-03-10"),
    )

    response = client.get("/api/v1/finance/entries", params={"competence_month": "2026-04"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["competence_month"] == "2026-04"


def test_list_filters_by_type_and_area(client: TestClient) -> None:
    client.post(
        "/api/v1/finance/entries",
        json=_payload(entry_type="RECEITA", service_area="RI", status="RECEIVED"),
    )
    client.post(
        "/api/v1/finance/entries",
        json=_payload(
            entry_type="DESPESA",
            service_area="GERAL",
            status="PAID",
            description="d",
        ),
    )

    r = client.get(
        "/api/v1/finance/entries",
        params={"entry_type": "RECEITA", "service_area": "RI"},
    )
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_get_entry_not_found(client: TestClient) -> None:
    r = client.get("/api/v1/finance/entries/9999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Update — campos imutáveis e regras
# ---------------------------------------------------------------------------
def test_update_status_pending_to_paid(client: TestClient) -> None:
    created = client.post(
        "/api/v1/finance/entries",
        json=_payload(
            entry_type="DESPESA",
            description="Internet",
            service_area="GERAL",
            amount="299.00",
            status="PENDING",
            payment_date=None,
        ),
    ).json()

    entry_id = created["id"]
    r = client.patch(
        f"/api/v1/finance/entries/{entry_id}",
        json={"status": "PAID", "payment_date": "2026-04-20", "updated_by": "gestor"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "PAID"
    assert body["payment_date"] == "2026-04-20"
    assert body["updated_by"] == "gestor"


def test_update_status_inconsistent_422(client: TestClient) -> None:
    created = client.post(
        "/api/v1/finance/entries",
        json=_payload(entry_type="RECEITA", status="RECEIVED"),
    ).json()
    r = client.patch(
        f"/api/v1/finance/entries/{created['id']}",
        json={"status": "PAID", "payment_date": "2026-04-15"},
    )
    assert r.status_code == 422


def test_update_to_paid_without_payment_date_fails(client: TestClient) -> None:
    created = client.post(
        "/api/v1/finance/entries",
        json=_payload(
            entry_type="DESPESA",
            description="Internet",
            service_area="GERAL",
            amount="299.00",
            status="PENDING",
            payment_date=None,
        ),
    ).json()
    r = client.patch(
        f"/api/v1/finance/entries/{created['id']}",
        json={"status": "PAID"},
    )
    assert r.status_code == 422


def test_update_to_received_without_payment_date_fails(client: TestClient) -> None:
    created = client.post(
        "/api/v1/finance/entries",
        json=_payload(status="PENDING", payment_date=None),
    ).json()
    r = client.patch(
        f"/api/v1/finance/entries/{created['id']}",
        json={"status": "RECEIVED"},
    )
    assert r.status_code == 422


def test_update_entry_type_forbidden(client: TestClient) -> None:
    created = client.post(
        "/api/v1/finance/entries",
        json=_payload(),
    ).json()
    r = client.patch(
        f"/api/v1/finance/entries/{created['id']}",
        json={"entry_type": "DESPESA"},
    )
    assert r.status_code == 422


def test_update_competence_month_forbidden(client: TestClient) -> None:
    created = client.post(
        "/api/v1/finance/entries",
        json=_payload(),
    ).json()
    r = client.patch(
        f"/api/v1/finance/entries/{created['id']}",
        json={"competence_month": "2026-05"},
    )
    assert r.status_code == 422


def test_update_with_null_amount_fails(client: TestClient) -> None:
    created = client.post(
        "/api/v1/finance/entries",
        json=_payload(),
    ).json()
    r = client.patch(
        f"/api/v1/finance/entries/{created['id']}",
        json={"amount": None},
    )
    assert r.status_code == 422


def test_update_without_amount_keeps_value(client: TestClient) -> None:
    created = client.post(
        "/api/v1/finance/entries",
        json=_payload(amount="150.50"),
    ).json()
    r = client.patch(
        f"/api/v1/finance/entries/{created['id']}",
        json={"notes": "apenas anotação"},
    )
    assert r.status_code == 200
    assert r.json()["amount"] == "150.50"


def test_update_with_positive_amount_succeeds(client: TestClient) -> None:
    created = client.post(
        "/api/v1/finance/entries",
        json=_payload(amount="100.00"),
    ).json()
    r = client.patch(
        f"/api/v1/finance/entries/{created['id']}",
        json={"amount": "250.75"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["amount"] == "250.75"


def test_update_with_zero_amount_fails(client: TestClient) -> None:
    created = client.post(
        "/api/v1/finance/entries",
        json=_payload(),
    ).json()
    r = client.patch(
        f"/api/v1/finance/entries/{created['id']}",
        json={"amount": "0"},
    )
    assert r.status_code == 422


def test_update_with_negative_amount_fails(client: TestClient) -> None:
    created = client.post(
        "/api/v1/finance/entries",
        json=_payload(),
    ).json()
    r = client.patch(
        f"/api/v1/finance/entries/{created['id']}",
        json={"amount": "-10.00"},
    )
    assert r.status_code == 422


def test_update_updated_by(client: TestClient) -> None:
    created = client.post(
        "/api/v1/finance/entries",
        json=_payload(),
    ).json()
    r = client.patch(
        f"/api/v1/finance/entries/{created['id']}",
        json={"notes": "verificado", "updated_by": "monique"},
    )
    assert r.status_code == 200
    assert r.json()["updated_by"] == "monique"


# ---------------------------------------------------------------------------
# Monthly summary
# ---------------------------------------------------------------------------
def test_monthly_summary_calculation(client: TestClient) -> None:
    # Receita liquidada 1000
    client.post(
        "/api/v1/finance/entries",
        json=_payload(amount="1000.00", status="RECEIVED", service_area="RI"),
    )
    # Receita pendente 500
    client.post(
        "/api/v1/finance/entries",
        json=_payload(
            amount="500.00",
            status="PENDING",
            service_area="NOTAS",
            payment_date=None,
        ),
    )
    # Despesa paga 300
    client.post(
        "/api/v1/finance/entries",
        json=_payload(
            entry_type="DESPESA",
            amount="300.00",
            status="PAID",
            service_area="GERAL",
            description="Energia",
        ),
    )
    # Repasse pago 200
    client.post(
        "/api/v1/finance/entries",
        json=_payload(
            entry_type="REPASSE",
            amount="200.00",
            status="PAID",
            service_area="GERAL",
            description="ISS",
        ),
    )
    # Ajuste positivo 50 (PAID)
    client.post(
        "/api/v1/finance/entries",
        json=_payload(
            entry_type="AJUSTE",
            direction="INFLOW",
            amount="50.00",
            status="PAID",
            service_area="GERAL",
            description="Estorno favorável",
        ),
    )
    # Ajuste negativo 25 (PAID)
    client.post(
        "/api/v1/finance/entries",
        json=_payload(
            entry_type="AJUSTE",
            direction="OUTFLOW",
            amount="25.00",
            status="PAID",
            service_area="GERAL",
            description="Estorno desfavorável",
        ),
    )
    # Cancelado 9999 (com payment_date None)
    client.post(
        "/api/v1/finance/entries",
        json=_payload(
            entry_type="DESPESA",
            amount="9999.00",
            status="CANCELLED",
            service_area="GERAL",
            description="Cancelado",
            payment_date=None,
        ),
    )
    # TO_REVIEW 777
    client.post(
        "/api/v1/finance/entries",
        json=_payload(
            entry_type="DESPESA",
            amount="777.00",
            status="TO_REVIEW",
            service_area="GERAL",
            description="Em revisão",
            payment_date=None,
        ),
    )
    # Outra competência (deve ficar fora)
    client.post(
        "/api/v1/finance/entries",
        json=_payload(
            competence_month="2026-03",
            date="2026-03-01",
            payment_date="2026-03-01",
        ),
    )

    r = client.get(
        "/api/v1/finance/monthly-summary",
        params={"competence_month": "2026-04"},
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["competence_month"] == "2026-04"
    assert body["entry_count"] == 8
    assert body["pending_count"] == 1
    assert body["cancelled_count"] == 1
    assert body["to_review_count"] == 1

    assert Decimal(body["total_revenues"]) == Decimal("1500.00")
    assert Decimal(body["total_expenses"]) == Decimal("300.00")
    assert Decimal(body["total_repasses"]) == Decimal("200.00")
    assert Decimal(body["total_adjustments_inflow"]) == Decimal("50.00")
    assert Decimal(body["total_adjustments_outflow"]) == Decimal("25.00")

    assert Decimal(body["result_estimate"]) == Decimal("1025.00")

    assert Decimal(body["receita"]["valid_total"]) == Decimal("1500.00")
    assert Decimal(body["receita"]["pending"]) == Decimal("500.00")
    assert Decimal(body["receita"]["settled"]) == Decimal("1000.00")
    assert Decimal(body["despesa"]["cancelled"]) == Decimal("9999.00")
    assert Decimal(body["despesa"]["to_review"]) == Decimal("777.00")
    assert Decimal(body["despesa"]["valid_total"]) == Decimal("300.00")

    by_area = body["by_service_area"]
    assert Decimal(by_area["RI"]["receita"]) == Decimal("1000.00")
    assert Decimal(by_area["NOTAS"]["receita"]) == Decimal("500.00")
    assert Decimal(by_area["GERAL"]["despesa"]) == Decimal("300.00")
    assert Decimal(by_area["GERAL"]["repasse"]) == Decimal("200.00")
    assert Decimal(by_area["GERAL"]["ajuste_inflow"]) == Decimal("50.00")
    assert Decimal(by_area["GERAL"]["ajuste_outflow"]) == Decimal("25.00")


def test_monthly_summary_cancelled_excluded(client: TestClient) -> None:
    client.post(
        "/api/v1/finance/entries",
        json=_payload(amount="100.00", status="RECEIVED"),
    )
    client.post(
        "/api/v1/finance/entries",
        json=_payload(
            amount="9999.00",
            status="CANCELLED",
            payment_date=None,
        ),
    )
    r = client.get(
        "/api/v1/finance/monthly-summary",
        params={"competence_month": "2026-04"},
    )
    body = r.json()
    assert Decimal(body["total_revenues"]) == Decimal("100.00")
    assert Decimal(body["result_estimate"]) == Decimal("100.00")


def test_monthly_summary_to_review_excluded(client: TestClient) -> None:
    client.post(
        "/api/v1/finance/entries",
        json=_payload(amount="100.00", status="RECEIVED"),
    )
    client.post(
        "/api/v1/finance/entries",
        json=_payload(
            amount="555.00",
            status="TO_REVIEW",
            payment_date=None,
        ),
    )
    r = client.get(
        "/api/v1/finance/monthly-summary",
        params={"competence_month": "2026-04"},
    )
    body = r.json()
    assert Decimal(body["total_revenues"]) == Decimal("100.00")
    assert Decimal(body["result_estimate"]) == Decimal("100.00")
    assert body["to_review_count"] == 1


def test_monthly_summary_empty_month(client: TestClient) -> None:
    r = client.get(
        "/api/v1/finance/monthly-summary",
        params={"competence_month": "2026-12"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["entry_count"] == 0
    assert Decimal(body["result_estimate"]) == Decimal("0.00")


def test_monthly_summary_invalid_format_422(client: TestClient) -> None:
    r = client.get(
        "/api/v1/finance/monthly-summary",
        params={"competence_month": "abril/2026"},
    )
    assert r.status_code == 422
