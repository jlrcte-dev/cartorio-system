"""Retrato de serviços: classificação calibrada, cobertura e formato local fechado."""

from __future__ import annotations

import copy
import json
from datetime import UTC, date, datetime

import pytest

from app.modules.services_snapshot.report import (
    ReportRejected,
    build_report,
    render_markdown,
    validate_report,
)
from app.modules.services_snapshot.rules import CATEGORIES, classify_workbook
from app.modules.services_snapshot.xlsx import XlsxError, parse_workbook
from tests.services_snapshot_support import PEOPLE, STD, row, standard_workbook, xlsx_bytes

REF = date(2026, 10, 20)  # data civil de captured_at abaixo em America/Sao_Paulo


def _tabs(sheets: list[dict]) -> list[dict]:
    return classify_workbook(parse_workbook(xlsx_bytes(sheets)), REF)


def _report(tabs: list[dict]) -> dict:
    report = build_report(
        source_alias="servicos_andamento_piloto",
        family="documentos_em_andamento",
        run_id="20261020T160054Z-8f95e2",
        captured_at="2026-10-20T16:00:59Z",
        drive_modified_time="2026-10-20T15:48:06.946Z",
        drive_version="11",
        tabs=tabs,
        reference=REF,
        generated_at=datetime(2026, 10, 21, 12, tzinfo=UTC),
    )
    validate_report(report)
    return report


def test_calibrated_status_rules_and_closed_vs_open() -> None:
    statuses = [
        "  em   EXECUÇÃO ",
        "FALTA ASS",
        "falta docs",
        "Falta Pagamento",
        "finalizacao",
        "Não iniciada",
        "BLOQUEADA",
        "Bloqueado",
        "Concluída",
        "concluído",
        "Concluído/entregue",
        "Cancelado",
        "cancelada",
        "Aguardando  Escritura",
        "PENDENTE DE PROTOCOLO",
    ]
    (tab,) = _tabs(
        [{"name": "Registro de Imóveis", "headers": STD, "rows": [row(s) for s in statuses]}]
    )
    c = tab["categorias"]
    assert (c["bloqueado"], c["concluido"], c["cancelado"]) == (2, 3, 2)
    assert all(c[k] == 1 for k in CATEGORIES if k not in ("bloqueado", "concluido", "cancelado"))
    assert (tab["concluidos"], tab["cancelados"], tab["nao_encerrados_reconhecidos"]) == (3, 2, 10)
    assert tab["status_nao_mapeado"] == 0 and all(tab["reconciliacoes"].values())


def test_empty_and_unknown_status_are_kept_apart_without_approximation() -> None:
    statuses = [None, "  ", "Concluído / entregue", "Cancelamento", "Concluídos", "bloq"]
    (tab,) = _tabs([{"name": "Procurações", "headers": STD, "rows": [row(s) for s in statuses]}])
    assert (tab["status_ausente"], tab["status_nao_mapeado"]) == (2, 4)
    assert sum(tab["categorias"].values()) == 0
    assert tab["nao_encerrados_reconhecidos"] == 0
    assert set(tab["nao_mapeados_por_alias"]) == {
        "desconhecido_01",
        "desconhecido_02",
        "desconhecido_03",
        "desconhecido_04",
    }


def test_hidden_rows_count_eligibility_and_shifted_columns() -> None:
    tabs = classify_workbook(parse_workbook(standard_workbook()), REF)
    esc, ri = tabs
    assert esc["setor"] == "Escrituras" and esc["total"] == 4
    assert (esc["visiveis"], esc["ocultos"]) == (2, 2)
    assert esc["status_ausente"] == 1 and esc["categorias"]["bloqueado"] == 1
    assert esc["linhas_desconsideradas"] == {
        "so_campos_ignorados": 0,
        "vazias": 2,
        "totais_subtotais": 0,
    }
    assert ri["setor"] == "Registro de Imóveis" and ri["categorias"]["cancelado"] == 1
    assert ri["campos_ignorados_nomeados"] == ["PRENOTAÇÃO"]


