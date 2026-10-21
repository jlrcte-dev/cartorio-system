"""Datas do retrato: conversão estrita, referência congelada na captura e agregados."""

from __future__ import annotations

import copy
import json
from datetime import UTC, date, datetime, timedelta

import pytest

from app.modules.services_snapshot.dates import capture_reference, from_serial, from_text
from app.modules.services_snapshot.report import (
    ReportRejected,
    build_report,
    render_markdown,
    validate_report,
)
from app.modules.services_snapshot.rules import classify_workbook
from app.modules.services_snapshot.xlsx import parse_workbook
from tests.services_snapshot_support import (
    PEOPLE,
    STD,
    Number,
    Serial,
    as_legacy_v10,
    row,
    xlsx_bytes,
)

REF = date(2026, 10, 20)
CAPTURED = "2026-10-21T01:13:49Z"  # 22:13 de 20/10 em America/Sao_Paulo
RI_HEADERS = [*STD, "Vencimento da Prenotação", "PRENOTAÇÃO"]


def serial(d: date, *, date1904: bool = False) -> Serial:
    base = date(1904, 1, 1) if date1904 else date(1899, 12, 30)
    return Serial((d - base).days)


def ago(days: int) -> Serial:
    return serial(REF - timedelta(days=days))


def ahead(days: int) -> Serial:
    return serial(REF + timedelta(days=days))


def _tabs(sheets: list[dict], *, date1904: bool = False, reference: date = REF) -> list[dict]:
    return classify_workbook(parse_workbook(xlsx_bytes(sheets, date1904=date1904)), reference)


def _one(rows: list, headers: list[str] = STD, name: str = "Escrituras", **kw: object) -> dict:
    (tab,) = _tabs([{"name": name, "headers": headers, "rows": rows}], **kw)  # type: ignore[arg-type]
    return tab


def _report(tabs: list[dict], captured_at: str = CAPTURED, reference: date = REF) -> dict:
    report = build_report(
        source_alias="servicos_andamento_piloto",
        family="documentos_em_andamento",
        run_id="20261021T011343Z-662a7f",
        captured_at=captured_at,
        drive_modified_time=None,
        drive_version="20",
        tabs=tabs,
        reference=reference,
        generated_at=datetime(2026, 10, 21, 1, 14, tzinfo=UTC),
    )
    validate_report(report)
    return report


# --------------------------------------------------------------------------- conversão


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", date(1900, 1, 1)),
        ("59", date(1900, 2, 28)),
        ("60", None),  # 29/02/1900 fictício
        ("61", date(1900, 3, 1)),
        ("45292", date(2024, 1, 1)),
        ("45292.75", date(2024, 1, 1)),  # hora descartada, sem deslocar o dia
        ("0", None),  # sentinela "00/01/1900", não ausência
        ("0.5", None),
        ("-3", None),
        ("nan", None),
        ("inf", None),
        ("1e12", None),
        ("abc", None),
    ],
)
def test_serial_in_1900_system(raw: str, expected: date | None) -> None:
    assert from_serial(raw, False) == expected


def test_serial_in_1904_system() -> None:
    assert from_serial("43830", True) == date(2024, 1, 1)
    assert from_serial("0", True) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("05/03/2026", date(2026, 3, 5)),  # dia/mês, nunca mês/dia
        ("5/3/2026", date(2026, 3, 5)),
        (" 2026-03-05 ", date(2026, 3, 5)),
        ("03/05/26", None),  # ano com dois dígitos
        ("2026-3-5", None),
        ("31/02/2026", None),
        ("05/03/2026 10:00", None),
        ("2026/03/05", None),
        ("03-05-2026", None),
        ("ontem", None),
        ("", None),
        ("٠٥/٠٣/٢٠٢٦", None),
    ],
)
def test_text_dates_only_in_documented_formats(text: str, expected: date | None) -> None:
    assert from_text(text) == expected


