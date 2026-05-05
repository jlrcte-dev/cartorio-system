"""Testes do módulo LGPD — Sprint LGPD-1.

Cobre importação CSV, CRUD básico, filtros, summary, export e histórico
de mudança de status. Usa o fixture `client` do conftest.py (banco in-memory).
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from fastapi.testclient import TestClient

BASE = "/api/v1/lgpd"

VALID_CSV_HEADER = (
    '"ID Ação","Atividade/Entregável","Categoria","Ações","Justificativa da ação",'
    '"Departamento/Unidade","Tipo de Ação","Nível de Prioridade","Responsável\nExecutante",'
    '"Data Passagem","Data Previsão","Data Conclusão","Status","Observação / Detalhe da ação"'
)


def _row(
    code: str,
    title: str,
    category: str = "Governança",
    description: str = "",
    justification: str = "",
    department: str = "TI",
    action_type: str = "Recomendação",
    priority: str = "Média",
    responsible: str = "Cliente",
    data_passagem: str = "",
    data_previsao: str = "",
    data_conclusao: str = "",
    status: str = "Pendente",
    observacao: str = "",
) -> list[str]:
    return [
        code,
        title,
        category,
        description,
        justification,
        department,
        action_type,
        priority,
        responsible,
        data_passagem,
        data_previsao,
        data_conclusao,
        status,
        observacao,
    ]


def _build_csv(rows: list[list[str]]) -> bytes:
    buf = io.StringIO()
    buf.write(VALID_CSV_HEADER + "\n")
    writer = csv.writer(buf, lineterminator="\n", quoting=csv.QUOTE_ALL)
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode("utf-8")


def _upload(client: TestClient, csv_bytes: bytes, filename: str = "plano.csv") -> dict:
    response = client.post(
        f"{BASE}/actions/import",
        files={"file": (filename, csv_bytes, "text/csv")},
    )
    assert response.status_code == 200, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Importação
# ---------------------------------------------------------------------------


def test_import_real_csv_25_actions(client: TestClient) -> None:
    """Importa o Plano de Ação real da INOVA com 25 ações."""
    csv_path = (
        Path(__file__).resolve().parent.parent
        / "_local_data"
        / "LGPD - inova"
        / "Plano de Ação.csv"
    )
    if not csv_path.exists():
        # Em ambientes sem o arquivo real, ignora silenciosamente.
        return
    raw = csv_path.read_bytes()
    report = _upload(client, raw, filename="Plano de Ação.csv")
    assert report["imported_count"] == 25
    assert report["error_count"] == 0
    assert report["final_summary"]["total"] == 25
    # Verifica algumas ações conhecidas
    list_resp = client.get(f"{BASE}/actions?limit=500")
    assert list_resp.status_code == 200
    codes = [a["action_code"] for a in list_resp.json()]
    assert "AC-01" in codes
    assert "AC-25" in codes
    assert len(codes) == 25


def test_import_minimal_csv(client: TestClient) -> None:
    csv = _build_csv(
        [
            _row("AC-01", "Definir diretório", category="Governança", status="Pendente"),
            _row(
                "AC-02",
                "Política de Descarte",
                category="Governança",
                action_type="Obrigatório",
                priority="Alta",
                status="Finalizada",
                data_conclusao="2023-03-10T08:00:00Z",
            ),
        ]
    )
    report = _upload(client, csv)
    assert report["total_rows"] == 2
    assert report["imported_count"] == 2
    assert report["skipped_count"] == 0
    assert report["error_count"] == 0


def test_import_rejects_csv_without_required_columns(client: TestClient) -> None:
    bad = b'"ID","Title"\n"AC-01","x"\n'
    response = client.post(
        f"{BASE}/actions/import",
        files={"file": ("bad.csv", bad, "text/csv")},
    )
    assert response.status_code == 400, response.text
    assert "obrigatórias" in response.json()["detail"]


def test_import_rejects_empty_file(client: TestClient) -> None:
    response = client.post(
        f"{BASE}/actions/import",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert response.status_code == 400


def test_import_is_idempotent_does_not_duplicate(client: TestClient) -> None:
    csv = _build_csv([_row("AC-01", "Algo")])
    r1 = _upload(client, csv)
    assert r1["imported_count"] == 1
    r2 = _upload(client, csv)
    assert r2["imported_count"] == 0
    assert r2["skipped_count"] == 1
    assert "AC-01" in r2["duplicated_action_codes"]


def test_import_normalizes_status_category_type_priority(client: TestClient) -> None:
    csv = _build_csv(
        [
            _row(
                "AC-01",
                "X",
                category="Governança",
                action_type="Obrigatório",
                priority="Alta",
                status="Finalizada",
            ),
            _row(
                "AC-02",
                "Y",
                category="Implantação",
                action_type="Recomendação",
                priority="Média",
                status="Em andamento",
            ),
            _row(
                "AC-03",
                "Z",
                category="Preparação",
                action_type="Obrigatório",
                priority="Baixa",
                status="Concluida",
            ),
        ]
    )
    _upload(client, csv)
    a1 = client.get(f"{BASE}/actions/AC-01").json()
    assert a1["status"] == "COMPLETED"
    assert a1["category"] == "GOVERNANCA"
    assert a1["action_type"] == "OBRIGATORIO"
    assert a1["priority"] == "ALTA"
    assert a1["original_status"] == "Finalizada"
    a2 = client.get(f"{BASE}/actions/AC-02").json()
    assert a2["status"] == "IN_PROGRESS"
    assert a2["category"] == "IMPLANTACAO"
    a3 = client.get(f"{BASE}/actions/AC-03").json()
    assert a3["status"] == "COMPLETED"
    assert a3["category"] == "PREPARACAO"
    assert a3["priority"] == "BAIXA"


def test_import_unknown_status_falls_back_to_pending(client: TestClient) -> None:
    csv = _build_csv([_row("AC-01", "X", status="Quem sabe")])
    _upload(client, csv)
    a = client.get(f"{BASE}/actions/AC-01").json()
    assert a["status"] == "PENDING"
    assert a["original_status"] == "Quem sabe"


def test_import_accepts_empty_dates(client: TestClient) -> None:
    csv = _build_csv([_row("AC-01", "X", data_passagem="", data_previsao="")])
    report = _upload(client, csv)
    assert report["imported_count"] == 1
    assert report["error_count"] == 0
    a = client.get(f"{BASE}/actions/AC-01").json()
    assert a["planned_date"] is None
    assert a["due_date"] is None


def test_import_iso_dates(client: TestClient) -> None:
    csv = _build_csv(
        [
            _row(
                "AC-01",
                "X",
                data_passagem="2023-03-01T08:00:00Z",
                data_previsao="2023-03-10T08:00:00Z",
                data_conclusao="2023-03-10",
                status="Finalizada",
            )
        ]
    )
    _upload(client, csv)
    a = client.get(f"{BASE}/actions/AC-01").json()
    assert a["planned_date"] == "2023-03-01"
    assert a["due_date"] == "2023-03-10"
    assert a["completed_date"] == "2023-03-10"


def test_import_brazilian_dates(client: TestClient) -> None:
    csv = _build_csv([_row("AC-01", "X", data_passagem="01/03/2023", data_previsao="10/03/2023")])
    _upload(client, csv)
    a = client.get(f"{BASE}/actions/AC-01").json()
    assert a["planned_date"] == "2023-03-01"
    assert a["due_date"] == "2023-03-10"


def test_import_invalid_date_records_error_but_continues(client: TestClient) -> None:
    csv = _build_csv(
        [
            _row("AC-01", "X", data_previsao="not-a-date"),
            _row("AC-02", "Y"),
        ]
    )
    report = _upload(client, csv)
    assert report["imported_count"] == 1
    assert report["error_count"] == 1
    assert report["errors"][0]["line"] == 2


def test_import_invalid_action_code_is_error(client: TestClient) -> None:
    csv = _build_csv([_row("XYZ-01", "X")])
    report = _upload(client, csv)
    assert report["imported_count"] == 0
    assert report["error_count"] == 1


def test_import_strips_html_from_description(client: TestClient) -> None:
    csv = _build_csv(
        [
            _row(
                "AC-01",
                "X",
                description='<font face="Segoe UI" size="1">Definir diretório</font>',
                justification="<font>Linha 1</font><br><font>Linha 2</font>",
            )
        ]
    )
    _upload(client, csv)
    a = client.get(f"{BASE}/actions/AC-01").json()
    assert a["description"] == "Definir diretório"
    assert "Linha 1" in a["justification"]
    assert "Linha 2" in a["justification"]
    assert "<" not in a["justification"]


# ---------------------------------------------------------------------------
# Listagem & filtros
# ---------------------------------------------------------------------------


def _seed_basic(client: TestClient) -> None:
    csv = _build_csv(
        [
            _row(
                "AC-01",
                "Política A",
                category="Governança",
                priority="Alta",
                action_type="Obrigatório",
                status="Pendente",
                department="TI",
                responsible="Cliente",
            ),
            _row(
                "AC-02",
                "Política B",
                category="Implantação",
                priority="Média",
                action_type="Recomendação",
                status="Em andamento",
                department="RH",
                responsible="InovaLGPD",
            ),
            _row(
                "AC-03",
                "Política C",
                category="Governança",
                priority="Alta",
                action_type="Obrigatório",
                status="Finalizada",
                department="TI",
                responsible="Cliente",
            ),
        ]
    )
    _upload(client, csv)


def test_list_returns_all(client: TestClient) -> None:
    _seed_basic(client)
    r = client.get(f"{BASE}/actions")
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_list_filter_by_status(client: TestClient) -> None:
    _seed_basic(client)
    r = client.get(f"{BASE}/actions?status=COMPLETED")
    codes = [a["action_code"] for a in r.json()]
    assert codes == ["AC-03"]


def test_list_filter_by_category(client: TestClient) -> None:
    _seed_basic(client)
    r = client.get(f"{BASE}/actions?category=GOVERNANCA")
    codes = sorted(a["action_code"] for a in r.json())
    assert codes == ["AC-01", "AC-03"]


def test_list_filter_by_priority(client: TestClient) -> None:
    _seed_basic(client)
    r = client.get(f"{BASE}/actions?priority=ALTA")
    codes = sorted(a["action_code"] for a in r.json())
    assert codes == ["AC-01", "AC-03"]


def test_list_filter_by_action_type(client: TestClient) -> None:
    _seed_basic(client)
    r = client.get(f"{BASE}/actions?action_type=RECOMENDACAO")
    codes = [a["action_code"] for a in r.json()]
    assert codes == ["AC-02"]


def test_list_filter_by_department(client: TestClient) -> None:
    _seed_basic(client)
    r = client.get(f"{BASE}/actions?department=RH")
    codes = [a["action_code"] for a in r.json()]
    assert codes == ["AC-02"]


def test_list_filter_by_responsible(client: TestClient) -> None:
    _seed_basic(client)
    r = client.get(f"{BASE}/actions?responsible_party=InovaLGPD")
    codes = [a["action_code"] for a in r.json()]
    assert codes == ["AC-02"]


def test_get_action_by_code(client: TestClient) -> None:
    _seed_basic(client)
    r = client.get(f"{BASE}/actions/AC-01")
    assert r.status_code == 200
    assert r.json()["title"] == "Política A"


def test_get_action_unknown_returns_404(client: TestClient) -> None:
    _seed_basic(client)
    r = client.get(f"{BASE}/actions/AC-99")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# PATCH e histórico de status
# ---------------------------------------------------------------------------


def test_patch_updates_status_and_creates_history(client: TestClient) -> None:
    _seed_basic(client)
    r = client.patch(
        f"{BASE}/actions/AC-01",
        json={"status": "IN_PROGRESS", "reason": "Iniciado em reunião", "updated_by": "joao"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "IN_PROGRESS"
    assert r.json()["updated_by"] == "joao"

    h = client.get(f"{BASE}/actions/AC-01/history")
    assert h.status_code == 200
    history = h.json()
    assert len(history) == 1
    assert history[0]["previous_status"] == "PENDING"
    assert history[0]["new_status"] == "IN_PROGRESS"
    assert history[0]["reason"] == "Iniciado em reunião"
    assert history[0]["changed_by"] == "joao"


def test_patch_status_to_completed_sets_completed_date(client: TestClient) -> None:
    _seed_basic(client)
    r = client.patch(f"{BASE}/actions/AC-01", json={"status": "COMPLETED"})
    assert r.status_code == 200
    assert r.json()["completed_date"] is not None


def test_patch_invalid_status_value_returns_422(client: TestClient) -> None:
    _seed_basic(client)
    r = client.patch(f"{BASE}/actions/AC-01", json={"status": "WHATEVER"})
    assert r.status_code == 422


def test_patch_invalid_transition_completed_to_pending_returns_422(client: TestClient) -> None:
    _seed_basic(client)
    r = client.patch(f"{BASE}/actions/AC-03", json={"status": "PENDING"})
    assert r.status_code == 422


def test_patch_rejects_action_code_field(client: TestClient) -> None:
    _seed_basic(client)
    r = client.patch(f"{BASE}/actions/AC-01", json={"action_code": "AC-99"})
    # extra="forbid" → 422
    assert r.status_code == 422


def test_patch_no_status_change_no_history(client: TestClient) -> None:
    _seed_basic(client)
    r = client.patch(f"{BASE}/actions/AC-01", json={"notes": "anotação"})
    assert r.status_code == 200
    assert r.json()["notes"] == "anotação"
    h = client.get(f"{BASE}/actions/AC-01/history").json()
    assert h == []


def test_patch_unknown_action_returns_404(client: TestClient) -> None:
    r = client.patch(f"{BASE}/actions/AC-99", json={"notes": "x"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def test_summary_returns_zero_when_empty(client: TestClient) -> None:
    r = client.get(f"{BASE}/actions/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["total_actions"] == 0
    assert body["completion_percentage"] == 0.0


def test_summary_counts_match(client: TestClient) -> None:
    _seed_basic(client)
    body = client.get(f"{BASE}/actions/summary").json()
    assert body["total_actions"] == 3
    assert body["completed"] == 1
    assert body["in_progress"] == 1
    assert body["pending"] == 1
    assert body["by_category"]["GOVERNANCA"] == 2
    assert body["by_category"]["IMPLANTACAO"] == 1
    assert body["by_priority"]["ALTA"] == 2
    assert body["by_priority"]["MEDIA"] == 1
    assert body["by_status"]["PENDING"] == 1
    assert body["by_status"]["IN_PROGRESS"] == 1
    assert body["by_status"]["COMPLETED"] == 1


def test_summary_completion_percentage(client: TestClient) -> None:
    _seed_basic(client)
    body = client.get(f"{BASE}/actions/summary").json()
    # 1 completed of 3 total ≈ 33.33%
    assert abs(body["completion_percentage"] - 33.33) < 0.1


def test_summary_overdue_count(client: TestClient) -> None:
    csv = _build_csv(
        [
            _row(
                "AC-01",
                "X",
                data_previsao="2020-01-01",  # passado
                status="Pendente",
            ),
            _row(
                "AC-02",
                "Y",
                data_previsao="2020-01-01",
                status="Finalizada",
            ),
            _row(
                "AC-03",
                "Z",
                # sem data_previsao
            ),
        ]
    )
    _upload(client, csv)
    body = client.get(f"{BASE}/actions/summary").json()
    assert body["overdue_count"] == 1
    assert body["actions_without_due_date"] == 1


# ---------------------------------------------------------------------------
# Export CSV
# ---------------------------------------------------------------------------


def test_export_csv_header(client: TestClient) -> None:
    r = client.get(f"{BASE}/actions/export.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert r.headers["content-disposition"].startswith("attachment")
    first_line = r.text.splitlines()[0]
    expected = (
        "action_code,title,category,priority,action_type,responsible_party,department,"
        "status,original_status,planned_date,due_date,completed_date,notes"
    )
    assert first_line == expected


def test_export_csv_contains_imported_actions(client: TestClient) -> None:
    _seed_basic(client)
    r = client.get(f"{BASE}/actions/export.csv")
    lines = r.text.splitlines()
    assert len(lines) == 4  # header + 3 rows
    body = "\n".join(lines[1:])
    assert "AC-01" in body
    assert "AC-02" in body
    assert "AC-03" in body
    assert "Política A" in body


# ---------------------------------------------------------------------------
# Smoke: rota raiz LGPD não conflita com outras
# ---------------------------------------------------------------------------


def test_other_modules_still_reachable(client: TestClient) -> None:
    # health check + finance entries listing devem permanecer funcionando
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/finance/entries").status_code == 200


# ---------------------------------------------------------------------------
# Detalhe do CSV: cabeçalho real da INOVA com prefixo ListSchema
# ---------------------------------------------------------------------------


def test_import_handles_inova_listschema_prefix(client: TestClient) -> None:
    csv_body = _build_csv([_row("AC-10", "Algo")])
    prefixed = b'ListSchema={"schemaXmlList":["..."]}\n' + csv_body
    report = _upload(client, prefixed)
    assert report["imported_count"] == 1
    a = client.get(f"{BASE}/actions/AC-10").json()
    assert a["title"] == "Algo"
