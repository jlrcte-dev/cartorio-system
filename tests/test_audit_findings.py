"""Testes do submódulo AuditFinding (Sprint 2).

Todos os testes usam o fixture `client` do conftest.py (TestClient com
banco in-memory). Nenhum dado real do servidor é utilizado.
"""

from __future__ import annotations

import datetime as _dt

from fastapi.testclient import TestClient

BASE = "/api/v1/audit/findings"


def _payload(**overrides) -> dict:
    """Payload mínimo válido para criar um AuditFinding."""
    base = {
        "title": "POPs de Protesto sem atualização desde 2019",
        "description": (
            "Documentos Procedimento Protesto.odt e .pdf com data de modificação "
            "de 2019. Necessitam revisão para alinhamento com Provimento CNJ 213/2026."
        ),
        "category": "POLICY_DOCUMENT",
        "origin": "SCANNER",
        "severity": "MEDIUM",
        "probability": "HIGH",
        "impact": "MEDIUM",
        "priority": "THIRTY_DAYS",
        "evidence_summary": "Scanner identificou arquivos com data de modificação 2019.",
        "recommended_action": "Revisar e atualizar os POPs ou criar nova versão aprovada.",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Criação básica
# ---------------------------------------------------------------------------


def test_create_finding_valid(client: TestClient) -> None:
    response = client.post(BASE, json=_payload())
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "POPs de Protesto sem atualização desde 2019"
    assert body["category"] == "POLICY_DOCUMENT"
    assert body["severity"] == "MEDIUM"
    assert body["origin"] == "SCANNER"
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


# ---------------------------------------------------------------------------
# 2. Status padrão open
# ---------------------------------------------------------------------------


def test_create_sets_status_open_by_default(client: TestClient) -> None:
    response = client.post(BASE, json=_payload())
    assert response.status_code == 201
    assert response.json()["status"] == "OPEN"


def test_create_can_set_explicit_status(client: TestClient) -> None:
    response = client.post(BASE, json=_payload(status="IN_PROGRESS"))
    assert response.status_code == 201
    assert response.json()["status"] == "IN_PROGRESS"


# ---------------------------------------------------------------------------
# 3. Campos obrigatórios
# ---------------------------------------------------------------------------


def test_create_missing_title_422(client: TestClient) -> None:
    data = _payload()
    del data["title"]
    assert client.post(BASE, json=data).status_code == 422


def test_create_missing_category_422(client: TestClient) -> None:
    data = _payload()
    del data["category"]
    assert client.post(BASE, json=data).status_code == 422


def test_create_missing_evidence_summary_422(client: TestClient) -> None:
    data = _payload()
    del data["evidence_summary"]
    assert client.post(BASE, json=data).status_code == 422


# ---------------------------------------------------------------------------
# 4. Achado CRITICAL exige IMMEDIATE ou SEVEN_DAYS (salvo notes)
# ---------------------------------------------------------------------------


def test_create_critical_without_urgent_priority_rejected(client: TestClient) -> None:
    data = _payload(severity="CRITICAL", priority="THIRTY_DAYS")
    response = client.post(BASE, json=data)
    assert response.status_code == 422
    assert "CRITICAL" in response.text


def test_create_critical_with_immediate_priority_ok(client: TestClient) -> None:
    data = _payload(severity="CRITICAL", priority="IMMEDIATE")
    assert client.post(BASE, json=data).status_code == 201


def test_create_critical_with_notes_justification_ok(client: TestClient) -> None:
    data = _payload(
        severity="CRITICAL",
        priority="THIRTY_DAYS",
        notes="Aguardando orçamento — prazo negociado com gestor.",
    )
    assert client.post(BASE, json=data).status_code == 201


# ---------------------------------------------------------------------------
# 5. Listagem básica
# ---------------------------------------------------------------------------


def test_list_findings_returns_list(client: TestClient) -> None:
    client.post(BASE, json=_payload())
    response = client.get(BASE)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


# ---------------------------------------------------------------------------
# 6. Filtros
# ---------------------------------------------------------------------------


def test_filter_by_status(client: TestClient) -> None:
    client.post(BASE, json=_payload())
    client.post(BASE, json=_payload(title="Outro achado", status="IN_PROGRESS"))
    open_findings = client.get(BASE, params={"status": "OPEN"}).json()
    assert all(f["status"] == "OPEN" for f in open_findings)


def test_filter_by_severity(client: TestClient) -> None:
    client.post(BASE, json=_payload(severity="HIGH", priority="SEVEN_DAYS"))
    client.post(BASE, json=_payload(severity="LOW", priority="BACKLOG"))
    high = client.get(BASE, params={"severity": "HIGH"}).json()
    assert all(f["severity"] == "HIGH" for f in high)


def test_filter_by_category(client: TestClient) -> None:
    client.post(BASE, json=_payload(category="BACKUP"))
    client.post(BASE, json=_payload(category="NETWORK"))
    backup = client.get(BASE, params={"category": "BACKUP"}).json()
    assert all(f["category"] == "BACKUP" for f in backup)


def test_filter_by_priority(client: TestClient) -> None:
    client.post(BASE, json=_payload(priority="IMMEDIATE", severity="CRITICAL"))
    client.post(BASE, json=_payload(priority="BACKLOG"))
    immediate = client.get(BASE, params={"priority": "IMMEDIATE"}).json()
    assert all(f["priority"] == "IMMEDIATE" for f in immediate)


def test_filter_by_origin(client: TestClient) -> None:
    client.post(BASE, json=_payload(origin="MANUAL"))
    manual = client.get(BASE, params={"origin": "MANUAL"}).json()
    assert all(f["origin"] == "MANUAL" for f in manual)


def test_filter_by_scanner_run_id(client: TestClient) -> None:
    run_id = "ef8139c3-07cb-400c-8c48-e319623dbacf"
    client.post(BASE, json=_payload(scanner_run_id=run_id, origin="SCANNER"))
    client.post(BASE, json=_payload(scanner_run_id="other-run-id", origin="SCANNER"))
    results = client.get(BASE, params={"scanner_run_id": run_id}).json()
    assert all(f["scanner_run_id"] == run_id for f in results)
    assert len(results) >= 1


# ---------------------------------------------------------------------------
# 7. Consulta por ID
# ---------------------------------------------------------------------------


def test_get_finding_by_id(client: TestClient) -> None:
    created = client.post(BASE, json=_payload()).json()
    response = client.get(f"{BASE}/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_finding_not_found(client: TestClient) -> None:
    assert client.get(f"{BASE}/99999").status_code == 404


# ---------------------------------------------------------------------------
# 8. Atualização parcial (PATCH)
# ---------------------------------------------------------------------------


def test_patch_updates_title(client: TestClient) -> None:
    created = client.post(BASE, json=_payload()).json()
    response = client.patch(f"{BASE}/{created['id']}", json={"title": "Título atualizado"})
    assert response.status_code == 200
    assert response.json()["title"] == "Título atualizado"


def test_patch_partial_leaves_other_fields(client: TestClient) -> None:
    created = client.post(BASE, json=_payload()).json()
    client.patch(f"{BASE}/{created['id']}", json={"priority": "NINETY_DAYS"})
    updated = client.get(f"{BASE}/{created['id']}").json()
    assert updated["priority"] == "NINETY_DAYS"
    assert updated["category"] == created["category"]  # unchanged


# ---------------------------------------------------------------------------
# 9. updated_at muda em atualização
# ---------------------------------------------------------------------------


def test_patch_changes_updated_at(client: TestClient) -> None:
    created = client.post(BASE, json=_payload()).json()
    updated = client.patch(f"{BASE}/{created['id']}", json={"notes": "Nota adicionada."}).json()
    # updated_at deve ser >= created_at (pode ser igual no mesmo milissegundo)
    created_ts = _dt.datetime.fromisoformat(created["created_at"])
    updated_ts = _dt.datetime.fromisoformat(updated["updated_at"])
    assert updated_ts >= created_ts


# ---------------------------------------------------------------------------
# 10 + 11. RESOLVED exige resolution_summary + evidência; resolved_at auto-preenchido
# ---------------------------------------------------------------------------


def test_status_resolved_without_resolution_summary_rejected(client: TestClient) -> None:
    created = client.post(BASE, json=_payload()).json()
    response = client.post(
        f"{BASE}/{created['id']}/status",
        json={"status": "RESOLVED"},
    )
    assert response.status_code == 422
    assert "resolution_summary" in response.text


def test_status_resolved_without_evidence_or_notes_rejected(client: TestClient) -> None:
    created = client.post(BASE, json=_payload()).json()
    response = client.post(
        f"{BASE}/{created['id']}/status",
        json={"status": "RESOLVED", "resolution_summary": "Corrigido."},
    )
    assert response.status_code == 422


def test_status_resolved_with_notes_ok_and_resolved_at_auto(client: TestClient) -> None:
    created = client.post(BASE, json=_payload()).json()
    response = client.post(
        f"{BASE}/{created['id']}/status",
        json={
            "status": "RESOLVED",
            "resolution_summary": "POPs revisados e nova versão aprovada.",
            "notes": "Aprovação em reunião de 2026-05-10.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "RESOLVED"
    assert body["resolved_at"] is not None  # auto-filled


def test_status_resolved_with_resolution_evidence_ok(client: TestClient) -> None:
    created = client.post(BASE, json=_payload()).json()
    response = client.post(
        f"{BASE}/{created['id']}/status",
        json={
            "status": "RESOLVED",
            "resolution_summary": "POPs atualizados.",
            "resolution_evidence": "exports/audit/scan-docs-cartorio/scan_manifest.json",
        },
    )
    assert response.status_code == 200
    assert response.json()["resolution_evidence"] is not None


# ---------------------------------------------------------------------------
# 12. DISMISSED exige dismissed_reason ou resolution_summary
# ---------------------------------------------------------------------------


def test_status_dismissed_without_reason_rejected(client: TestClient) -> None:
    created = client.post(BASE, json=_payload()).json()
    response = client.post(
        f"{BASE}/{created['id']}/status",
        json={"status": "DISMISSED"},
    )
    assert response.status_code == 422


def test_status_dismissed_with_reason_ok(client: TestClient) -> None:
    created = client.post(BASE, json=_payload()).json()
    response = client.post(
        f"{BASE}/{created['id']}/status",
        json={
            "status": "DISMISSED",
            "dismissed_reason": "Achado não se aplica a este ambiente.",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "DISMISSED"


# ---------------------------------------------------------------------------
# 13. Arquivar não exclui fisicamente
# ---------------------------------------------------------------------------


def test_archive_marks_as_archived_and_persists(client: TestClient) -> None:
    created = client.post(BASE, json=_payload()).json()
    fid = created["id"]
    response = client.post(
        f"{BASE}/{fid}/archive",
        params={"notes": "Achado arquivado após ciclo de auditoria concluído."},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ARCHIVED"

    # Finding still retrievable
    assert client.get(f"{BASE}/{fid}").status_code == 200


def test_archive_without_notes_rejected(client: TestClient) -> None:
    created = client.post(BASE, json=_payload()).json()
    # FastAPI rejects missing required query param with 422
    response = client.post(f"{BASE}/{created['id']}/archive")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 14. DELETE não existe
# ---------------------------------------------------------------------------


def test_delete_endpoint_does_not_exist(client: TestClient) -> None:
    created = client.post(BASE, json=_payload()).json()
    response = client.delete(f"{BASE}/{created['id']}")
    # 404 (route not registered) or 405 (method not allowed) — both acceptable
    assert response.status_code in (404, 405)


# ---------------------------------------------------------------------------
# 15. due_date anterior à criação é rejeitada
# ---------------------------------------------------------------------------


def test_due_date_in_past_rejected(client: TestClient) -> None:
    data = _payload(due_date="2020-01-01")
    response = client.post(BASE, json=data)
    assert response.status_code == 422
    assert "due_date" in response.text


def test_due_date_today_or_future_ok(client: TestClient) -> None:
    future = (_dt.date.today() + _dt.timedelta(days=30)).isoformat()
    data = _payload(due_date=future)
    assert client.post(BASE, json=data).status_code == 201


# ---------------------------------------------------------------------------
# 16. scanner_run_id é persistido e retornado
# ---------------------------------------------------------------------------


def test_scanner_run_id_persisted(client: TestClient) -> None:
    run_id = "ef8139c3-07cb-400c-8c48-e319623dbacf"
    created = client.post(
        BASE,
        json=_payload(scanner_run_id=run_id, origin="SCANNER"),
    ).json()
    assert created["scanner_run_id"] == run_id
    fetched = client.get(f"{BASE}/{created['id']}").json()
    assert fetched["scanner_run_id"] == run_id


# ---------------------------------------------------------------------------
# 17. related_file_path aceita caminho relativo
# ---------------------------------------------------------------------------


def test_related_file_path_relative(client: TestClient) -> None:
    path = "Gerenciamento_financeiro/2025/Marco/Fundos e taxas/planilha.ods"
    created = client.post(BASE, json=_payload(related_file_path=path)).json()
    assert created["related_file_path"] == path


# ---------------------------------------------------------------------------
# 18. Criação com status terminal valida regras específicas do status
# ---------------------------------------------------------------------------


def test_create_with_status_resolved_without_resolution_summary_rejected(
    client: TestClient,
) -> None:
    data = _payload(status="RESOLVED")
    response = client.post(BASE, json=data)
    assert response.status_code == 422
    assert "resolution_summary" in response.text


def test_create_with_status_resolved_without_evidence_or_notes_rejected(
    client: TestClient,
) -> None:
    data = _payload(status="RESOLVED", resolution_summary="Corrigido.")
    response = client.post(BASE, json=data)
    assert response.status_code == 422


def test_create_with_status_resolved_with_valid_fields_ok(client: TestClient) -> None:
    future = (_dt.date.today() + _dt.timedelta(days=7)).isoformat()
    data = _payload(
        status="RESOLVED",
        resolution_summary="POPs revisados e aprovados.",
        notes="Aprovado em reunião de 2026-05-10.",
        due_date=future,
    )
    response = client.post(BASE, json=data)
    assert response.status_code == 201
    assert response.json()["status"] == "RESOLVED"


def test_create_with_status_dismissed_without_reason_rejected(client: TestClient) -> None:
    data = _payload(status="DISMISSED")
    response = client.post(BASE, json=data)
    assert response.status_code == 422


def test_create_with_status_dismissed_with_reason_ok(client: TestClient) -> None:
    data = _payload(
        status="DISMISSED",
        dismissed_reason="Achado não se aplica a este ambiente.",
    )
    response = client.post(BASE, json=data)
    assert response.status_code == 201
    assert response.json()["status"] == "DISMISSED"


def test_create_with_status_archived_without_notes_rejected(client: TestClient) -> None:
    data = _payload(status="ARCHIVED")
    response = client.post(BASE, json=data)
    assert response.status_code == 422


def test_create_with_status_archived_with_notes_ok(client: TestClient) -> None:
    data = _payload(status="ARCHIVED", notes="Importado de sistema legado já encerrado.")
    response = client.post(BASE, json=data)
    assert response.status_code == 201
    assert response.json()["status"] == "ARCHIVED"


# ---------------------------------------------------------------------------
# Testes de integridade: outros módulos não afetados
# ---------------------------------------------------------------------------


def test_health_still_works(client: TestClient) -> None:
    assert client.get("/api/v1/health").status_code == 200


def test_finance_entries_still_work(client: TestClient) -> None:
    response = client.get("/api/v1/finance/entries")
    assert response.status_code == 200