def test_capture_reference_is_the_civil_date_in_sao_paulo() -> None:
    assert capture_reference(CAPTURED) == date(2026, 10, 20)  # em UTC já é 21/10
    assert capture_reference("2026-10-21T03:00:00Z") == date(2026, 10, 21)
    assert capture_reference("ontem") is None and capture_reference(None) is None


def test_only_date_styled_numbers_and_explicit_text_become_dates() -> None:
    value = (REF - date(1899, 12, 30)).days - 3
    cells = [
        Serial(value, style=1),  # interno 14
        Serial(value, style=2),  # dd/mm/yyyy
        "05/10/2026",
        Serial(value, style=3),  # "0.00": número, não data
        Serial(value, style=4),  # [h]:mm: tempo decorrido
        Number(value),  # General
        "ontem",
        True,
        None,
        "   ",
    ]
    tab = _one([row("Em execução", inicio=v) for v in cells])
    cov = tab["datas"]["cobertura"]["cadastro"]["nao_encerrados"]
    assert cov == {"registros": 10, "validas": 3, "ausentes": 2, "invalidas": 5, "futuras": 0}


def test_same_serial_follows_the_declared_date_system() -> None:
    s = serial(date(2026, 10, 13))
    in_1900 = _one([row("Em execução", inicio=s)])
    in_1904 = _one([row("Em execução", inicio=s)], date1904=True)  # 4 anos depois
    assert in_1900["datas"]["idade_carteira"]["faixas"]["0_7"] == 1
    assert in_1904["datas"]["cobertura"]["cadastro"]["nao_encerrados"]["futuras"] == 1
    native = _one(
        [row("Em execução", inicio=serial(date(2026, 10, 13), date1904=True))], date1904=True
    )
    assert native["datas"]["idade_carteira"]["faixas"]["0_7"] == 1


# --------------------------------------------------------------------------- indicadores


def test_age_same_day_is_zero_and_band_limits() -> None:
    ages = [0, 7, 8, 15, 16, 30, 31, 60, 61, 400]
    rows = [row("Em execução", inicio=ago(a)) for a in ages] + [row("Bloqueada", inicio=ago(3))]
    age = _one(rows)["datas"]["idade_carteira"]
    assert age == {
        "base": 11,
        "calculaveis": 11,
        "faixas": {"0_7": 3, "8_15": 2, "16_30": 2, "31_60": 2, "mais_de_60": 2},
    }


def test_closed_groups_are_separate_and_status_still_classifies() -> None:
    rows = [
        row("Concluída", inicio=ago(10), termino=ago(4)),  # 6 dias
        row("Concluído", inicio=ago(10), termino=ago(0)),  # 10
        row("Concluído/entregue", inicio=ago(5), termino=ago(5)),  # 0
        row("Concluída", inicio=ago(3), termino=ago(8)),  # encerramento antes do cadastro
        row("Concluída", inicio=ago(3), termino=ahead(2)),  # encerramento futuro
        row("Concluída", inicio=ago(3)),  # encerrado sem data final
        row("Cancelada", inicio=ago(20), termino=ago(10)),  # 10
        row("Em execução", inicio=ago(2), termino=ago(1)),  # data final não encerra
        row("Em execução", inicio=ahead(1)),  # cadastro futuro
        row(None, inicio=ago(30), termino=ago(1)),  # sem status: fora de carteira e duração
        row("Talvez", inicio=ago(30), termino=ago(1)),
    ]
    tab = _one(rows)
    assert (
        tab["concluidos"],
        tab["cancelados"],
        tab["nao_encerrados_reconhecidos"],
        tab["status_ausente"],
        tab["status_nao_mapeado"],
    ) == (6, 1, 2, 1, 1)
    d = tab["datas"]
    assert d["duracao_conclusao"] == {
        "base": 6,
        "calculaveis": 3,
        "media_dias": 5.3,
        "mediana_dias": 6,
    }
    assert d["duracao_cancelamento"] == {
        "base": 1,
        "calculaveis": 1,
        "media_dias": 10.0,
        "mediana_dias": 10,
    }
    assert d["sinais"] == {
        "encerramento_anterior_ao_cadastro": 1,
        "nao_encerrado_com_data_final": 1,
        "encerrado_sem_data_final": 1,
    }
    assert (d["idade_carteira"]["base"], d["idade_carteira"]["calculaveis"]) == (2, 1)
    cad, enc = d["cobertura"]["cadastro"], d["cobertura"]["encerramento"]
    assert cad["nao_encerrados"]["futuras"] == 1
    assert enc["concluidos"] == {
        "registros": 6,
        "validas": 4,
        "ausentes": 1,
        "invalidas": 0,
        "futuras": 1,
    }
    assert cad["sem_status_reconhecido"]["registros"] == 2
    _report([tab])


