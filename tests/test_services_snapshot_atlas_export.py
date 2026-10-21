"""export-atlas: contrato próprio fechado, relação conservadora da tentativa e preservação."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.modules.drive_capture.errors import Code
from app.modules.services_snapshot import atlas_export, cli, pipeline
from app.modules.services_snapshot.atlas_export import (
    EXPORT_FILE,
    ExportFailed,
    export_atlas,
    validate_export,
)
from app.modules.services_snapshot.pipeline import ATTEMPT, LATEST
from app.modules.services_snapshot.report import ReportRejected
from tests.drive_capture_support import IDENTITY, SHEET_1, make_config
from tests.services_snapshot_support import (
    PEOPLE,
    STD,
    as_legacy_v10,
    example_export,
    row,
    xlsx_bytes,
)
from tests.test_services_snapshot_refresh import _out, _refresh, _setup

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "docs" / "modules" / "services_snapshot_atlas.example.json"


def _export(config) -> dict:  # noqa: ANN001
    return export_atlas(config, out=_out(config), latest=LATEST, attempt_name=ATTEMPT)


def _published(config) -> dict:  # noqa: ANN001
    return json.loads((_out(config) / EXPORT_FILE).read_text(encoding="utf-8"))


def _code(config) -> tuple[str, int]:  # noqa: ANN001
    with pytest.raises(ExportFailed) as exc:
        _export(config)
    return exc.value.code, exc.value.exit_code


def test_documented_example_is_the_producer_output() -> None:
    example = example_export()
    validate_export(example)
    assert json.loads(EXAMPLE.read_text(encoding="utf-8")) == example


def test_export_after_refresh_is_closed_partial_and_confirmed(tmp_path: Path) -> None:
    _drive, config, factory = _setup(tmp_path)
    _code_, report, _attempt = _refresh(config, factory)
    before = {n: (_out(config) / n).read_bytes() for n in (LATEST, ATTEMPT)}

    export = _export(config)

    assert export == _published(config)
    validate_export(export)
    assert {n: (_out(config) / n).read_bytes() for n in (LATEST, ATTEMPT)} == before
    assert export["formato"] == "cartorio_system.atlas.services_snapshot"
    assert export["origem"]["versao_local"] == "1.1"
    assert export["cobertura"]["qualidade"] == "parcial"  # status vazio: lacuna, não falha
    assert export["atualizacao"]["relacao"] == "confirmada"
    assert export["atualizacao"]["tentativa"]["mesmo_run"] is True
    assert export["tempos"]["capturada_em"] == report["captura"]["capturada_em"]
    assert export["tempos"]["relatorio_gerado_em"] == report["gerado_em"]
    assert export["tempos"]["referencia_indicadores"] == report["referencia_temporal"]["data"]
    assert export["agregado"]["servicos"]["total"] == report["agregado"]["total"]
    ri = export["setores"][1]
    assert ri["setor"] == "Registro de Imóveis"
    assert ri["datas"]["prenotacao"]["data_prenotacao"] == {
        "estado_campo": "nao_identificado",
        "contagens": None,
        "media_dias_desde": None,
        "mediana_dias_desde": None,
    }
    assert export["setores"][0]["datas"]["prenotacao"] is None


def test_later_failure_and_reexport_keep_the_original_capture(tmp_path: Path) -> None:
    drive, config, factory = _setup(tmp_path)
    _refresh(config, factory)
    first = _export(config)

    drive.fail("export", SHEET_1, Code.PERMISSION_DENIED)
    assert _refresh(config, factory)[0] == 2
    again = _export(config)

    assert again["atualizacao"]["relacao"] == "falhou_depois"
    assert again["atualizacao"]["tentativa"]["codigo"] == "permission_denied"
    assert again["tempos"]["capturada_em"] == first["tempos"]["capturada_em"]
    assert again["origem"]["run_id"] == first["origem"]["run_id"]
    assert again["tempos"]["exportado_em"] >= first["tempos"]["exportado_em"]


def test_absent_or_other_run_attempt_is_never_confirmation(tmp_path: Path) -> None:
    _drive, config, factory = _setup(tmp_path)
    _refresh(config, factory)
    attempt = json.loads((_out(config) / ATTEMPT).read_text(encoding="utf-8"))

    (_out(config) / ATTEMPT).unlink()
    export = _export(config)
    assert export["atualizacao"] == {
        "relacao": "nao_confirmada",
        "observada_em": export["tempos"]["exportado_em"],
        "tentativa": None,
    }

    attempt["run_id"] = "20991231T000000Z-abcdef"
    (_out(config) / ATTEMPT).write_text(json.dumps(attempt), encoding="utf-8")
    export = _export(config)
    assert export["atualizacao"]["relacao"] == "nao_confirmada"
    assert export["atualizacao"]["tentativa"]["mesmo_run"] is False


@pytest.mark.parametrize("target", [LATEST, ATTEMPT])
def test_invalid_input_blocks_export_and_preserves_previous(tmp_path: Path, target: str) -> None:
    _drive, config, factory = _setup(tmp_path)
    _refresh(config, factory)
    _export(config)
    before = (_out(config) / EXPORT_FILE).read_bytes()

    (_out(config) / target).write_text('{"resultado": "sucesso", "x": "' + PEOPLE[0] + '"}')

    assert _code(config) == ("entrada_invalida", 2)
    assert (_out(config) / EXPORT_FILE).read_bytes() == before


def test_legacy_report_and_missing_report_have_fixed_exits(tmp_path: Path) -> None:
    _drive, config, factory = _setup(tmp_path)
    assert _code(config) == ("sem_relatorio", 3)

    _code_, report, _attempt = _refresh(config, factory)
    (_out(config) / LATEST).write_text(json.dumps(as_legacy_v10(report)), encoding="utf-8")
    assert _code(config) == ("relatorio_sem_datas", 5)
    assert not (_out(config) / EXPORT_FILE).exists()


def test_write_failure_preserves_previous_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    drive, config, factory = _setup(tmp_path)
    _refresh(config, factory)
    _export(config)
    before = (_out(config) / EXPORT_FILE).read_bytes()

    def failing(path: Path, payload: dict) -> None:
        raise OSError("disco cheio")

    monkeypatch.setattr(atlas_export, "atomic_write_json", failing)
    drive.touch(SHEET_1)
    _refresh(config, factory)

    assert _code(config) == ("falha_ao_gravar", 2)
    assert (_out(config) / EXPORT_FILE).read_bytes() == before
    assert not list(_out(config).glob("*.tmp"))


def test_source_must_match_the_single_configured_pilot(tmp_path: Path) -> None:
    _drive, config, factory = _setup(tmp_path)
    _refresh(config, factory)
    other = make_config(
        tmp_path,
        files=[{"alias": "outra_fonte", "family": "documentos_em_andamento", "file_id": SHEET_1}],
    )
    assert _code(other) == ("fonte_divergente", 2)

    two = make_config(
        tmp_path,
        files=[
            {"alias": "fonte_a", "family": "protestos", "file_id": SHEET_1},
            {"alias": "fonte_b", "family": "protestos", "file_id": "SHEETsegundafonte0001"},
        ],
    )
    assert _code(two) == ("fora_do_recorte_piloto", 2)


def test_active_refresh_lock_and_unstable_reads_refuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _drive, config, factory = _setup(tmp_path)
    _refresh(config, factory)
    (_out(config) / "run.lock").write_text("{}", encoding="utf-8")
    assert _code(config) == ("refresh_em_andamento", 4)
    (_out(config) / "run.lock").unlink()

    calls = iter(range(100))
    monkeypatch.setattr(atlas_export, "_read_pair", lambda *_a: (str(next(calls)).encode(), None))
    assert _code(config) == ("leitura_instavel", 2)
    assert not (_out(config) / "run.lock").exists()


@pytest.mark.parametrize(
    "mutate",
    [
        lambda e: e.__setitem__("extra", 1),
        lambda e: e["origem"].__setitem__("fonte_alias", "Planilha do " + PEOPLE[1]),
        lambda e: e["setores"][0].__setitem__("setor", PEOPLE[0]),
        lambda e: e["setores"][0]["servicos"].__setitem__("total", "5"),
        lambda e: e["setores"][0]["datas"]["duracao_conclusao"].__setitem__(
            "media_dias", float("inf")
        ),
        lambda e: e["tempos"].__setitem__("capturada_em", "ontem"),
        lambda e: e["atualizacao"].__setitem__("relacao", "sucesso"),
        lambda e: e["agregado"]["servicos"].__setitem__("total", 999),
        lambda e: e.__setitem__("versao", "1.1"),
    ],
)
def test_export_schema_rejects_extra_fields_free_text_and_bad_totals(mutate) -> None:  # noqa: ANN001
    bad = copy.deepcopy(example_export())
    mutate(bad)
    with pytest.raises(ReportRejected) as exc:
        validate_export(bad)
    assert not any(p in str(exc.value) for p in PEOPLE)


def test_export_and_cli_carry_no_personal_or_technical_markers(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:  # noqa: ANN001
    content = xlsx_bytes(
        [
            {
                "name": "Registro de Imóveis",
                "headers": [*STD, "Vencimento da Prenotação", "PRENOTAÇÃO"],
                "rows": [
                    [*row("Talvez " + PEOPLE[0], obs=PEOPLE[2]), "12/03/2026", "778899"],
                    [*row("Concluída", tarefa="Inventário " + PEOPLE[1]), None, "PROT-55"],
                ],
            }
        ]
    )
    _drive, config, factory = _setup(tmp_path, content)
    _refresh(config, factory)
    monkeypatch.setattr(cli, "load_config", lambda _p: config)

    assert cli.main(["export-atlas"]) == 0

    out = capsys.readouterr()
    text = out.out + out.err + (_out(config) / EXPORT_FILE).read_text(encoding="utf-8")
    for marker in [
        *PEOPLE,
        "Talvez",
        "Inventário",
        "12/03/2026",
        "778899",
        "PROT-55",
        "45900",
        SHEET_1,
        IDENTITY,
        str(tmp_path),
        "sha256",
    ]:
        assert marker not in text


def test_cli_legacy_report_prints_fixed_guidance(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:  # noqa: ANN001
    _drive, config, factory = _setup(tmp_path)
    _code_, report, _attempt = _refresh(config, factory)
    (_out(config) / LATEST).write_text(json.dumps(as_legacy_v10(report)), encoding="utf-8")
    monkeypatch.setattr(cli, "load_config", lambda _p: config)

    assert cli.main(["export-atlas"]) == 5
    assert "formato 1.0" in capsys.readouterr().err


def test_export_never_runs_the_collector(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _drive, config, factory = _setup(tmp_path)
    _refresh(config, factory)

    def must_not_run(*_a, **_k):  # noqa: ANN002, ANN003, ANN202
        raise AssertionError("export-atlas tentou coletar")

    monkeypatch.setattr(pipeline, "default_collector", must_not_run)
    monkeypatch.setattr(pipeline, "refresh", must_not_run)
    _export(config)
