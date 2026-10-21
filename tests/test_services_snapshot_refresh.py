"""Fluxo refresh/show: composição com o coletor, vínculo da geração, preservação em falha.

O coletor real roda sobre o Drive sintético em memória (FakeDrive); nada de rede.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.modules.drive_capture.collector import Collector
from app.modules.drive_capture.config import GOOGLE_SHEET
from app.modules.drive_capture.errors import Code
from app.modules.drive_capture.store import CaptureStore
from app.modules.services_snapshot import cli, pipeline
from app.modules.services_snapshot.dates import BRT
from app.modules.services_snapshot.pipeline import ATTEMPT, LATEST, RefreshFailed, bind_generation
from tests.drive_capture_support import IDENTITY, SHEET_1, FakeDrive, make_client, make_config
from tests.services_snapshot_support import (
    PEOPLE,
    STD,
    as_legacy_v10,
    row,
    standard_workbook,
    xlsx_bytes,
)

ROOT = Path(__file__).resolve().parents[1]


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 21, 12, tzinfo=UTC)

    def __call__(self) -> datetime:
        self.now += timedelta(minutes=1)
        return self.now


def _setup(tmp_path: Path, content: bytes | None = None) -> tuple:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET, content=content or standard_workbook())
    config = make_config(
        tmp_path,
        files=[
            {
                "alias": "servicos_andamento_piloto",
                "family": "documentos_em_andamento",
                "file_id": SHEET_1,
            }
        ],
    )

    def factory(cfg):  # noqa: ANN001, ANN202
        return Collector(cfg, make_client(drive, cfg), CaptureStore(cfg.data_dir)), IDENTITY

    return drive, config, factory


def _config_yaml() -> str:
    source = "{alias: servicos_andamento_piloto, family: documentos_em_andamento, file_id: %s}"
    return (
        f"version: 1\ncredentials_file: sa.json\nexpected_identity: {IDENTITY}\n"
        f"files:\n  - {source % SHEET_1}\n"
    )


def _out(config) -> Path:  # noqa: ANN001
    return config.data_dir / "services_snapshot"


_CLOCK = Clock()  # compartilhado: tentativas sucessivas têm horários crescentes, como no real


def _refresh(config, factory, clock=None):  # noqa: ANN001, ANN202
    return pipeline.refresh(config, collector_factory=factory, clock=clock or _CLOCK)


def test_first_run_then_show(tmp_path: Path) -> None:
    _drive, config, factory = _setup(tmp_path)
    code, text = pipeline.show(config)
    assert code == 3 and "Nenhum relatório válido" in text

    code, report, attempt = _refresh(config, factory)

    assert code == 0 and attempt["resultado"] == "sucesso"
    assert report["agregado"]["total"] == 5
    assert (
        report["cobertura"]["qualidade"] == "parcial"
    )  # um status vazio: lacuna da fonte, não falha
    assert json.loads((_out(config) / LATEST).read_text(encoding="utf-8")) == report
    code, text = pipeline.show(config)
    assert code == 0 and "Escrituras" in text and report["captura"]["run_id"] in text


@pytest.mark.parametrize(
    ("break_source", "stage", "code"),
    [
        (
            lambda d: d.fail("export", SHEET_1, Code.PERMISSION_DENIED),
            "coleta",
            "permission_denied",
        ),
        (lambda d: d.touch(SHEET_1, b"PK\x03\x04conteudo-corrompido"), "leitura", "xlsx_invalido"),
    ],
)
def test_failure_after_success_preserves_last_report(
    tmp_path: Path, break_source, stage, code
) -> None:  # noqa: ANN001
    drive, config, factory = _setup(tmp_path)
    assert _refresh(config, factory)[0] == 0
    before = (_out(config) / LATEST).read_bytes()

    break_source(drive)
    result, report, attempt = _refresh(config, factory)

    assert (result, report) == (2, None)
    assert (attempt["etapa"], attempt["codigo"]) == (stage, code)
    assert (_out(config) / LATEST).read_bytes() == before  # mesma captura e mesmos timestamps
    shown, text = pipeline.show(config)
    assert shown == 1
    assert "A última atualização falhou" in text and json.loads(before)["captura"]["run_id"] in text


def test_failure_before_atomic_swap_keeps_previous(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    drive, config, factory = _setup(tmp_path)
    assert _refresh(config, factory)[0] == 0
    before = (_out(config) / LATEST).read_bytes()
    real = pipeline.atomic_write_json

    def failing(path: Path, payload: dict) -> None:
        if path.name == LATEST:
            raise OSError("disco cheio")
        real(path, payload)

    monkeypatch.setattr(pipeline, "atomic_write_json", failing)
    drive.touch(SHEET_1)
    code, _, attempt = _refresh(config, factory)

    assert (code, attempt["etapa"], attempt["codigo"]) == (2, "publicacao", "falha_ao_publicar")
    assert (_out(config) / LATEST).read_bytes() == before
    assert not list(_out(config).glob("*.tmp"))


def test_overlapping_refresh_is_refused_without_touching_state(tmp_path: Path) -> None:
    _drive, config, _factory = _setup(tmp_path)
    _out(config).mkdir(parents=True)
    (_out(config) / "run.lock").write_text("{}", encoding="utf-8")

    def must_not_run(cfg):  # noqa: ANN001, ANN202
        raise AssertionError("coletor chamado com refresh sobreposto")

    assert _refresh(config, must_not_run)[0] == 4
    assert not (_out(config) / ATTEMPT).exists()


def test_pilot_scope_is_enforced(tmp_path: Path) -> None:
    config = make_config(
        tmp_path,
        files=[
            {"alias": "fonte_a", "family": "protestos", "file_id": SHEET_1},
            {"alias": "fonte_b", "family": "protestos", "file_id": "SHEETsegundafonte0001"},
        ],
    )

    def must_not_run(cfg):  # noqa: ANN001, ANN202
        raise AssertionError("coletor chamado fora do recorte piloto")

    code, _, attempt = _refresh(config, must_not_run)
    assert (code, attempt["etapa"], attempt["codigo"]) == (
        2,
        "configuracao",
        "fora_do_recorte_piloto",
    )


def test_generation_must_belong_to_this_run_and_match_hashes(tmp_path: Path) -> None:
    _drive, config, factory = _setup(tmp_path)
    collector, identity = factory(config)
    result = collector.run(identity)
    key = result.sources[0].key
    store = collector.store

    content, _, manifest = bind_generation(store, key, result.run_id, SHEET_1)
    assert manifest["run_id"] == result.run_id and content

    with pytest.raises(RefreshFailed) as other_run:
        bind_generation(store, key, "20991231T000000Z-abcdef", SHEET_1)
    assert other_run.value.code == "geracao_nao_vinculada"

    state = store.read_state(key)
    content_path = store.sources_dir / key / state["current"]["generation"] / "content.xlsx"
    content_path.write_bytes(content + b"x")
    with pytest.raises(RefreshFailed) as tampered:
        bind_generation(store, key, result.run_id, SHEET_1)
    assert tampered.value.code == "integridade_divergente"

    content_path.unlink()
    with pytest.raises(RefreshFailed) as missing:
        bind_generation(store, key, result.run_id, SHEET_1)
    assert missing.value.code == "geracao_indisponivel"


def test_no_personal_markers_in_report_attempt_show_or_cli(
    tmp_path: Path, capsys, monkeypatch
) -> None:  # noqa: ANN001
    content = xlsx_bytes(
        [
            {
                "name": "Escrituras",
                "headers": [*STD, "Cliente " + PEOPLE[2]],
                "rows": [
                    [*row("Talvez " + PEOPLE[0], obs=PEOPLE[2]), "nota solta ficticia"],
                    [*row("Concluída"), None],
                ],
            }
        ]
    )
    drive, config, factory = _setup(tmp_path, content)
    monkeypatch.setattr(cli, "load_config", lambda _p: config)
    monkeypatch.setattr(pipeline, "default_collector", factory)
    monkeypatch.setattr(
        cli, "refresh", lambda cfg: pipeline.refresh(cfg, collector_factory=factory)
    )

    assert cli.main(["refresh"]) == 0
    drive.fail("export", SHEET_1, Code.PERMISSION_DENIED)
    assert cli.main(["refresh"]) == 2
    assert cli.main(["show"]) == 1

    captured = capsys.readouterr()
    files = "".join(p.read_text(encoding="utf-8") for p in _out(config).glob("*.json"))
    everything = captured.out + captured.err + files
    for marker in [
        *PEOPLE,
        "Talvez",
        "nota solta ficticia",
        "Alta",
        "Escritura de compra",
        SHEET_1,
        IDENTITY,
        str(tmp_path),
    ]:
        assert marker not in everything


def test_cli_refresh_without_credential_fails_controlled_and_offline(
    tmp_path: Path, capsys
) -> None:  # noqa: ANN001
    cfg = tmp_path / "config.yaml"
    cfg.write_text(_config_yaml(), encoding="utf-8")
    assert cli.main(["refresh", "--config", str(cfg)]) == 2
    attempt = json.loads((tmp_path / "services_snapshot" / ATTEMPT).read_text(encoding="utf-8"))
    assert (attempt["etapa"], attempt["codigo"]) == ("coleta", "credentials_missing")
    assert cli.main(["show", "--config", str(cfg)]) == 3
    assert "credentials_missing" in capsys.readouterr().err


def test_import_and_show_work_without_google_or_defusedxml(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(_config_yaml(), encoding="utf-8")
    code = (
        "import sys\n"
        "class B:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name.split('.')[0] in {'google', 'requests', 'defusedxml', 'urllib3'}:\n"
        "            raise ModuleNotFoundError(name)\n"
        "sys.meta_path.insert(0, B())\n"
        "from app.modules.services_snapshot import cli\n"
        f"rc = cli.main(['show', '--config', r'{cfg}'])\n"
        "bad = [m for m in sys.modules if m.startswith(('google', 'requests', 'defusedxml'))]\n"
        "print('rc', rc, 'bad', bad)\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT, check=True
    )
    assert "rc 3 bad []" in out.stdout


def _fail_attempt_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    real = pipeline.atomic_write_json

    def failing(path: Path, payload: dict) -> None:
        if path.name == ATTEMPT:
            raise OSError("disco cheio")
        real(path, payload)

    monkeypatch.setattr(pipeline, "atomic_write_json", failing)


def test_attempt_not_recorded_after_publication_is_never_shown_as_success_or_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    drive, config, factory = _setup(tmp_path)
    assert _refresh(config, factory)[0] == 0
    first = json.loads((_out(config) / LATEST).read_text(encoding="utf-8"))

    _fail_attempt_writes(monkeypatch)
    drive.touch(SHEET_1)
    code, report, attempt = _refresh(config, factory)

    assert (code, attempt) == (0, None)  # publicado; registro da tentativa não gravado
    latest = json.loads((_out(config) / LATEST).read_text(encoding="utf-8"))
    assert latest == report and latest["captura"]["run_id"] != first["captura"]["run_id"]
    stale = json.loads((_out(config) / ATTEMPT).read_text(encoding="utf-8"))
    assert stale["run_id"] == first["captura"]["run_id"]  # sucesso de OUTRO run

    shown, text = pipeline.show(config)
    assert shown == 1
    assert "Atualização não confirmada" in text
    assert "A última atualização falhou" not in text and "último válido" not in text


def test_missing_or_invalid_attempt_never_fabricates_success(tmp_path: Path) -> None:
    _drive, config, factory = _setup(tmp_path)
    assert _refresh(config, factory)[0] == 0
    assert pipeline.show(config)[0] == 0

    (_out(config) / ATTEMPT).unlink()
    shown, text = pipeline.show(config)
    assert shown == 1 and "Atualização não confirmada" in text

    (_out(config) / ATTEMPT).write_text('{"resultado": "sucesso"}', encoding="utf-8")
    assert pipeline.show(config)[0] == 2


def test_cli_warns_when_attempt_record_fails_after_publication(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:  # noqa: ANN001
    _drive, config, factory = _setup(tmp_path)
    monkeypatch.setattr(cli, "load_config", lambda _p: config)
    monkeypatch.setattr(cli, "refresh", lambda cfg: _refresh(cfg, factory))
    _fail_attempt_writes(monkeypatch)

    assert cli.main(["refresh"]) == 0
    captured = capsys.readouterr()
    assert "registro da tentativa não foi gravado" in captured.err
    assert "Atualização não confirmada" in captured.out


def test_legacy_v10_latest_is_shown_without_date_indicators(tmp_path: Path) -> None:
    _drive, config, factory = _setup(tmp_path)
    _code, report, _attempt = _refresh(config, factory)
    (_out(config) / LATEST).write_text(
        json.dumps(as_legacy_v10(report), ensure_ascii=False), encoding="utf-8"
    )

    shown, text = pipeline.show(config)

    assert shown == 0
    assert "formato 1.0" in text and "Indicadores de datas indisponíveis" in text
    assert "## Datas" not in text and "Idade da carteira" not in text


def test_refresh_writes_v11_with_reference_from_capture(tmp_path: Path) -> None:
    _drive, config, factory = _setup(tmp_path)
    _code, report, _attempt = _refresh(config, factory)
    collector, _ = factory(config)
    key = "servicos_andamento_piloto"
    state = collector.store.read_state(key)
    gdir = collector.store.sources_dir / key / state["current"]["generation"]
    manifest = json.loads((gdir / "manifest.json").read_text(encoding="utf-8"))

    assert report["versao"] == "1.1"
    assert report["referencia_temporal"]["data"] == (
        datetime.fromisoformat(manifest["captured_at"]).astimezone(BRT).date().isoformat()
    )
    assert report["gerado_em"] != report["captura"]["capturada_em"]
    ri = report["abas"][1]
    assert ri["datas"]["campos"]["data_prenotacao"] == "nao_identificado"
    assert ri["datas"]["prenotacao"]["data_prenotacao"] is None