def test_no_sample_means_null_not_zero() -> None:
    tab = _one([row("Concluída", inicio=ago(3)), row("Cancelada")])
    assert tab["datas"]["duracao_conclusao"] == {
        "base": 1,
        "calculaveis": 0,
        "media_dias": None,
        "mediana_dias": None,
    }
    assert tab["datas"]["idade_carteira"] == {
        "base": 0,
        "calculaveis": 0,
        "faixas": {"0_7": 0, "8_15": 0, "16_30": 0, "31_60": 0, "mais_de_60": 0},
    }
    _report([tab])


def test_header_aliases_and_ambiguous_date_fields() -> None:
    renamed = {"Data de início": "Data inicial", "Data de término": "Data final"}
    tab = _one(
        [row("Concluída", inicio=ago(5), termino=ago(1))],
        headers=[renamed.get(h, h) for h in STD],
    )
    assert tab["campos_ausentes"] == [] and tab["datas"]["duracao_conclusao"]["calculaveis"] == 1

    both = _one(
        [[*row("Concluída", inicio=ago(5), termino=ago(1)), ago(5)]], headers=[*STD, "Data inicial"]
    )
    d = both["datas"]
    assert d["campos"]["data_inicio"] == "ambiguo" and both["total"] == 1
    assert d["cobertura"]["cadastro"] is None and d["idade_carteira"] is None
    assert (
        d["duracao_conclusao"] is None and d["sinais"]["encerramento_anterior_ao_cadastro"] is None
    )
    assert d["sinais"]["encerrado_sem_data_final"] == 0  # o encerramento segue identificado
    assert "campo ambíguo" in render_markdown(_report([both]), None)


# --------------------------------------------------------------------------- prenotação


def _ri(status: str, due: object, protocol: object = "2026") -> list:
    return [*row(status, inicio=ago(1)), due, protocol]


def test_prenotation_due_date_buckets_and_protocol_never_becomes_a_date() -> None:
    rows = [
        _ri("Em execução", ago(1)),
        _ri("FALTA DOCS", serial(REF)),
        _ri("falta ass", ahead(1)),
        _ri("Pendente de protocolo", ahead(7)),
        _ri("Bloqueada", ahead(8)),
        _ri("Não iniciada", None, protocol=Serial(46000)),  # protocolo com estilo de data
        _ri("Em execução", "sem prazo"),
        _ri("Concluída", ago(30)),  # encerrado: fora da leitura de prenotação
    ]
    tab = _one(rows, headers=RI_HEADERS, name="Registro de Imóveis")
    assert tab["datas"]["campos"] == {
        "data_inicio": "identificado",
        "data_termino": "identificado",
        "data_prenotacao": "nao_identificado",
        "vencimento_prenotacao": "identificado",
    }
    assert tab["datas"]["prenotacao"] == {
        "base": 7,
        "data_prenotacao": None,
        "vencimento_informado": {
            "validos": 5,
            "ausentes": 1,
            "invalidos": 1,
            "anteriores_a_referencia": 1,
            "na_referencia": 1,
            "proximos_1_a_7_dias": 2,
            "alem_de_7_dias": 1,
        },
    }
    assert tab["campos_ignorados_nomeados"] == ["PRENOTAÇÃO"]
    md = render_markdown(_report([tab]), None)
    assert "data da prenotação: campo não identificado" in md
    assert "vencimento informado na planilha" in md and "não atesta prazo legal" in md


