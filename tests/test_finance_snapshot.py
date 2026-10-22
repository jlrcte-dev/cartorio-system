"""Leitura local do Financeiro — só fixtures sintéticas (tests/finance_snapshot_support.py)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from app.modules.drive_capture.config import GOOGLE_SHEET, CaptureConfig, FileSource, FolderSource
from app.modules.drive_capture.store import Acquisition, CaptureStore
from app.modules.finance_snapshot import cli, pipeline
from app.modules.finance_snapshot.layout import canonical, money, read_day
from app.modules.finance_snapshot.pipeline import LATEST, LATEST_MD, AnalyzeFailed, analyze
from app.modules.finance_snapshot.report import (
    ReportRejected,
    parse_tab_name,
    render_summary,
    validate_report,
)
from app.modules.services_snapshot.xlsx import Cell, parse_workbook
from tests.finance_snapshot_support import (
    DESCRIPTIONS,
    PEOPLE,
    PROTOCOL,
    B,
    F,
    N,
    day,
    xlsx_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
FILE_ID = "1FinanceiroSinteticoAAAAAAAAAAAAAAAAAAAA"
ALIAS = "financeiro_teste"
RUN = "20261022T150000Z-abc123"
CAPTURED = datetime(2026, 10, 22, 15, 0, tzinfo=UTC)  # referência BRT: 22/10/2026
PERIOD = (2026, 10)


def _config(tmp: Path, **over: object) -> CaptureConfig:
    base = dict(
        credentials_file=tmp / "chave-inexistente.json",
        data_dir=tmp,
        expected_identity="leitor@exemplo.iam.gserviceaccount.com",
        files=(FileSource(ALIAS, "gerenciamento_financeiro", FILE_ID),),
    )
    base.update(over)
    return CaptureConfig(**base)  # type: ignore[arg-type]


def _capture(tmp: Path, content: bytes, run_id: str = RUN) -> CaptureStore:
    store = CaptureStore(tmp)
    acq = Acquisition(
        content=content,
        extension="xlsx",
        method="export_xlsx",
        source_mime=GOOGLE_SHEET,
        exported_mime=None,
        modified_time="2026-10-22T14:00:00.000Z",
        version="13",
        drive_size=None,
        drive_md5=None,
    )
    store.publish(
        ALIAS,
        FILE_ID,
        acq,
        alias=ALIAS,
        family="gerenciamento_financeiro",
        run_id=run_id,
        captured_at=CAPTURED,
    )
    return store


def _run(tmp: Path, sheets: list[dict]) -> dict:
    _capture(tmp, xlsx_bytes(sheets))
    return analyze(_config(tmp), RUN, PERIOD, clock=lambda: CAPTURED)


def _read(sheet: dict):  # noqa: ANN202
    return read_day(parse_workbook(xlsx_bytes([sheet]))[0])


def _tab(rep: dict, pos: int) -> dict:
    return rep["abas"][pos - 1]


# -- valores --------------------------------------------------------------------------------


def test_money_is_decimal_from_xml_text_and_never_zero_for_gaps() -> None:
    assert money(Cell(literal=("numero", "0.1"))) == (Decimal("0.1"), None)
    assert money(Cell(literal=("numero", "1E+3")))[0] == Decimal("1000")
    assert money(Cell(literal=("numero", "0"))) == (Decimal("0"), None)
    assert money(None) == (None, "vazio")
    assert money(Cell(literal=("texto", "  "))) == (None, "vazio")
    assert money(Cell(literal=("texto", "R$ 10"))) == (None, "nao_numerico")
    assert money(Cell(literal=("booleano", "1"))) == (None, "nao_numerico")
    assert money(Cell(formula="SUM(A1)", cache=None)) == (None, "formula_sem_resultado")
    assert money(Cell(formula="X", cache=("erro", "#REF!"))) == (None, "erro_de_formula")
    for bad in ("NaN", "Infinity", "-inf", "1,5", ""):
        assert money(Cell(literal=("numero", bad)))[1] == "numero_invalido"
    date_cell = Cell(literal=("numero", "46300"))
    date_cell.date_format = True
    assert money(date_cell) == (None, "formato_de_data")
    assert canonical(Decimal("150.2500")) == "150.25"
    assert canonical(Decimal("1E+2")) == "100"
    assert canonical(Decimal("-0.0")) == "0"
    assert canonical(Decimal("0.30000000000000004")) == "0.30000000000000004"  # sem arredondar


# -- leitura por âncora --------------------------------------------------------------------------


def test_standard_day_reads_published_cells() -> None:
    r = _read(day("0510"))
    d = r.blocks["dinheiro"]
    assert d["caixa_inicial"]["valor"] == "100" and d["registros"] == 3
    # totais publicados (cache das fórmulas), saída positiva na própria coluna
    assert d["total_entradas"]["valor"] == "150.25" and d["total_saidas"]["valor"] == "30"
    assert d["retirada_malote"]["valor"] == "20" and d["saldo_teorico"]["valor"] == "200.25"
    assert d["saldo_conferido"]["valor"] == "200.25" and d["diferenca"]["valor"] == "0"
    assert r.conferencia == {"estado": "valida", "motivo": None, "sinal": "zero"}
    assert r.blocks["pix"]["total"]["valor"] == "100"
    p = r.blocks["protesto"]
    assert (
        p["registros"],
        p["total_recebido"]["valor"],
        p["total_repassado"]["valor"],
        p["total_emolumentos"]["valor"],
    ) == (1, "500", "450", "50")
    m = r.blocks["maquininha"]
    assert (m["total_a_receber"]["valor"], m["total_cobrado"]["valor"]) == ("97.5", "100")
    assert r.blocks["verificacao"] == {
        "localizado": True,
        "motivo": None,
        "preenchidas": 1,
        "incompletas": 0,
    }
    assert all(s["estado"] == "confere" for s in r.sums.values())
    assert r.movement and r.body_date == date(2026, 10, 5)


def test_published_total_is_never_replaced_by_a_sum() -> None:
    r = _read(day("0510", totais=(F("SUM(C7:C21)", "999"), F("SUM(D7:D21)", "30"))))
    assert r.blocks["dinheiro"]["total_entradas"]["valor"] == "999"
    assert r.sums["dinheiro_entradas"]["estado"] == "diverge"
    assert r.sums["dinheiro_saidas"]["estado"] == "confere"


def test_inserted_rows_shift_blocks_and_are_followed_by_anchor() -> None:
    sh = day("0510", pix_extra=4)
    r = _read(sh)
    assert r.blocks["maquininha"]["total_a_receber"]["valor"] == "97.5"
    assert r.blocks["pix"]["total"]["valor"] == "100"
    assert r.blocks["protesto"]["total_recebido"]["valor"] == "500"


def test_merged_label_moves_the_value_cell_and_value_inside_merge_is_refused() -> None:
    # rótulo mesclado B4:C4 → valor em D4
    sh = day(
        "0510", set_cells={(4, 4): N("77")}, drop={(4, 3)}, merges=["B4:C4", "C23:D23", "C24:D24"]
    )
    assert _read(sh).blocks["dinheiro"]["caixa_inicial"]["valor"] == "77"
    # valor cairia no meio de uma mescla (C3:C5 começa acima) → layout inválido, nada inventado
    bad = day("0510", merges=["C3:C5"])
    blk = _read(bad).blocks["dinheiro"]
    assert blk["localizado"] is False and blk["motivo"] == "layout_invalido"
    assert blk["caixa_inicial"] == {"valor": None, "motivo": "bloco_indisponivel"}


def test_missing_or_duplicated_anchor_never_picks_first_occurrence() -> None:
    dup = _read(day("0510", set_cells={(25, 2): "Retirada para malote", (25, 3): N("5")}))
    assert dup.blocks["dinheiro"]["motivo"] == "ancora_repetida"
    assert dup.blocks["dinheiro"]["retirada_malote"]["valor"] is None
    gone = _read(day("0510", drop={(28, 2)}))
    assert gone.blocks["dinheiro"]["motivo"] == "ancora_ausente"
    two_pix_totals = _read(day("0510", set_cells={(36, 2): "Total"}))
    assert two_pix_totals.blocks["pix"]["motivo"] == "ancora_repetida"


def test_formula_without_cache_and_error_are_unavailable_not_zero() -> None:
    r = _read(day("0510", teorico=F("(C4+C22-D22-C23)"), diferenca=F("C26-C24", error="#REF!")))
    d = r.blocks["dinheiro"]
    assert d["saldo_teorico"] == {"valor": None, "motivo": "formula_sem_resultado"}
    assert r.conferencia["estado"] == "indisponivel" and d["diferenca"]["valor"] is None


def test_zero_is_valid_zero() -> None:
    r = _read(
        day("0510", malote=N("0"), conferido=N("0"), teorico=F("x", "0"), diferenca=F("y", "0"))
    )
    d = r.blocks["dinheiro"]
    assert d["retirada_malote"]["valor"] == "0" and d["saldo_conferido"]["valor"] == "0"
    assert r.conferencia["estado"] == "valida" and d["diferenca"]["valor"] == "0"


def test_empty_count_with_difference_formula_is_sem_conferencia() -> None:
    r = _read(day("0510", conferido=None, diferenca=F("C26-C24", "-200.25")))
    assert r.conferencia["estado"] == "sem_conferencia"
    assert r.blocks["dinheiro"]["diferenca"] == {"valor": None, "motivo": "sem_conferencia"}


def test_movement_only_in_pix_protest_or_card_counts_as_preenchido(tmp_path: Path) -> None:
    empty_cash = dict(lanc=[], totais=(F("SUM(C7:C21)", "0"), F("SUM(D7:D21)", "0")), malote=N("0"))
    no_pix = dict(pix=[], pix_total=F("SUM(C33:C39)", "0"))
    no_prot = dict(protesto=[], protesto_totais=(F("a", "0"), F("b", "0"), F("c", "0")))
    no_maq = dict(maq=[], maq_totais=(F("a", "0"), F("b", "0")))
    sheets = [
        day("0110", **empty_cash, **no_prot, **no_maq),  # só PIX
        day("0210", **empty_cash, **no_pix, **no_maq),  # só protesto
        day("0510", **empty_cash, **no_pix, **no_prot),  # só cartão
        day("0610", **empty_cash, **no_pix, **no_prot, **no_maq),  # nada
    ]
    rep = _run(tmp_path, sheets)
    assert [t["estado"] for t in rep["abas"]] == ["preenchido"] * 3 + ["sem_lancamento"]


# -- somas diagnósticas ---------------------------------------------------------------------------


def test_incomplete_parcel_subtotal_and_divergent_perimeter_make_sum_unavailable() -> None:
    bad_parcel = _read(day("0510", lanc=[(DESCRIPTIONS[0], "R$ 50", None)]))
    assert bad_parcel.sums["dinheiro_entradas"] == {
        "estado": "indisponivel",
        "motivo": "parcela_invalida",
    }
    subtotal = _read(
        day("0510", lanc=[(DESCRIPTIONS[0], N("50"), None), ("Subtotal", N("50"), None)])
    )
    assert subtotal.sums["dinheiro_entradas"]["motivo"] == "subtotal_no_perimetro"
    # Fora do PIX (perímetro não aprovado), fórmula que omite linha preenchida segue bloqueando.
    sh = day("0510", maq=[("Cartao ficticio", N("97.5"), N("100"))])
    mh = sh["maq_header"]
    sh["cells"][(mh + 6, 3)] = F(f"SUM(C{mh + 2}:C{mh + 5})", "97.5")
    assert _read(sh).sums["maquininha_a_receber"]["motivo"] == "perimetro_divergente"
    formula_parcel = _read(day("0510", lanc=[(DESCRIPTIONS[0], F("10+5", "15"), None)]))
    assert formula_parcel.sums["dinheiro_entradas"]["motivo"] == "parcela_por_formula"


def test_totals_row_with_description_is_not_associated() -> None:
    r = _read(day("0510", set_cells={(22, 2): DESCRIPTIONS[0]}))
    d = r.blocks["dinheiro"]
    assert d["total_entradas"] == {"valor": None, "motivo": "total_nao_confirmado"}
    assert r.sums["dinheiro_entradas"]["estado"] == "indisponivel"


# -- datas, estados, temporalidade -------------------------------------------------------


def test_tab_name_rules() -> None:
    assert parse_tab_name("0510", 2026, 10) == (date(2026, 10, 5), None, None)
    assert parse_tab_name("1210 - Feriado", 2026, 10) == (date(2026, 10, 12), "feriado", None)
    assert parse_tab_name("1210-FERIADO", 2026, 10)[1] == "feriado"
    assert parse_tab_name("1210 - Ponto facultativo", 2026, 10)[2] == "sufixo_nao_aprovado"
    assert parse_tab_name("3009-Feriado", 2026, 10) == (None, None, "fora_do_periodo")
    assert parse_tab_name("3210", 2026, 10) == (None, None, "data_invalida")
    assert parse_tab_name("Resumo", 2026, 10) == (None, None, "nome_sem_data")
    assert parse_tab_name("05102", 2026, 10)[2] == "nome_sem_data"


def test_states_temporality_and_checks(tmp_path: Path) -> None:
    sheets = [
        day("3009-Feriado"),  # fora do período → ignorada (reavaliada se o nome mudar)
        day("0510"),
        day("0610", caixa_inicial=N("200.25")),  # continuidade confere com 05/10
        day("0710", caixa_inicial=N("1")),  # diverge
        day("1210 - Feriado", body=date(2026, 10, 7)),  # feriado com valores preservados
        day("1310 - Sem expediente"),  # sufixo não aprovado
        day("1410"),
        day("1410"),  # data repetida
        day("2210", conferido=None),  # na referência
        day("2310"),  # futura
    ]
    rep = _run(tmp_path, sheets)
    states = [(t["estado"], t["motivo_estado"]) for t in rep["abas"]]
    assert states == [
        ("ignorada", "fora_do_periodo"),
        ("preenchido", None),
        ("preenchido", None),
        ("preenchido", None),
        ("feriado", None),
        ("fora_do_padrao", "sufixo_nao_aprovado"),
        ("fora_do_padrao", "data_repetida"),
        ("fora_do_padrao", "data_repetida"),
        ("preenchido", None),
        ("preenchido", None),
    ]
    assert [t["temporalidade"] for t in rep["abas"]][-2:] == ["referencia", "futura"]
    cont = [t["checagens"]["continuidade"] for t in rep["abas"]]
    assert cont[1]["estado"] == "indisponivel" and cont[1]["motivo"] == "sem_base"
    assert (cont[2]["estado"], cont[2]["base_data"], cont[2]["dias_desde_base"]) == (
        "confere",
        "2026-10-05",
        1,
    )
    assert cont[3]["estado"] == "diverge"
    assert cont[4]["base_data"] == "2026-10-07"  # feriado comparado com a data anterior
    assert cont[8]["motivo"] == "base_ambigua"  # 14/10 repetida: sem fusão, sem escolha
    assert cont[9] == {
        "estado": "nao_aplicavel",
        "motivo": "data_futura",
        "base_data": None,
        "dias_desde_base": None,
    }
    feriado = _tab(rep, 5)
    assert feriado["blocos"]["dinheiro"]["total_entradas"]["valor"] == "150.25"
    assert feriado["checagens"]["data_corpo"]["estado"] == "diverge"  # corpo 07/10, nome 12/10
    assert _tab(rep, 2)["checagens"]["data_corpo"]["estado"] == "concorda"
    assert (
        _tab(rep, 3)["checagens"]["data_corpo"]["estado"] == "diverge"
    )  # corpo congelado em 05/10
    assert _tab(rep, 9)["checagens"]["conferencia"]["estado"] == "sem_conferencia"
    assert _tab(rep, 1)["blocos"] is None
    cov = rep["cobertura"]
    assert cov["por_estado"] == {
        "preenchido": 5,
        "sem_lancamento": 0,
        "feriado": 1,
        "fora_do_padrao": 3,
        "ignorada": 1,
    }
    assert cov["por_temporalidade"] == {"anterior": 7, "referencia": 1, "futura": 1, "sem_data": 1}
    assert cov["datas_repetidas"] == 1


def test_body_date_is_only_compared(tmp_path: Path) -> None:
    rep = _run(tmp_path, [day("0510", body=date(2026, 10, 1)), day("0610", body=None)])
    assert _tab(rep, 1)["data"] == "2026-10-05"
    assert _tab(rep, 1)["checagens"]["data_corpo"]["estado"] == "diverge"
    assert _tab(rep, 2)["checagens"]["data_corpo"]["estado"] == "indisponivel"


def test_continuity_does_not_jump_over_unreadable_base(tmp_path: Path) -> None:
    sheets = [day("0510"), day("0610", drop={(28, 2)}), day("0710", caixa_inicial=N("200.25"))]
    rep = _run(tmp_path, sheets)
    assert _tab(rep, 2)["estado"] == "fora_do_padrao"
    assert _tab(rep, 3)["checagens"]["continuidade"]["motivo"] == "base_fora_do_padrao"


# -- relatório, publicação e falhas ------------------------------------------------------


def test_report_is_closed_and_reconciled(tmp_path: Path) -> None:
    rep = _run(tmp_path, [day("0510"), day("0610")])
    validate_report(rep)
    for mutate in (
        lambda r: r.__setitem__("extra", 1),
        lambda r: r["abas"][0]["blocos"]["dinheiro"]["caixa_inicial"].__setitem__("valor", "1.50"),
        lambda r: r["abas"][0]["blocos"]["dinheiro"]["caixa_inicial"].__setitem__("valor", 1.5),
        lambda r: r["abas"][0]["blocos"]["dinheiro"]["caixa_inicial"].__setitem__("valor", True),
        lambda r: r["cobertura"]["por_estado"].__setitem__("preenchido", 9),
        lambda r: r["abas"][0].__setitem__("estado", "sem_lancamento"),
        lambda r: r["abas"][0]["blocos"]["pix"].__setitem__("descricao", PEOPLE[0]),
    ):
        bad = json.loads(json.dumps(rep))
        mutate(bad)
        with pytest.raises(ReportRejected):
            validate_report(bad)


def test_publication_and_shareable_summary(tmp_path: Path) -> None:
    rep = _run(tmp_path, [day("0510"), day("1210 - Feriado")])
    out = tmp_path / "finance_snapshot"
    assert json.loads((out / LATEST).read_text(encoding="utf-8")) == rep
    assert (
        (out / LATEST_MD)
        .read_text(encoding="utf-8")
        .startswith("# Leitura local do Financeiro — PRIVADO")
    )
    summary = render_summary(rep)
    leaks = [
        *PEOPLE,
        PROTOCOL,
        *DESCRIPTIONS,
        "150.25",
        "200.25",
        "97.5",
        "2026-10-05",
        "Feriado",
        FILE_ID,
        "1210",
    ]
    assert not [x for x in leaks if x in summary]
    private = (out / LATEST).read_text(encoding="utf-8") + (out / LATEST_MD).read_text(
        encoding="utf-8"
    )
    assert not [x for x in (*PEOPLE, PROTOCOL, *DESCRIPTIONS, FILE_ID) if x in private]


def test_cli_prints_only_counts_and_codes(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    _capture(tmp_path, xlsx_bytes([day("0510")]))
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "version: 1\n"
        f"credentials_file: {(tmp_path / 'chave.json').as_posix()}\n"
        "expected_identity: leitor@exemplo.iam.gserviceaccount.com\n"
        "data_dir: .\n"
        f"files:\n  - alias: {ALIAS}\n    family: gerenciamento_financeiro\n"
        f"    file_id: {FILE_ID}\n"
        "folders: []\n",
        encoding="utf-8",
    )
    assert cli.main(["analyze", "--config", str(cfg), "--run-id", RUN, "--periodo", "2026-10"]) == 0
    out = capsys.readouterr().out
    assert (
        "preenchido" in out
        and "150.25" not in out
        and FILE_ID not in out
        and str(tmp_path) not in out
    )
    assert cli.main(["analyze", "--config", str(cfg), "--run-id", RUN, "--periodo", "2026-13"]) == 2


@pytest.mark.parametrize(
    "over",
    [
        {"files": (FileSource(ALIAS, "protestos", FILE_ID),)},
        {
            "files": (
                FileSource(ALIAS, "gerenciamento_financeiro", FILE_ID),
                FileSource(
                    "outra_fonte", "gerenciamento_financeiro", "1OutroIdSinteticoBBBBBBBBBB"
                ),
            )
        },
        {
            "folders": (
                FolderSource(
                    "pasta", "gerenciamento_financeiro", "1PastaSinteticaCCCCCCCC", ("x",)
                ),
            )
        },
    ],
)
def test_out_of_scope_config_is_refused_before_reading(tmp_path: Path, over: dict) -> None:
    with pytest.raises(AnalyzeFailed) as exc:
        analyze(_config(tmp_path, **over), RUN, PERIOD)
    assert exc.value.code == "fora_do_recorte_financeiro"
    assert not (tmp_path / "sources").exists()


def test_integrity_and_run_failures_preserve_previous_report(tmp_path: Path) -> None:
    rep = _run(tmp_path, [day("0510")])
    out = tmp_path / "finance_snapshot" / LATEST
    before = out.read_bytes()
    with pytest.raises(AnalyzeFailed) as exc:
        analyze(_config(tmp_path), "20261022T160000Z-ffffff", PERIOD)  # outro run
    assert exc.value.code == "geracao_nao_vinculada"
    state = CaptureStore(tmp_path).read_state(ALIAS)
    content = tmp_path / "sources" / ALIAS / state["current"]["generation"] / "content.xlsx"
    content.write_bytes(content.read_bytes() + b"\0")  # adulteração
    with pytest.raises(AnalyzeFailed) as exc:
        analyze(_config(tmp_path), RUN, PERIOD)
    assert (exc.value.stage, exc.value.code) == ("integridade", "integridade_divergente")
    assert out.read_bytes() == before and rep["origem"]["run_id"] == RUN


def test_publication_failure_keeps_last_valid_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _run(tmp_path, [day("0510")])
    out = tmp_path / "finance_snapshot" / LATEST
    before = out.read_bytes()

    def boom(*_a: object, **_k: object) -> None:
        raise OSError("disco")

    monkeypatch.setattr(pipeline, "atomic_write_bytes", boom)
    with pytest.raises(AnalyzeFailed) as exc:
        analyze(_config(tmp_path), RUN, PERIOD)
    assert (exc.value.stage, exc.value.code) == ("publicacao", "falha_ao_publicar")
    assert out.read_bytes() == before


def test_workbook_without_any_model_tab_is_not_published(tmp_path: Path) -> None:
    _capture(tmp_path, xlsx_bytes([day("Resumo"), day("0510", drop={(4, 2)})]))
    with pytest.raises(AnalyzeFailed) as exc:
        analyze(_config(tmp_path), RUN, PERIOD)
    assert exc.value.code == "nenhuma_aba_no_modelo"
    assert not (tmp_path / "finance_snapshot").exists()


def test_boolean_in_money_cell_is_not_money() -> None:
    r = _read(day("0510", malote=B(True)))
    assert r.blocks["dinheiro"]["retirada_malote"] == {"valor": None, "motivo": "nao_numerico"}


def test_analyze_runs_without_google_and_with_network_blocked(tmp_path: Path) -> None:
    _capture(tmp_path, xlsx_bytes([day("0510")]))
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "version: 1\n"
        f"credentials_file: {(tmp_path / 'chave.json').as_posix()}\n"
        "expected_identity: leitor@exemplo.iam.gserviceaccount.com\n"
        "data_dir: .\n"
        f"files:\n  - alias: {ALIAS}\n    family: gerenciamento_financeiro\n"
        f"    file_id: {FILE_ID}\n",
        encoding="utf-8",
    )
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
        f"rc = cli.main(['analyze', '--config', r'{cfg}', '--run-id', '{RUN}',"
        " '--periodo', '2026-10'])\n"
        "bad = [m for m in sys.modules if m.startswith(('google', 'requests', 'urllib3'))]\n"
        "print('rc', rc, 'bad', bad)\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT, check=True
    )
    assert "rc 0 bad []" in out.stdout


def test_runtime_does_not_depend_on_private_helpers() -> None:
    src = "".join(
        p.read_text(encoding="utf-8") for p in (ROOT / "app/modules/finance_snapshot").glob("*.py")
    )
    for forbidden in (
        "_local_data",
        "discovery_1",
        "calibrate_financeiro",
        "profile_sources",
        "private",
    ):
        assert forbidden not in src


TOTAIS_50_30 = (F("SUM(C7:C21)", "50.25"), F("SUM(D7:D21)", "30"))


def test_hyphen_marker_in_unused_column_allows_the_comparison() -> None:
    # "-" e a sequência só de hífens (como na cópia) valem como vazio na coluna não usada.
    lanc = [(DESCRIPTIONS[0], N("50.25"), "-"), (DESCRIPTIONS[1], " ----------------- ", N("30"))]
    r = _read(day("0510", lanc=lanc, totais=TOTAIS_50_30))
    assert r.sums["dinheiro_entradas"] == {"estado": "confere", "motivo": None}
    assert r.sums["dinheiro_saidas"] == {"estado": "confere", "motivo": None}
    assert r.blocks["dinheiro"]["registros"] == 2  # o marcador não cria nem apaga registro


def test_hyphen_marker_in_scalar_fields_is_absence_not_zero() -> None:
    r = _read(day("0510", caixa_inicial="-", conferido="-", malote="---"))
    d = r.blocks["dinheiro"]
    assert d["caixa_inicial"] == {"valor": None, "motivo": "vazio"}
    assert d["retirada_malote"] == {"valor": None, "motivo": "vazio"}
    assert d["saldo_conferido"] == {"valor": None, "motivo": "vazio"}
    assert r.conferencia["estado"] == "sem_conferencia"  # traço não é contagem
    assert d["diferenca"] == {"valor": None, "motivo": "sem_conferencia"}


def test_hyphen_rule_does_not_extend_to_other_text_or_numbers() -> None:
    for other in ("–", "—", "- -", "x", "-0-", "R$ -"):
        lanc = [(DESCRIPTIONS[0], N("50.25"), other), (DESCRIPTIONS[1], "-", N("30"))]
        r = _read(day("0510", lanc=lanc, totais=TOTAIS_50_30))
        assert r.sums["dinheiro_saidas"]["motivo"] == "parcela_invalida", other
    neg = [(DESCRIPTIONS[0], N("50.25"), "-"), (DESCRIPTIONS[1], "-", N("-30"))]
    r = _read(day("0510", lanc=neg, totais=(F("a", "50.25"), F("b", "-30"))))
    assert r.blocks["dinheiro"]["total_saidas"]["valor"] == "-30"  # sinal preservado
    assert r.sums["dinheiro_saidas"]["estado"] == "confere"
    zero = _read(day("0510", malote=N("0")))
    assert zero.blocks["dinheiro"]["retirada_malote"] == {"valor": "0", "motivo": None}
    formula_dash = _read(day("0510", malote=F("x", None)))
    assert formula_dash.blocks["dinheiro"]["retirada_malote"]["motivo"] == "formula_sem_resultado"


def test_hyphen_only_rows_are_not_movement_and_described_rows_do_not_vanish(
    tmp_path: Path,
) -> None:
    only_marks = [(None, "-", "-")]
    sh = day(
        "0510",
        lanc=only_marks,
        totais=(F("a", "0"), F("b", "0")),
        malote=N("0"),
        pix=[],
        pix_total=F("SUM(C31:C39)", "0"),
        protesto=[],
        protesto_totais=(F("a", "0"), F("b", "0"), F("c", "0")),
        maq=[],
        maq_totais=(F("a", "0"), F("b", "0")),
    )
    sh["cells"].pop((8, 2), None)
    rep = _run(tmp_path, [sh])
    assert _tab(rep, 1)["estado"] == "sem_lancamento"
    described = [(DESCRIPTIONS[0], N("50.25"), "-"), (DESCRIPTIONS[1], "-", "-")]
    r = _read(day("0510", lanc=described, totais=(F("a", "50.25"), F("b", "0"))))
    assert r.sums["dinheiro_entradas"] == {"estado": "indisponivel", "motivo": "parcela_incompleta"}


# -- PIX: perímetro aprovado = bloco inteiro; total publicado preservado -------------------


def test_pix_sum_uses_whole_block_and_keeps_published_total(tmp_path: Path) -> None:
    omitted = [(31, "PIX linha 1", N("7")), (32, "PIX linha 2", N("3")), (33, "PIX", N("100"))]
    r = _read(day("0510", pix=omitted, pix_total=F("SUM(C33:C39)", "100")))
    assert r.blocks["pix"]["total"] == {"valor": "100", "motivo": None}  # célula, sem soma
    assert r.blocks["pix"]["formula_do_total"] == "omite_linhas"
    assert r.sums["pix"] == {"estado": "diverge", "motivo": None}  # 110 ≠ 100
    # Igualdade numérica não apaga a limitação estrutural da fórmula.
    equal = _read(day("0510", pix=[(33, "PIX", N("100"))], pix_total=F("SUM(C33:C39)", "100")))
    assert equal.sums["pix"]["estado"] == "confere"
    assert equal.blocks["pix"]["formula_do_total"] == "omite_linhas"
    bad = _read(day("0510", pix=[(31, "PIX", "R$ 7"), (33, "PIX", N("100"))]))
    assert bad.sums["pix"] == {"estado": "indisponivel", "motivo": "parcela_invalida"}
    full = _read(day("0510", pix=omitted, pix_total=F("SUM(C31:C39)", "110")))
    assert (full.blocks["pix"]["formula_do_total"], full.sums["pix"]["estado"]) == (
        "cobre_o_bloco",
        "confere",
    )
    literal = _read(day("0510", pix=omitted, pix_total=N("110")))
    assert literal.blocks["pix"]["formula_do_total"] == "nao_verificavel"

    rep = _run(tmp_path, [day("0510", pix=omitted, pix_total=F("SUM(C33:C39)", "100"))])
    assert "pix_total_publicado_omite_linhas_do_bloco" in rep["limitacoes"]
    assert rep["cobertura"]["pix_formula_do_total"]["omite_linhas"] == 1
    md = (tmp_path / "finance_snapshot" / LATEST_MD).read_text(encoding="utf-8")
    assert "não um total integral validado" in md and "(fórmula omite linhas)" in md
    summary = render_summary(rep)
    assert "pix_total_publicado_omite_linhas_do_bloco" in summary and "110" not in summary


def test_limitation_absent_when_every_pix_formula_covers_the_block(tmp_path: Path) -> None:
    rep = _run(tmp_path, [day("0510", pix_total=F("SUM(C31:C39)", "100"))])
    assert "pix_total_publicado_omite_linhas_do_bloco" not in rep["limitacoes"]
    bad = json.loads(json.dumps(rep))
    bad["limitacoes"].append("pix_total_publicado_omite_linhas_do_bloco")
    with pytest.raises(ReportRejected):
        validate_report(bad)


# -- Maquininha: "Total em transferências" é o total do cartão ----------------------------


def test_total_em_transferencias_belongs_to_card_block_not_pix() -> None:
    maq = [("Cartao ficticio 1", N("97.5"), N("100")), ("Cartao ficticio 2", N("48"), N("50"))]
    sh = day("0510", maq=maq, maq_totais=(F("a", "145.5"), F("b", "150")))
    # Rótulo igual acima do cabeçalho da maquininha (dentro do PIX) não é o total de nenhum.
    sh["cells"][(35, 2)] = "Total em transferências"
    r = _read(sh)
    m = r.blocks["maquininha"]
    assert (m["total_a_receber"]["valor"], m["total_cobrado"]["valor"]) == ("145.5", "150")
    assert r.blocks["pix"]["total"]["valor"] == "100"
    assert r.sums["maquininha_a_receber"]["estado"] == "confere"
    assert r.sums["maquininha_cobrado"]["estado"] == "confere"


def test_empty_opening_cash_is_not_filled_from_verification_cells() -> None:
    sh = day("0510", verif=[(N("0.4166"), N("200.25"), PEOPLE[0])])
    sh["cells"].pop((4, 3))  # caixa inicial vazio; F4/G4 (verificação) seguem preenchidas
    d = _read(sh).blocks["dinheiro"]
    assert d["caixa_inicial"] == {"valor": None, "motivo": "vazio"}


def test_continuity_base_needs_its_own_opening_cash(tmp_path: Path) -> None:
    empty_holiday = day(
        "1210 - Feriado",
        caixa_inicial=None,
        lanc=[],
        totais=(F("SUM(C7:C21)", "0"), F("SUM(D7:D21)", "0")),
        teorico=F("(C4+C22-D22-C23)", "-20"),
    )
    empty_holiday["cells"].pop((4, 3))
    rep = _run(tmp_path, [day("0910"), empty_holiday, day("1310", caixa_inicial=N("200.25"))])
    cont = _tab(rep, 3)["checagens"]["continuidade"]
    assert (cont["estado"], cont["motivo"], cont["base_data"]) == (
        "indisponivel",
        "base_sem_saldo",
        "2026-10-12",
    )


# -- R1: publicação coerente (JSON autoritativo × Markdown derivado × resposta) -----------


def _published(tmp: Path) -> tuple[bytes | None, bytes | None]:
    out = tmp / "finance_snapshot"
    json_b = (out / LATEST).read_bytes() if (out / LATEST).is_file() else None
    md_b = (out / LATEST_MD).read_bytes() if (out / LATEST_MD).is_file() else None
    return json_b, md_b


def _second_capture(tmp: Path) -> None:
    _run(tmp, [day("0510")])
    _capture(tmp, xlsx_bytes([day("0610")]))  # nova geração, mesmo run sintético


def _cli_args(tmp: Path) -> list[str]:
    cfg = tmp / "config.yaml"
    cfg.write_text(
        "version: 1\n"
        f"credentials_file: {(tmp / 'chave.json').as_posix()}\n"
        "expected_identity: leitor@exemplo.iam.gserviceaccount.com\n"
        "data_dir: .\n"
        f"files:\n  - alias: {ALIAS}\n    family: gerenciamento_financeiro\n"
        f"    file_id: {FILE_ID}\n",
        encoding="utf-8",
    )
    return ["analyze", "--config", str(cfg), "--run-id", RUN, "--periodo", "2026-10"]


def _no_staging_left(tmp: Path) -> bool:
    names = {p.name for p in (tmp / "finance_snapshot").iterdir()}
    return names <= {LATEST, LATEST_MD}


def _boom(*_a: object, **_k: object) -> None:
    raise OSError("disco")


def test_r1_markdown_write_failure_preserves_both_outputs_and_message_is_true(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _second_capture(tmp_path)
    before = _published(tmp_path)
    monkeypatch.setattr(pipeline, "atomic_write_bytes", _boom)
    assert cli.main(_cli_args(tmp_path)) == 2
    err = capsys.readouterr().err
    assert _published(tmp_path) == before  # JSON e Markdown anteriores intactos
    assert "falha_ao_publicar" in err and "foi preservado" in err
    assert _no_staging_left(tmp_path)


def test_r1_markdown_render_failure_preserves_both(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _second_capture(tmp_path)
    before = _published(tmp_path)

    def broken(_rep: dict) -> str:
        raise ValueError("render")

    monkeypatch.setattr(pipeline, "render_markdown", broken)
    with pytest.raises(AnalyzeFailed) as exc:
        analyze(_config(tmp_path), RUN, PERIOD)
    assert (exc.value.stage, exc.value.code) == ("publicacao", "markdown_nao_gerado")
    assert _published(tmp_path) == before


@pytest.mark.parametrize("failing", [LATEST_MD, LATEST])
def test_r1_promotion_failure_preserves_both(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failing: str
) -> None:
    _second_capture(tmp_path)
    before = _published(tmp_path)
    real = pipeline._promote

    def promote(src: Path, dst: Path) -> None:
        if dst.name == failing:
            raise OSError("troca")
        real(src, dst)

    monkeypatch.setattr(pipeline, "_promote", promote)
    with pytest.raises(AnalyzeFailed) as exc:
        analyze(_config(tmp_path), RUN, PERIOD)
    assert exc.value.code == "falha_ao_publicar"
    assert _published(tmp_path) == before  # Markdown restaurado quando o JSON não foi trocado
    assert _no_staging_left(tmp_path)


def test_r1_failed_recovery_is_reported_without_promising_preservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _second_capture(tmp_path)
    old_json, old_md = _published(tmp_path)
    real_promote, real_write = pipeline._promote, pipeline.atomic_write_bytes

    def promote(src: Path, dst: Path) -> None:
        if dst.name == LATEST:
            raise OSError("troca do JSON")
        real_promote(src, dst)

    def write(path: Path, data: bytes) -> None:
        if path.name == LATEST_MD:  # restauração do Markdown anterior
            raise OSError("restauração")
        real_write(path, data)

    monkeypatch.setattr(pipeline, "_promote", promote)
    monkeypatch.setattr(pipeline, "atomic_write_bytes", write)
    assert cli.main(_cli_args(tmp_path)) == 2
    err = capsys.readouterr().err
    new_json, new_md = _published(tmp_path)
    assert new_json == old_json and new_md != old_md  # estado real: só o Markdown mudou
    assert "publicacao_inconsistente" in err and "foi preservado" not in err
    assert "latest.md" in err


def test_r1_first_publication_failure_leaves_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _capture(tmp_path, xlsx_bytes([day("0510")]))
    real = pipeline._promote

    def promote(src: Path, dst: Path) -> None:
        if dst.name == LATEST:
            raise OSError("troca")
        real(src, dst)

    monkeypatch.setattr(pipeline, "_promote", promote)
    with pytest.raises(AnalyzeFailed):
        analyze(_config(tmp_path), RUN, PERIOD)
    assert _published(tmp_path) == (None, None)


def test_r1_success_after_success_publishes_a_coherent_pair(tmp_path: Path) -> None:
    _second_capture(tmp_path)
    later = datetime(2026, 10, 22, 16, tzinfo=UTC)
    rep = analyze(_config(tmp_path), RUN, PERIOD, clock=lambda: later)
    new_json, new_md = _published(tmp_path)
    assert new_json is not None and new_md is not None
    assert json.loads(new_json) == rep and rep["abas"][0]["data"] == "2026-10-06"
    assert rep["gerado_em"] in new_md.decode("utf-8")
    assert _no_staging_left(tmp_path)


# -- R2: linha descrita sem valor utilizável, qualquer que seja a forma da ausência --------

ZERO_CASH: dict = {"totais": (F("a", "0"), F("b", "0")), "malote": N("0")}
NO_PIX: dict = {"pix": [], "pix_total": F("SUM(C31:C39)", "0")}
NO_PROT: dict = {"protesto": [], "protesto_totais": (F("a", "0"), F("b", "0"), F("c", "0"))}
NO_MAQ: dict = {"maq": [], "maq_totais": (F("a", "0"), F("b", "0"))}
ZERO_PROT_TOTALS = (F("a", "0"), F("b", "0"), F("c", "0"))
INCOMPLETE = {"estado": "indisponivel", "motivo": "parcela_incompleta"}
CONFERE = {"estado": "confere", "motivo": None}


def test_r2_cash_described_row_with_absent_values() -> None:
    absent = [(DESCRIPTIONS[0], None, None)]
    r = _read(day("0510", lanc=absent, **ZERO_CASH, **NO_PIX, **NO_PROT, **NO_MAQ))
    assert r.sums["dinheiro_entradas"] == INCOMPLETE and r.sums["dinheiro_saidas"] == INCOMPLETE
    blank = _read(day("0510", lanc=[(DESCRIPTIONS[0], "  ", "")], **ZERO_CASH))
    assert blank.sums["dinheiro_entradas"] == INCOMPLETE
    hyph = _read(day("0510", lanc=[(DESCRIPTIONS[0], "-", "---")], **ZERO_CASH))
    assert hyph.sums["dinheiro_entradas"] == INCOMPLETE
    zero = _read(day("0510", lanc=[(DESCRIPTIONS[0], N("0"), None)], **ZERO_CASH))
    assert zero.sums["dinheiro_entradas"] == CONFERE and zero.sums["dinheiro_saidas"] == CONFERE
    one_side = _read(day("0510"))  # entrada OU saída preenchida é movimentação válida
    assert one_side.sums["dinheiro_saidas"] == CONFERE


def test_r2_rows_without_description_stay_ignored() -> None:
    sh = day("0510", lanc=[("-", "-", None)], **ZERO_CASH)
    sh["cells"][(9, 3)] = "   "  # linha só formatada/em branco, sem descrição
    r = _read(sh)
    assert r.sums["dinheiro_entradas"] == CONFERE and r.blocks["dinheiro"]["registros"] == 0


def test_r2_pix_described_row_with_missing_value_cell() -> None:
    sh = day(
        "0510",
        pix=[(31, "PIX descrito", N("0"))],
        pix_total=F("SUM(C31:C39)", "0"),
        lanc=[],
        **ZERO_CASH,
        **NO_PROT,
        **NO_MAQ,
    )
    sh["cells"].pop((31, 3))  # ausência real da célula (não o texto "None")
    assert _read(sh).sums["pix"] == INCOMPLETE
    unlabeled = day("0510", pix=[(31, "-", N("0"))], pix_total=F("SUM(C31:C39)", "0"))
    unlabeled["cells"].pop((31, 3))
    assert _read(unlabeled).sums["pix"] == CONFERE  # só marcador, sem descrição


def test_r2_card_described_row_with_absent_values() -> None:
    card = [("Cartao descrito", None, None)]
    zero_totals = (F("a", "0"), F("b", "0"))
    r = _read(
        day("0510", maq=card, maq_totais=zero_totals, lanc=[], **ZERO_CASH, **NO_PIX, **NO_PROT)
    )
    assert r.sums["maquininha_a_receber"] == INCOMPLETE
    assert r.sums["maquininha_cobrado"] == INCOMPLETE


def test_r2_protest_template_label_is_not_a_description() -> None:
    tmpl = _read(
        day("0510", protesto=[("Protocolo nº", None, None)], protesto_totais=ZERO_PROT_TOTALS)
    )
    assert tmpl.sums["protesto_recebido"] == CONFERE
    filled = day(
        "0510", protesto=[("Protocolo nº 4521", None, None)], protesto_totais=ZERO_PROT_TOTALS
    )
    assert _read(filled).sums["protesto_recebido"] == INCOMPLETE
    variant = day("0510", protesto=[("Protocolo n°", None, None)], protesto_totais=ZERO_PROT_TOTALS)
    assert _read(variant).sums["protesto_recebido"] == INCOMPLETE  # só o rótulo exato do modelo


def test_r2_specific_treatments_are_kept() -> None:
    no_result = _read(day("0510", lanc=[(DESCRIPTIONS[0], F("x"), None)], **ZERO_CASH))
    assert no_result.sums["dinheiro_entradas"]["motivo"] == "parcela_invalida"
    bad_text = _read(day("0510", lanc=[(DESCRIPTIONS[0], "R$ 5", None)], **ZERO_CASH))
    assert bad_text.sums["dinheiro_entradas"]["motivo"] == "parcela_invalida"
    subtotal = _read(day("0510", lanc=[("Subtotal", None, None)], **ZERO_CASH))
    assert subtotal.sums["dinheiro_entradas"]["motivo"] == "subtotal_no_perimetro"
