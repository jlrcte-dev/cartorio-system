"""export-atlas do Financeiro: contrato próprio fechado, vínculo, recusas e publicação.

Só fixtures sintéticas (tests/finance_snapshot_support.py). Nenhum teste toca rede,
credencial, coletor real ou dado da fonte.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.modules.drive_capture import store
from app.modules.drive_capture.config import CaptureConfig, FileSource, FolderSource
from app.modules.drive_capture.store import RunLock
from app.modules.finance_snapshot import atlas_export, cli, layout, pipeline, report
from app.modules.finance_snapshot.atlas_export import (
    EXPORT_FILE,
    EXPORT_FORMAT,
    EXPORT_VERSION,
    ExportFailed,
    ExportRejected,
    export_atlas,
    strict_loads,
    validate_export,
)
from app.modules.finance_snapshot.pipeline import LATEST, LATEST_MD, analyze
from tests.finance_snapshot_support import DESCRIPTIONS, PEOPLE, PROTOCOL, F, N, day, xlsx_bytes
from tests.test_finance_snapshot import ALIAS, CAPTURED, FILE_ID, PERIOD, RUN, _capture, _config

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "docs" / "modules" / "finance_snapshot_atlas.example.json"
EXPORTED = datetime(2026, 10, 22, 18, 30, tzinfo=UTC)
PERIODO = "2026-10"
# Marcadores privados das fixtures: nada disso pode sair no contrato, no terminal ou em erro.
MARKERS = [*PEOPLE, PROTOCOL, *DESCRIPTIONS, FILE_ID, "PIX ficticio extra", "Resumo", "Feriado"]


def example_sheets() -> list[dict]:
    """Um item de cada situação que o contrato precisa preservar."""
    zero = F("SUM(C7:C21)", "0"), F("SUM(D7:D21)", "0")
    return [
        day("Resumo"),  # 1 ignorada (nome sem data)
        day(  # 2 PIX: fórmula omite linhas e a soma de todas as linhas DIVERGE
            "0510",
            pix=[
                (31, "PIX ficticio extra", N("5")),
                (33, "PIX a", N("80")),
                (34, "TED b", N("20")),
            ],
        ),
        day(  # 3 diferença negativa com 3 casas; malote zero; continuidade confere
            "0610",
            body=None,
            caixa_inicial=N("200.25"),
            malote=N("0"),
            teorico=F("(C4+C22-D22-C23)", "320.5"),
            conferido=N("320.375"),
            diferenca=F("C26-C24", "-0.125"),
        ),
        day(  # 4 sem contagem manual; PIX com fórmula que cobre o bloco; continuidade diverge
            "0710",
            caixa_inicial=N("1"),
            conferido=None,
            pix_total=F("SUM(C31:C39)", "100"),
        ),
        day(  # 5 sem lançamento na cópia; malote é fórmula sem resultado (null com motivo)
            "0810",
            lanc=[],
            totais=zero,
            malote=F("C99"),
            pix=[],
            pix_total=F("SUM(C33:C39)", "0"),
            protesto=[],
            protesto_totais=(F("SUM(H31:H39)", "0"), F("SUM(I31:I39)", "0"), F("0", "0")),
            maq=[],
            maq_totais=(F("SUM(C45:C49)", "0"), F("SUM(D45:D49)", "0")),
        ),
        day("1210 - Feriado"),  # 6 feriado: valores preservados
        day("1310", drop={(28, 2)}),  # 7 bloco não localizado → fora do padrão
        day("1410"),  # 8 data repetida
        day("1410"),  # 9 data repetida
        day("1510"),  # 10 base ambígua (14/10 repetida)
        day("2210"),  # 11 data de referência (captura em 22/10, America/Sao_Paulo)
        day("2310"),  # 12 futura: sem checagem de dia observado
    ]


@pytest.fixture(autouse=True)
def _fixed_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    # A CLI usa o relógio real; a captura sintética é de 22/10/2026 15:00 UTC.
    monkeypatch.setattr(atlas_export, "utc_now", lambda: EXPORTED)


def _cfg_file(tmp: Path, alias: str = ALIAS) -> Path:
    cfg = tmp / "config.yaml"
    cfg.write_text(
        "version: 1\n"
        f"credentials_file: {(tmp / 'chave.json').as_posix()}\n"
        "expected_identity: leitor@exemplo.iam.gserviceaccount.com\n"
        "data_dir: .\n"
        f"files:\n  - alias: {alias}\n    family: gerenciamento_financeiro\n"
        f"    file_id: {FILE_ID}\n"
        "folders: []\n",
        encoding="utf-8",
    )
    return cfg


def _analyze(tmp: Path, sheets: list[dict] | None = None, period: tuple = PERIOD) -> dict:
    _capture(tmp, xlsx_bytes(sheets or example_sheets()))
    return analyze(_config(tmp), RUN, period, clock=lambda: CAPTURED)


def _export(tmp: Path, when: datetime = EXPORTED, **over: object) -> dict:
    return export_atlas(_config(tmp, **over), RUN, PERIODO, clock=lambda: when)


def _out(tmp: Path) -> Path:
    return tmp / "finance_snapshot"


def _failed(tmp: Path, run: str = RUN, period: str = PERIODO, **over: object) -> ExportFailed:
    with pytest.raises(ExportFailed) as exc:
        export_atlas(_config(tmp, **over), run, period, clock=lambda: EXPORTED)
    return exc.value


def _inputs(tmp: Path) -> dict[str, bytes]:
    return {n: (_out(tmp) / n).read_bytes() for n in (LATEST, LATEST_MD)}


def example_export(tmp: Path) -> dict:
    """Fonte do exemplo documentado: produtor real, relógios fixos."""
    _analyze(tmp)
    _export(tmp)
    return json.loads((_out(tmp) / EXPORT_FILE).read_text(encoding="utf-8"))


def _day(exp: dict, pos: int) -> dict:
    return exp["dias"][pos - 1]


# -- contrato e cenário principal -----------------------------------------------------------


def test_documented_example_is_the_producer_output(tmp_path: Path) -> None:
    example = example_export(tmp_path)
    validate_export(example)
    assert json.loads(EXAMPLE.read_text(encoding="utf-8")) == example
    text = EXAMPLE.read_text(encoding="utf-8")
    assert not [m for m in MARKERS if m in text]


def test_report_to_export_flow_preserves_days_states_and_values(tmp_path: Path) -> None:
    rep = _analyze(tmp_path)
    before = _inputs(tmp_path)
    exp = _export(tmp_path)
    raw = (_out(tmp_path) / EXPORT_FILE).read_bytes()
    assert strict_loads(raw) == exp
    validate_export(strict_loads(raw))
    assert _inputs(tmp_path) == before  # latest.json e latest.md intactos

    assert (exp["formato"], exp["versao"]) == (EXPORT_FORMAT, EXPORT_VERSION)
    assert exp["origem"] == {
        "formato_local": "cartorio_system.finance_snapshot.local",
        "versao_local": "0.1",
        "escopo": "fonte_financeira_unica",
        "fonte_alias": ALIAS,
        "familia": "gerenciamento_financeiro",
        "run_id": RUN,
    }
    assert exp["periodo"] == PERIODO
    assert exp["tempos"] == {
        "capturada_em": rep["origem"]["capturada_em"],
        "relatorio_gerado_em": rep["gerado_em"],
        "exportado_em": "2026-10-22T18:30:00+00:00",
        "referencia_indicadores": "2026-10-22",
        "fuso_referencia": "America/Sao_Paulo",
    }
    # Procedência técnica do XLSX fica no relatório privado; atualização não existe aqui.
    flat = json.dumps(exp)
    for absent in ("sha256", "drive_version", "drive_modified_time", "bytes", "atualizacao"):
        assert f'"{absent}":' not in flat

    # Uma entrada por aba, como lista: ignorada e datas repetidas continuam presentes.
    assert len(exp["dias"]) == len(rep["abas"]) == 12
    assert [d["posicao"] for d in exp["dias"]] == list(range(1, 13))
    assert [(d["estado"], d["motivo_estado"]) for d in exp["dias"]] == [
        (t["estado"], t["motivo_estado"]) for t in rep["abas"]
    ]
    ignored = _day(exp, 1)
    assert (ignored["data"], ignored["temporalidade"], ignored["blocos"]) == (None, None, None)
    assert ignored["motivo_estado"] == "nome_sem_data"
    assert [_day(exp, p)["data"] for p in (8, 9)] == ["2026-10-14", "2026-10-14"]
    assert {_day(exp, p)["motivo_estado"] for p in (8, 9)} == {"data_repetida"}
    assert [d["temporalidade"] for d in exp["dias"]][-3:] == ["anterior", "referencia", "futura"]

    # Decimal como texto, sem float nem arredondamento; zero é zero; null tem motivo.
    d3 = _day(exp, 3)["blocos"]["dinheiro"]
    assert d3["diferenca"] == {"valor": "-0.125", "motivo": None}
    assert d3["retirada_malote"] == {"valor": "0", "motivo": None}
    assert _day(exp, 3)["checagens"]["conferencia"] == {
        "estado": "valida",
        "motivo": None,
        "sinal": "nao_zero",
    }
    assert _day(exp, 2)["checagens"]["conferencia"]["sinal"] == "zero"
    assert exp["cobertura"]["valores_com_mais_de_duas_casas"] == 2
    assert _day(exp, 5)["estado"] == "sem_lancamento"
    assert _day(exp, 5)["blocos"]["dinheiro"]["retirada_malote"] == {
        "valor": None,
        "motivo": "formula_sem_resultado",
    }
    # Sem contagem manual: diferença não vira conferência.
    d4 = _day(exp, 4)
    assert d4["checagens"]["conferencia"] == {
        "estado": "sem_conferencia",
        "motivo": None,
        "sinal": None,
    }
    assert d4["blocos"]["dinheiro"]["diferenca"] == {"valor": None, "motivo": "sem_conferencia"}
    # Bloco indisponível: null com motivo, nunca zero; sem checagem.
    d7 = _day(exp, 7)
    assert (d7["estado"], d7["motivo_estado"]) == ("fora_do_padrao", "bloco_nao_localizado")
    cash = d7["blocos"]["dinheiro"]
    assert cash["localizado"] is False and cash["registros"] is None
    assert cash["caixa_inicial"] == {"valor": None, "motivo": "bloco_indisponivel"}
    assert d7["checagens"]["conferencia"]["estado"] == "nao_aplicavel"

    # Continuidade: base e distância preservadas; indisponível sem base inventada.
    cont = [d["checagens"]["continuidade"] for d in exp["dias"]]
    assert cont[1] == {
        "estado": "indisponivel",
        "motivo": "sem_base",
        "base_data": None,
        "dias_desde_base": None,
    }
    assert (cont[2]["estado"], cont[2]["base_data"], cont[2]["dias_desde_base"]) == (
        "confere",
        "2026-10-05",
        1,
    )
    assert cont[3]["estado"] == "diverge"
    assert (cont[9]["motivo"], cont[9]["base_data"]) == ("base_ambigua", "2026-10-14")
    assert cont[11] == {
        "estado": "nao_aplicavel",
        "motivo": "data_futura",
        "base_data": None,
        "dias_desde_base": None,
    }
    future = _day(exp, 12)["checagens"]
    assert {c["estado"] for c in (*future["soma"].values(), future["data_corpo"])} == {
        "nao_aplicavel"
    }

    # Agregados e checagens: exatamente os do relatório validado.
    assert exp["cobertura"] == rep["cobertura"]
    assert exp["checagens"] == rep["checagens"]
    assert exp["limitacoes"] == rep["limitacoes"]


def test_pix_formula_limitation_survives_both_diverge_and_equal_sums(tmp_path: Path) -> None:
    rep = _analyze(tmp_path)
    exp = _export(tmp_path)
    diverge, equal, covers = _day(exp, 2), _day(exp, 6), _day(exp, 4)
    for d, state in ((diverge, "diverge"), (equal, "confere")):
        assert d["blocos"]["pix"] == {
            "localizado": True,
            "motivo": None,
            "total": {"valor": "100", "motivo": None},  # o publicado, nunca a soma
            "formula_do_total": "omite_linhas",
        }
        assert d["checagens"]["soma"]["pix"] == {"estado": state, "motivo": None}
    assert covers["blocos"]["pix"]["formula_do_total"] == "cobre_o_bloco"
    assert exp["limitacoes"][-1] == "pix_total_publicado_omite_linhas_do_bloco"
    assert exp["cobertura"]["pix_formula_do_total"] == rep["cobertura"]["pix_formula_do_total"]
    # Maquininha ("Total em transferências") e protesto continuam blocos próprios.
    blocks = diverge["blocos"]
    assert blocks["maquininha"] == {
        "localizado": True,
        "motivo": None,
        "total_a_receber": {"valor": "97.5", "motivo": None},
        "total_cobrado": {"valor": "100", "motivo": None},
    }
    assert blocks["protesto"]["registros"] == 1
    assert blocks["protesto"]["total_emolumentos"] == {"valor": "50", "motivo": None}
    assert set(blocks) == {"dinheiro", "verificacao", "pix", "protesto", "maquininha"}


def test_limitation_absent_when_every_pix_formula_covers_the_block(tmp_path: Path) -> None:
    covers = F("SUM(C31:C39)", "100")
    _analyze(tmp_path, [day("0510", pix_total=covers), day("0610", pix_total=covers)])
    exp = _export(tmp_path)
    assert "pix_total_publicado_omite_linhas_do_bloco" not in exp["limitacoes"]
    bad = copy.deepcopy(exp)
    bad["limitacoes"].append("pix_total_publicado_omite_linhas_do_bloco")
    with pytest.raises(ExportRejected):
        validate_export(bad)


def test_reexport_of_old_capture_renews_only_exportado_em(tmp_path: Path) -> None:
    _analyze(tmp_path)
    first = _export(tmp_path)
    later = _export(tmp_path, when=datetime(2026, 11, 30, 12, 0, tzinfo=UTC))
    assert later["tempos"]["exportado_em"] == "2026-11-30T12:00:00+00:00"
    for key in ("capturada_em", "relatorio_gerado_em", "referencia_indicadores"):
        assert later["tempos"][key] == first["tempos"][key]
    first["tempos"].pop("exportado_em")
    later["tempos"].pop("exportado_em")
    assert later == first  # nada mais muda: a captura não é renovada pela exportação


def test_later_capture_may_hold_a_past_period(tmp_path: Path) -> None:
    _analyze(tmp_path, [day("2909"), day("3009")], period=(2026, 9))
    exp = export_atlas(_config(tmp_path), RUN, "2026-09", clock=lambda: EXPORTED)
    assert exp["periodo"] == "2026-09"
    assert exp["tempos"]["referencia_indicadores"] == "2026-10-22"
    assert {d["temporalidade"] for d in exp["dias"]} == {"anterior"}


def test_contract_enumerations_are_explicit_and_match_the_local_format_today() -> None:
    """O contrato não importa as listas internas; este teste avisa quando elas mudarem."""
    assert {b: list(f) for b, f in atlas_export.BLOCKS.items()} == layout.BLOCK_KEYS
    assert [
        k
        for b in atlas_export.BLOCKS
        for k, kind in atlas_export.BLOCKS[b].items()
        if kind == atlas_export.MONEY
    ] == [f for b in layout.BLOCKS for f in layout.BLOCK_FIELDS[b]]
    assert list(atlas_export.SUMS) == layout.SUM_FIELDS
    pairs = [
        (atlas_export.VALUE_REASONS, layout.VALUE_REASONS),
        (atlas_export.BLOCK_REASONS, layout.BLOCK_REASONS),
        (atlas_export.SUM_REASONS, layout.SUM_REASONS),
        (atlas_export.FORMULA_COVERAGE, layout.FORMULA_COVERAGE),
        (atlas_export.STATES, report.STATES),
        (
            [*atlas_export.IGNORED_REASONS, *atlas_export.OUT_OF_PATTERN_REASONS],
            report.STATE_REASONS,
        ),
        (atlas_export.TEMPORAL, report.TEMPORAL),
        (atlas_export.CONFERENCE, report.CONFERENCE),
        (atlas_export.CONTINUITY, report.CONTINUITY),
        (atlas_export.CONTINUITY_REASONS, report.CONTINUITY_REASONS),
        (atlas_export.SUM_STATES, report.SUM_STATES),
        (atlas_export.BODY_DATE, report.BODY_DATE),
        (atlas_export.NA_REASONS, report.NA_REASONS),
        (atlas_export.LIMITATIONS, report.LIMITATIONS),
        ([atlas_export.PIX_LIMITATION], [report.PIX_FORMULA_LIMITATION]),
        ([atlas_export.FAMILY], [report.FAMILY]),
    ]
    for ours, theirs in pairs:
        assert ours == theirs
        assert ours is not theirs


# -- validação do contrato (recusa, nunca conserto) ------------------------------------------


def _bump(path: list, value: object) -> object:
    def mutate(exp: dict) -> None:
        target = exp
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    return mutate


D2 = ["dias", 1]
CASH2 = [*D2, "blocos", "dinheiro"]


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (_bump(["extra"], 1), "exportacao_invalida"),
        (_bump([*CASH2, "descricao"], "x"), "exportacao_invalida"),
        (lambda e: e["origem"].pop("run_id"), "exportacao_invalida"),
        (_bump(["versao"], "1.1"), "exportacao_invalida"),
        (_bump([*CASH2, "registros"], True), "exportacao_invalida"),
        (_bump([*CASH2, "registros"], -1), "exportacao_invalida"),
        (_bump([*CASH2, "registros"], 3.0), "exportacao_invalida"),
        (_bump([*CASH2, "registros"], "3"), "exportacao_invalida"),
        (_bump([*CASH2, "caixa_inicial", "valor"], 100), "exportacao_invalida"),
        (_bump([*CASH2, "caixa_inicial", "valor"], "100.50"), "exportacao_invalida"),
        (_bump([*CASH2, "caixa_inicial", "valor"], "١٠٠"), "exportacao_invalida"),
        (_bump([*CASH2, "caixa_inicial", "motivo"], "vazio"), "exportacao_invalida"),
        (
            _bump([*CASH2, "saldo_conferido"], {"valor": None, "motivo": None}),
            "exportacao_invalida",
        ),
        (_bump([*CASH2, "localizado"], "sim"), "exportacao_invalida"),
        (_bump([*D2, "estado"], "aprovado"), "exportacao_invalida"),
        (_bump([*D2, "posicao"], 5), "exportacao_invalida"),
        (_bump([*D2, "checagens", "conferencia", "sinal"], "nao_zero"), "exportacao_invalida"),
        (_bump(["dias", 3, "checagens", "conferencia", "sinal"], "zero"), "exportacao_invalida"),
        (
            _bump([*CASH2, "saldo_conferido"], {"valor": None, "motivo": "vazio"}),
            "exportacao_invalida",
        ),
        (
            _bump(["dias", 2, "checagens", "continuidade", "base_data"], "2026-10-04"),
            "exportacao_invalida",
        ),
        (
            _bump(["dias", 2, "checagens", "continuidade", "dias_desde_base"], 2),
            "exportacao_invalida",
        ),
        (
            _bump(["dias", 1, "checagens", "continuidade", "base_data"], "2026-10-01"),
            "exportacao_invalida",
        ),
        (
            _bump(["dias", 11, "checagens", "data_corpo"], {"estado": "concorda", "motivo": None}),
            "exportacao_invalida",
        ),
        (
            _bump([*D2, "checagens", "soma", "pix", "motivo"], "parcela_invalida"),
            "exportacao_invalida",
        ),
        (_bump(["dias", 6, "blocos", "dinheiro", "localizado"], True), "exportacao_invalida"),
        (_bump(["cobertura", "por_estado", "preenchido"], 99), "exportacao_invalida"),
        (_bump(["cobertura", "valores_com_mais_de_duas_casas"], 0), "exportacao_invalida"),
        (_bump(["checagens", "continuidade", "confere"], 0), "exportacao_invalida"),
        (lambda e: e["limitacoes"].pop(), "exportacao_invalida"),
        (lambda e: e["dias"].pop(8), "exportacao_invalida"),
        (_bump(["dias"], []), "exportacao_invalida"),
        (_bump([*D2, "temporalidade"], "futura"), "inconsistencia_temporal"),
        (_bump([*D2, "data"], "2026-09-05"), "inconsistencia_temporal"),
        (_bump([*D2, "data"], "2026-10-32"), "inconsistencia_temporal"),
        (_bump(["tempos", "exportado_em"], "2026-10-22T14:00:00+00:00"), "inconsistencia_temporal"),
        (_bump(["tempos", "capturada_em"], "2026-13-01T00:00:00Z"), "inconsistencia_temporal"),
        (_bump(["tempos", "referencia_indicadores"], "2026-10-23"), "inconsistencia_temporal"),
    ],
)
def test_export_validation_refuses_and_never_fixes(tmp_path: Path, mutate, code: str) -> None:  # noqa: ANN001
    bad = copy.deepcopy(example_export(tmp_path))
    mutate(bad)
    with pytest.raises(ExportRejected) as exc:
        validate_export(bad)
    assert exc.value.code == code
    assert not [m for m in ("Fulano", "١٠٠", "aprovado") if m in str(exc.value)]


# -- vínculo e entrada ------------------------------------------------------------------------


def _published(tmp: Path) -> bytes:
    return (_out(tmp) / EXPORT_FILE).read_bytes()


def test_missing_report_exits_3_without_creating_anything(tmp_path: Path) -> None:
    failed = _failed(tmp_path)
    assert (failed.code, failed.exit_code) == ("sem_relatorio", 3)
    assert not _out(tmp_path).exists()
    _out(tmp_path).mkdir()
    failed = _failed(tmp_path)
    assert (failed.code, failed.exit_code) == ("sem_relatorio", 3)
    assert list(_out(tmp_path).iterdir()) == []


@pytest.mark.parametrize(
    "over",
    [
        {"files": (FileSource(ALIAS, "protestos", FILE_ID),)},
        {
            "files": (
                FileSource(ALIAS, "gerenciamento_financeiro", FILE_ID),
                FileSource("outra_fonte", "gerenciamento_financeiro", "1OutroIdSinteticoBBBBBBBB"),
            )
        },
        {
            "folders": (
                FolderSource("pasta", "gerenciamento_financeiro", "1PastaSintCCCCCCCC", ("x",)),
            )
        },
    ],
)
def test_out_of_scope_config_is_refused_before_reading(
    tmp_path: Path, over: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _analyze(tmp_path)

    def no_read(*_a: object, **_k: object) -> None:
        raise AssertionError("conteúdo lido com config fora do recorte")

    monkeypatch.setattr(atlas_export, "_read", no_read)
    assert _failed(tmp_path, **over).code == "fora_do_recorte_financeiro"


def test_source_run_and_period_must_match_and_preserve_previous(tmp_path: Path) -> None:
    _analyze(tmp_path)
    _export(tmp_path)
    before = _published(tmp_path)
    other = (FileSource("financeiro_outro", "gerenciamento_financeiro", FILE_ID),)
    assert _failed(tmp_path, files=other).code == "fonte_divergente"
    assert _failed(tmp_path, run="20261022T160000Z-ffffff").code == "run_divergente"
    assert _failed(tmp_path, period="2026-09").code == "periodo_divergente"
    assert _failed(tmp_path, period="2026-9").code == "argumento_invalido"
    assert _published(tmp_path) == before


def _set_report(tmp: Path, raw: bytes) -> None:
    (_out(tmp) / LATEST).write_bytes(raw)


def _report_with(tmp: Path, mutate) -> bytes:  # noqa: ANN001
    rep = json.loads((_out(tmp) / LATEST).read_text(encoding="utf-8"))
    mutate(rep)
    return json.dumps(rep, ensure_ascii=False).encode("utf-8")


@pytest.mark.parametrize(
    ("make", "code"),
    [
        (lambda t: b"\xff\xfe" + PEOPLE[0].encode("utf-16"), "entrada_invalida"),
        (lambda t: b'{"formato": ', "entrada_invalida"),
        (lambda t: b'{"formato": "a", "formato": "b"}', "entrada_invalida"),
        (lambda t: b'{"x": NaN}', "entrada_invalida"),
        (lambda t: b'{"x": -Infinity}', "entrada_invalida"),
        (lambda t: b'{"x": 1e400}', "entrada_invalida"),
        (lambda t: b"[]", "formato_nao_suportado"),
        (
            lambda t: _report_with(t, lambda r: r.__setitem__("versao", "0.2")),
            "formato_nao_suportado",
        ),
        (
            lambda t: _report_with(t, lambda r: r.__setitem__("formato", "outro")),
            "formato_nao_suportado",
        ),
        (lambda t: _report_with(t, lambda r: r.__setitem__("nota", PEOPLE[0])), "entrada_invalida"),
        (
            lambda t: _report_with(
                t, lambda r: r["abas"][1]["blocos"]["pix"].__setitem__("descricao", PROTOCOL)
            ),
            "entrada_invalida",
        ),
        (
            lambda t: _report_with(t, lambda r: r["cobertura"].__setitem__("abas_total", 99)),
            "entrada_invalida",
        ),
        (
            lambda t: _report_with(
                t, lambda r: r.__setitem__("gerado_em", "2026-10-21T00:00:00+00:00")
            ),
            "inconsistencia_temporal",
        ),
        (
            lambda t: _report_with(
                t, lambda r: r["origem"].__setitem__("capturada_em", "2026-02-30T10:00:00Z")
            ),
            "inconsistencia_temporal",
        ),
        (
            lambda t: _report_with(t, lambda r: r["referencia"].__setitem__("data", "2026-10-21")),
            "inconsistencia_temporal",
        ),
    ],
)
def test_invalid_input_is_refused_and_previous_export_preserved(
    tmp_path: Path,
    make,
    code: str,
    capsys: pytest.CaptureFixture,  # noqa: ANN001
) -> None:
    _analyze(tmp_path)
    _export(tmp_path)
    before = _published(tmp_path)
    _set_report(tmp_path, make(tmp_path))
    failed = _failed(tmp_path)
    assert (failed.code, failed.exit_code, failed.file_state) == (code, 2, None)
    assert _published(tmp_path) == before
    cfg = _cfg_file(tmp_path)
    args = ["export-atlas", "--config", str(cfg), "--run-id", RUN, "--periodo", PERIODO]
    assert cli.main(args) == 2
    err = capsys.readouterr().err
    assert f"código {code}" in err and "preservada" in err
    assert not [m for m in (*MARKERS, str(tmp_path)) if m in err]


def test_read_failure_is_controlled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _analyze(tmp_path)
    _export(tmp_path)
    before = _published(tmp_path)
    real = Path.read_bytes

    def read_bytes(self: Path) -> bytes:
        if self.name == LATEST:
            raise PermissionError("negado")
        return real(self)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    assert _failed(tmp_path).code == "leitura_falhou"
    monkeypatch.undo()
    assert _published(tmp_path) == before


# -- publicação ---------------------------------------------------------------------------------


def _fail_tmp_write(monkeypatch: pytest.MonkeyPatch) -> None:
    real = store._write_private

    def write(path: Path, data: bytes) -> None:
        if path.name.endswith(".tmp"):
            raise OSError("disco")
        real(path, data)

    monkeypatch.setattr(store, "_write_private", write)


def _fail_replace(monkeypatch: pytest.MonkeyPatch) -> None:
    real = os.replace

    def replace(src: object, dst: object) -> None:
        if Path(dst).name == EXPORT_FILE:
            raise OSError("troca")
        real(src, dst)

    monkeypatch.setattr(os, "replace", replace)


def _fail_serialize(monkeypatch: pytest.MonkeyPatch) -> None:
    def serialize(_e: dict) -> bytes:
        raise TypeError("não serializável")

    monkeypatch.setattr(atlas_export, "serialize", serialize)


def _no_tmp_left(tmp: Path) -> bool:
    return not [p for p in _out(tmp).iterdir() if p.name.endswith(".tmp")]


@pytest.mark.parametrize(
    ("breaker", "code"),
    [
        (_fail_tmp_write, "falha_ao_gravar"),
        (_fail_replace, "falha_ao_gravar"),
        (_fail_serialize, "falha_ao_serializar"),
    ],
)
def test_failure_before_the_swap_preserves_previous_byte_for_byte(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    breaker,
    code: str,  # noqa: ANN001
) -> None:
    _analyze(tmp_path)
    _export(tmp_path)
    before = _published(tmp_path)
    breaker(monkeypatch)
    failed = _failed(tmp_path)
    assert failed.code == code
    assert failed.file_state in (None, "preservada")
    assert _published(tmp_path) == before
    assert _no_tmp_left(tmp_path) and not (_out(tmp_path) / "run.lock").exists()


@pytest.mark.parametrize("breaker", [_fail_tmp_write, _fail_replace])
def test_first_publication_failure_leaves_no_final_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    breaker,
    capsys: pytest.CaptureFixture,  # noqa: ANN001
) -> None:
    _analyze(tmp_path)
    breaker(monkeypatch)
    failed = _failed(tmp_path)
    assert (failed.code, failed.file_state) == ("falha_ao_gravar", "ausente")
    assert not (_out(tmp_path) / EXPORT_FILE).exists() and _no_tmp_left(tmp_path)
    cfg = _cfg_file(tmp_path)
    assert (
        cli.main(["export-atlas", "--config", str(cfg), "--run-id", RUN, "--periodo", PERIODO]) == 2
    )
    assert "nenhum arquivo final foi criado" in capsys.readouterr().err


def test_failure_after_the_swap_reports_the_real_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """O auxiliar do coletor limpa o temporário DEPOIS do os.replace: falha ali já não
    preserva nada, e a mensagem não pode prometer o contrário."""
    _analyze(tmp_path)
    _export(tmp_path)
    before = _published(tmp_path)
    real = Path.unlink

    def unlink(self: Path, missing_ok: bool = False) -> None:
        if self.name.endswith(".tmp"):
            raise PermissionError("limpeza")
        real(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", unlink)
    later = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)
    with pytest.raises(ExportFailed) as exc:
        _export(tmp_path, when=later)
    assert (exc.value.code, exc.value.file_state) == ("gravado_com_falha_posterior", "substituida")
    now = json.loads(_published(tmp_path))
    assert _published(tmp_path) != before
    assert now["tempos"]["exportado_em"] == "2026-10-23T09:00:00+00:00"
    validate_export(now)
    monkeypatch.setattr(atlas_export, "utc_now", lambda: datetime(2026, 10, 24, tzinfo=UTC))
    cfg = _cfg_file(tmp_path)
    assert (
        cli.main(["export-atlas", "--config", str(cfg), "--run-id", RUN, "--periodo", PERIODO]) == 2
    )
    err = capsys.readouterr().err
    assert "JÁ é a nova exportação" in err and "preservada" not in err


def test_lock_blocks_only_another_export_and_is_not_removed(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    _analyze(tmp_path)
    _export(tmp_path)
    before = _published(tmp_path)
    lock = _out(tmp_path) / "run.lock"
    with RunLock(_out(tmp_path), "outra-exportacao"):
        held = lock.read_bytes()
        failed = _failed(tmp_path)
        assert (failed.code, failed.exit_code) == ("exportacao_em_andamento", 4)
        assert lock.read_bytes() == held  # trava alheia intacta
        cfg = _cfg_file(tmp_path)
        args = ["export-atlas", "--config", str(cfg), "--run-id", RUN, "--periodo", PERIODO]
        assert cli.main(args) == 4
        err = capsys.readouterr().err
        assert "exportação financeira em andamento" in err and "análise" not in err
        # A trava não é do analyze: ele continua publicando com ela presente.
        analyze(_config(tmp_path), RUN, PERIOD, clock=lambda: CAPTURED)
    assert _published(tmp_path) == before
    _export(tmp_path)
    assert not lock.exists()


def test_lock_left_after_publication_is_reported_as_published(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _analyze(tmp_path)

    def stuck(*_a: object) -> None:
        raise PermissionError("trava")

    monkeypatch.setattr(RunLock, "__exit__", stuck)
    failed = _failed(tmp_path)
    assert (failed.code, failed.file_state) == ("trava_nao_removida", "substituida")
    validate_export(json.loads(_published(tmp_path)))


def test_services_files_are_untouched(tmp_path: Path) -> None:
    services = tmp_path / "services_snapshot"
    services.mkdir()
    (services / EXPORT_FILE).write_bytes(b'{"formato": "servicos"}')
    _analyze(tmp_path)
    _export(tmp_path)
    assert (services / EXPORT_FILE).read_bytes() == b'{"formato": "servicos"}'
    assert sorted(p.name for p in services.iterdir()) == [EXPORT_FILE]


# -- isolamento e sigilo -------------------------------------------------------------------------


def test_export_never_reads_xlsx_runs_analyze_or_the_collector(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _analyze(tmp_path)
    shutil.rmtree(tmp_path / "sources")  # sem gerações retidas: só o latest.json existe
    before = _inputs(tmp_path)

    def forbidden(*_a: object, **_k: object) -> None:
        raise AssertionError("caminho proibido na exportação")

    from app.modules.drive_capture import collector
    from app.modules.services_snapshot import pipeline as services_pipeline
    from app.modules.services_snapshot import xlsx

    monkeypatch.setattr(pipeline, "analyze", forbidden)
    monkeypatch.setattr(services_pipeline, "bind_generation", forbidden)
    monkeypatch.setattr(xlsx, "parse_workbook", forbidden)
    monkeypatch.setattr(collector.Collector, "__init__", forbidden)
    validate_export(_export(tmp_path))
    assert _inputs(tmp_path) == before


def test_cli_export_runs_without_google_and_with_network_blocked(tmp_path: Path) -> None:
    _analyze(tmp_path)
    cfg = _cfg_file(tmp_path)
    code = (
        "import sys, socket\n"
        "class B:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name.split('.')[0] in {'google', 'requests', 'urllib3'}:\n"
        "            raise ModuleNotFoundError(name)\n"
        "sys.meta_path.insert(0, B())\n"
        "def no_net(*a, **k):\n"
        "    raise OSError('rede bloqueada no teste')\n"
        "socket.socket.connect = no_net; socket.create_connection = no_net\n"
        "socket.getaddrinfo = no_net\n"
        "from app.modules.finance_snapshot import cli\n"
        f"rc = cli.main(['export-atlas', '--config', r'{cfg}', '--run-id', '{RUN}',"
        f" '--periodo', '{PERIODO}'])\n"
        "bad = [m for m in sys.modules if m.startswith(('google', 'requests', 'urllib3',"
        " 'app.modules.drive_capture.collector', 'app.modules.drive_capture.drive_client',"
        " 'app.modules.drive_capture.auth'))]\n"
        "print('rc', rc, 'bad', bad)\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT, check=True
    )
    assert "rc 0 bad []" in out.stdout


def test_cli_success_prints_only_codes_counts_and_technical_metadata(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    _analyze(tmp_path)
    cfg = _cfg_file(tmp_path)
    args = ["export-atlas", "--config", str(cfg), "--run-id", RUN, "--periodo", PERIODO]
    assert cli.main(args) == 0
    out = capsys.readouterr()
    text = out.out + out.err
    assert "atlas_snapshot.json" in text and RUN in text and "preenchido" in text
    values = ["150.25", "200.25", "97.5", "-0.125", "320.375", "2026-10-05"]
    assert not [m for m in (*MARKERS, *values, str(tmp_path)) if m in text]
    published = _published(tmp_path).decode("utf-8")
    assert not [m for m in (*MARKERS, str(tmp_path), tmp_path.as_posix()) if m in published]
    # Argumentos continuam obrigatórios e com formato conferido.
    assert (
        cli.main(["export-atlas", "--config", str(cfg), "--run-id", RUN, "--periodo", "2026-13"])
        == 2
    )
    with pytest.raises(SystemExit):
        cli.main(["export-atlas", "--config", str(cfg), "--run-id", RUN])


def test_config_paths_never_reach_the_contract(tmp_path: Path) -> None:
    cfg: CaptureConfig = _config(tmp_path)
    _analyze(tmp_path)
    text = json.dumps(_export(tmp_path))
    assert str(cfg.data_dir) not in text and str(cfg.credentials_file) not in text


# -- continuidade: o estado declarado precisa ser o único compatível com os campos -----------


def _contradict(rep: dict, case: str) -> None:
    """Adultera UM dia mantendo cobertura e totais coerentes: só a continuidade contradiz."""
    abas = rep["abas"]
    if case == "confere_com_valores_diferentes":  # 06/10: base 05/10 tem teórico 200.25
        abas[2]["blocos"]["dinheiro"]["caixa_inicial"]["valor"] = "999"
    elif case == "diverge_com_valores_iguais":  # 07/10: base 06/10 tem teórico 320.5
        abas[3]["blocos"]["dinheiro"]["caixa_inicial"]["valor"] = "320.5"
    elif case == "base_sem_saldo_com_base_completa":
        abas[2]["checagens"]["continuidade"].update(estado="indisponivel", motivo="base_sem_saldo")
        rep["checagens"]["continuidade"]["confere"] -= 1
        rep["checagens"]["continuidade"]["indisponivel"] += 1


CONTRADICTIONS = [
    "confere_com_valores_diferentes",
    "diverge_com_valores_iguais",
    "base_sem_saldo_com_base_completa",
]


@pytest.mark.parametrize("case", CONTRADICTIONS)
def test_contradictory_continuity_passes_the_local_reader_but_is_refused(
    tmp_path: Path, case: str, capsys: pytest.CaptureFixture
) -> None:
    _analyze(tmp_path)
    _export(tmp_path)
    before = _published(tmp_path)
    rep = json.loads((_out(tmp_path) / LATEST).read_text(encoding="utf-8"))
    _contradict(rep, case)
    report.validate_report(rep)  # o leitor local aceita: a recusa é do contrato externo
    _set_report(tmp_path, json.dumps(rep, ensure_ascii=False).encode("utf-8"))
    inputs = _inputs(tmp_path)

    failed = _failed(tmp_path)
    assert (failed.code, failed.exit_code, failed.file_state) == ("exportacao_invalida", 2, None)
    cfg = _cfg_file(tmp_path)
    args = ["export-atlas", "--config", str(cfg), "--run-id", RUN, "--periodo", PERIODO]
    assert cli.main(args) == 2
    err = capsys.readouterr().err
    assert "código exportacao_invalida" in err and "999" not in err and "320.5" not in err
    assert _published(tmp_path) == before
    assert _inputs(tmp_path) == inputs


@pytest.mark.parametrize("case", CONTRADICTIONS)
def test_validator_refuses_contradictory_continuity_with_coherent_counts(
    tmp_path: Path, case: str
) -> None:
    exp = example_export(tmp_path)
    days = exp["dias"]
    if case == "confere_com_valores_diferentes":
        days[2]["blocos"]["dinheiro"]["caixa_inicial"]["valor"] = "999"
    elif case == "diverge_com_valores_iguais":
        days[3]["blocos"]["dinheiro"]["caixa_inicial"]["valor"] = "320.5"
    else:
        days[2]["checagens"]["continuidade"].update(estado="indisponivel", motivo="base_sem_saldo")
        exp["checagens"]["continuidade"]["confere"] -= 1
        exp["checagens"]["continuidade"]["indisponivel"] += 1
    limits, coverage, checks = atlas_export.recount(days)  # o resto continua coerente
    assert (limits, coverage, checks) == (exp["limitacoes"], exp["cobertura"], exp["checagens"])
    with pytest.raises(ExportRejected) as exc:
        validate_export(exp)
    assert exc.value.code == "exportacao_invalida"
    assert str(exc.value).endswith("checagens.continuidade")


def test_valid_continuity_states_are_all_accepted(tmp_path: Path) -> None:
    no_result = F("(C4+C22-D22-C23)")
    sheets = [
        day("0110"),  # sem base
        day("0210", caixa_inicial=N("200.25"), teorico=F("(C4+C22-D22-C23)", "320.125")),
        day("0310", caixa_inicial=N("320.124"), teorico=F("(C4+C22-D22-C23)", "0")),
        day("0410", caixa_inicial=N("0")),  # zero igual a zero
        day("0510", drop={(4, 3)}),  # caixa inicial atual ausente
        day("0610"),  # base sem caixa inicial próprio
        day("0710", teorico=no_result),
        day("0810", drop={(4, 3)}),  # base sem teórico E caixa atual ausente: precedência
        day("0910", drop={(28, 2)}),  # inelegível
        day("1010"),
        day("1110"),
        day("1110"),
        day("1210"),
        day("2310"),  # futura
    ]
    rep = _analyze(tmp_path, sheets)
    exp = _export(tmp_path)
    got = [
        (c["estado"], c["motivo"]) for c in (d["checagens"]["continuidade"] for d in exp["dias"])
    ]
    assert got == [
        ("indisponivel", "sem_base"),
        ("confere", None),
        ("diverge", None),  # diferença de 0.001
        ("confere", None),
        ("indisponivel", "caixa_inicial_indisponivel"),
        ("indisponivel", "base_sem_saldo"),
        ("diverge", None),
        ("indisponivel", "base_sem_saldo"),
        ("nao_aplicavel", "estado_nao_elegivel"),
        ("indisponivel", "base_fora_do_padrao"),
        ("nao_aplicavel", "estado_nao_elegivel"),  # data repetida
        ("nao_aplicavel", "estado_nao_elegivel"),
        ("indisponivel", "base_ambigua"),
        ("nao_aplicavel", "data_futura"),
    ]
    assert got == [
        (t["checagens"]["continuidade"]["estado"], t["checagens"]["continuidade"]["motivo"])
        for t in rep["abas"]
    ]
    validate_export(json.loads(_published(tmp_path)))