def test_prenotation_date_only_with_its_own_header_and_only_in_ri() -> None:
    headers = [*STD, "Data da prenotação"]
    rows = [
        [*row("Em execução", inicio=ago(9)), ago(4)],
        [*row("Em execução", inicio=ago(9)), None],  # ainda não prenotado: não é erro
        [*row("Em execução"), ago(10)],
        [*row("Concluída"), ago(2)],
    ]
    ri = _one(rows, headers=headers, name="Registro de Imóveis")
    assert ri["datas"]["prenotacao"]["data_prenotacao"] == {
        "validas": 2,
        "ausentes": 1,
        "invalidas": 0,
        "futuras": 0,
        "media_dias_desde": 7.0,
        "mediana_dias_desde": 7.0,
    }
    assert ri["datas"]["prenotacao"]["vencimento_informado"] is None
    assert _one(rows, headers=headers, name="Escrituras")["datas"]["prenotacao"] is None
    _report([ri])


def test_auxiliary_date_columns_do_not_create_services_or_change_totals() -> None:
    base_rows = [row("Concluída"), row("Em execução"), row(None), row("Talvez")]
    plain = _one(base_rows, name="Registro de Imóveis")
    with_aux = _one(
        [[*r, ago(1), "123"] for r in base_rows] + [[None] * 8 + [ago(1), "456"]],
        headers=RI_HEADERS,
        name="Registro de Imóveis",
    )
    keys = [
        "total",
        "categorias",
        "concluidos",
        "cancelados",
        "nao_encerrados_reconhecidos",
        "status_ausente",
        "status_nao_mapeado",
        "visiveis",
        "ocultos",
    ]
    assert {k: plain[k] for k in keys} == {k: with_aux[k] for k in keys}
    assert with_aux["linhas_desconsideradas"]["so_campos_ignorados"] == 1


# --------------------------------------------------------------------------- relatório


def test_aggregate_pools_samples_and_lists_tabs_with_each_field() -> None:
    no_end = [h for h in STD if h != "Data de término"]
    tabs = _tabs(
        [
            {
                "name": "Escrituras",
                "headers": STD,
                "rows": [
                    row("Concluída", inicio=ago(4), termino=ago(2)),
                    row("Em execução", inicio=ago(1)),
                ],
            },
            {
                "name": "Procurações",
                "headers": STD,
                "rows": [
                    row("Concluída", inicio=ago(30), termino=ago(0)),
                    row("Concluída", inicio=ago(10), termino=ago(0)),
                ],
            },
            {
                "name": "Diversos",
                "headers": no_end,
                "rows": [[v for i, v in enumerate(row("Concluída", inicio=ago(3))) if i != 5]],
            },
        ]
    )
    report = _report(tabs)
    agg = report["agregado"]["datas"]
    assert agg["abas_com_cadastro"] == ["aba_01", "aba_02", "aba_03"]
    assert agg["abas_com_encerramento"] == ["aba_01", "aba_02"]
    assert agg["duracao_conclusao"] == {
        "base": 3,
        "calculaveis": 3,
        "media_dias": 14.0,
        "mediana_dias": 10,
    }
    assert agg["idade_carteira"]["calculaveis"] == 1
    assert agg["cobertura"]["cadastro"]["concluidos"]["registros"] == 4
    assert "_amostras" not in json.dumps(report)
    assert report["agregado"]["total"] == 5  # totais por status intactos