def test_only_ignored_column_situacao_alias_and_named_fields() -> None:
    headers = [*STD[:7], "Situação", "Outorgante", "Coluna X"]
    rows = [[*row("Concluída")[:7], "texto livre", "x", "y"], [None] * 8 + ["só outorgante", None]]
    (tab,) = _tabs([{"name": "Procurações", "headers": headers, "rows": rows}])
    assert tab["total"] == 1
    assert tab["campos_ausentes"] == []
    assert tab["linhas_desconsideradas"]["so_campos_ignorados"] == 1
    assert (tab["campos_ignorados_nomeados"], tab["campos_ignorados_outros"]) == (["Outorgante"], 1)


def test_sector_by_name_not_position_and_partial_coverage() -> None:
    tabs = _tabs(
        [
            {"name": "Planilha nova", "headers": STD, "rows": [row("Concluída")]},
            {"name": "Diversos", "headers": STD, "rows": [row("Concluída")]},
            {"name": "Registro Civil", "headers": ["Tarefa", "Prioridade"], "rows": [["a", "b"]]},
        ]
    )
    assert (tabs[0]["setor"], tabs[0]["vinculo_setor"]) == (None, "nao_vinculado")
    assert tabs[1]["setor"] == "Diversos"
    assert (tabs[2]["situacao"], tabs[2]["motivo"]) == (
        "schema_pending",
        "Status ausente no cabeçalho",
    )
    report = _report(tabs)
    cob = report["cobertura"]
    assert cob["qualidade"] == "parcial"
    assert cob["abas_pendentes"] == ["aba_03"] and cob["abas_sem_vinculo_de_setor"] == ["aba_01"]
    assert report["agregado"]["total"] == 2  # só abas interpretadas
    assert "pendente" in render_markdown(report, None)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r["abas"][0].__setitem__("observacao", "qualquer"),
        lambda r: r["abas"][0].__setitem__("setor", PEOPLE[0]),
        lambda r: r["abas"][0].__setitem__("setor", "aguardando pagamento registro"),
        lambda r: r["abas"][0]["nao_mapeados_por_alias"].__setitem__("talvez", 1),
        lambda r: r["agregado"].__setitem__("total", "10"),
        lambda r: r["captura"].__setitem__("capturada_em", "ontem às 13h"),
        lambda r: r["fonte"].__setitem__("alias", "Planilha do " + PEOPLE[1]),
        lambda r: r.__setitem__("extra", {}),
    ],
)
def test_report_schema_rejects_free_text_and_extra_fields(mutate) -> None:  # noqa: ANN001
    report = _report(classify_workbook(parse_workbook(standard_workbook()), REF))
    bad = copy.deepcopy(report)
    mutate(bad)
    with pytest.raises(ReportRejected) as exc:
        validate_report(bad)
    for marker in [*PEOPLE, "talvez", "qualquer", "ontem", "aguardando pagamento registro"]:
        assert marker not in str(exc.value)


def test_json_and_markdown_carry_no_cell_text() -> None:
    sheets = [
        {
            "name": "Escrituras",
            "headers": [*STD, "Cliente " + PEOPLE[2]],
            "rows": [
                [*row("Talvez " + PEOPLE[0], obs=PEOPLE[2]), "nota solta"],
                [*row("Concluída", tarefa="Inventário " + PEOPLE[1]), None],
            ],
        }
    ]
    report = _report(_tabs(sheets))
    text = json.dumps(report, ensure_ascii=False) + render_markdown(report, None)
    for marker in [*PEOPLE, "Talvez", "nota solta", "Inventário", "Alta", "45900"]:
        assert marker not in text


def test_corrupt_package_is_a_controlled_error() -> None:
    with pytest.raises(XlsxError) as exc:
        parse_workbook(b"PK\x03\x04" + b"lixo " + PEOPLE[0].encode())
    assert PEOPLE[0] not in str(exc.value)