def test_reference_is_frozen_at_capture_and_rendering_has_no_clock() -> None:
    old = date(2024, 1, 10)
    tab = _one([row("Em execução", inicio=serial(date(2024, 1, 1)))], reference=old)
    report = _report([tab], captured_at="2024-01-10T15:00:00Z", reference=old)
    assert report["referencia_temporal"] == {
        "data": "2024-01-10",
        "fuso": "America/Sao_Paulo",
        "base": "data_civil_da_captura",
    }
    assert report["abas"][0]["datas"]["idade_carteira"]["faixas"]["8_15"] == 1  # 9 dias, não anos
    md = render_markdown(report, None)
    reread = json.loads(json.dumps(report))
    validate_report(reread)
    assert "2024-01-10" in md and render_markdown(reread, None) == md

    mismatch = copy.deepcopy(report)
    mismatch["referencia_temporal"]["data"] = REF.isoformat()  # relógio da consulta
    with pytest.raises(ReportRejected):
        validate_report(mismatch)


def _sample_report() -> dict:
    return _report(
        _tabs(
            [
                {
                    "name": "Escrituras",
                    "headers": STD,
                    "rows": [
                        row("Concluída", inicio=ago(4), termino=ago(2)),
                        row("Em execução", inicio=ago(1)),
                    ],
                }
            ]
        )
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r["abas"][0]["datas"]["idade_carteira"]["faixas"].__setitem__("0_7", 99),
        lambda r: r["abas"][0]["datas"]["duracao_conclusao"].__setitem__(
            "media_dias", "05/03/2026"
        ),
        lambda r: r["abas"][0]["datas"]["duracao_conclusao"].__setitem__("media_dias", None),
        lambda r: r["abas"][0]["datas"]["duracao_conclusao"].__setitem__(
            "mediana_dias", float("nan")
        ),
        lambda r: r["abas"][0]["datas"].__setitem__("datas_individuais", ["2026-03-05"]),
        lambda r: r["abas"][0]["datas"]["cobertura"]["cadastro"]["concluidos"].__setitem__(
            "validas", 5
        ),
        lambda r: r["agregado"]["datas"]["sinais"].__setitem__("encerrado_sem_data_final", 7),
        lambda r: r["agregado"]["datas"].__setitem__("abas_com_cadastro", []),
        lambda r: r.__setitem__("versao", "1.0"),  # objeto novo rebatizado de antigo
        lambda r: r.__setitem__("versao", "1.2"),
    ],
)
def test_v11_schema_and_reconciliations_reject_tampering(mutate) -> None:  # noqa: ANN001
    bad = copy.deepcopy(_sample_report())
    mutate(bad)
    with pytest.raises(ReportRejected) as exc:
        validate_report(bad)
    assert "05/03/2026" not in str(exc.value) and "2026-03-05" not in str(exc.value)


def test_legacy_v10_is_read_and_never_relabelled_as_v11() -> None:
    report = _sample_report()
    legacy = as_legacy_v10(report)
    validate_report(legacy)
    md = render_markdown(legacy, None)
    assert "formato 1.0" in md and "## Datas" not in md
    assert "Datas não interpretadas" in md

    relabelled = copy.deepcopy(legacy)
    relabelled["versao"] = "1.1"
    with pytest.raises(ReportRejected):
        validate_report(relabelled)


def test_no_individual_dates_protocols_or_cell_values_leave_the_process() -> None:
    rows = [
        [*row("Concluída", inicio="05/03/2026", termino="2026-03-09"), "12/03/2026", "778899"],
        [*row("Em execução", inicio=Serial(46000)), Serial(46010), "PROT-55"],
    ]
    report = _report([_one(rows, headers=RI_HEADERS, name="Registro de Imóveis")])
    text = json.dumps(report, ensure_ascii=False) + render_markdown(report, None)
    for marker in [
        "05/03/2026",
        "2026-03-05",
        "2026-03-09",
        "12/03/2026",
        "778899",
        "PROT-55",
        "46000",
        "46010",
        "Escritura de compra",
        *PEOPLE,
    ]:
        assert marker not in text
