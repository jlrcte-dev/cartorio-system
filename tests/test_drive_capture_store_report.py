"""Publicação atômica, retenção limitada, relatório sanitizado e CLI do coletor."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.modules.drive_capture import cli
from app.modules.drive_capture.collector import Collector
from app.modules.drive_capture.config import GOOGLE_DOC, GOOGLE_SHEET
from app.modules.drive_capture.errors import Code, DriveCaptureError
from app.modules.drive_capture.report import CONTRACT_VERSION, build_report, render_markdown
from app.modules.drive_capture.store import Acquisition, CaptureStore
from tests.drive_capture_support import (
    DOC_1,
    FOLDER,
    FOLDER_A,
    FOLDER_RULE,
    IDENTITY,
    SHEET_1,
    FakeDrive,
    make_client,
    make_config,
    xlsx_bytes,
)

SENSITIVE_NAME = "Escritura Cliente Fulano de Tal"
SENSITIVE_CONTENT = "CPF 000.000.000-00 valor R$ 1.234,56"


def _acq(marker: str) -> Acquisition:
    return Acquisition(
        content=xlsx_bytes(marker),
        extension="xlsx",
        method="export_xlsx",
        source_mime=GOOGLE_SHEET,
        exported_mime="x",
        modified_time="2026-10-19T11:00:00.000Z",
        version="1",
        drive_size=None,
        drive_md5=None,
    )


def _publish(store: CaptureStore, marker: str) -> dict:
    return store.publish(
        "fonte_piloto",
        SHEET_1,
        _acq(marker),
        alias="fonte_piloto",
        family="protestos",
        run_id="r",
        captured_at=datetime.now(UTC),
    )


# -- armazenamento -----------------------------------------------------------------------


def test_failed_promotion_leaves_previous_generation_and_no_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = CaptureStore(tmp_path)
    before = _publish(store, "v1")
    real_replace = os.replace

    def failing_replace(src: object, dst: object) -> None:
        if Path(str(src)).name.startswith("staging-"):
            raise OSError("disco cheio")
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", failing_replace)
    with pytest.raises(DriveCaptureError) as excinfo:
        _publish(store, "v2")

    assert excinfo.value.code == Code.STORE_ERROR
    assert store.read_state("fonte_piloto") == before
    assert store.current_content_path("fonte_piloto").read_bytes() == xlsx_bytes("v1")
    assert not list((tmp_path / "sources" / "fonte_piloto").glob("staging-*"))


def test_prune_removes_only_collector_owned_orphans(tmp_path: Path) -> None:
    store = CaptureStore(tmp_path)
    _publish(store, "v1")
    source_dir = tmp_path / "sources" / "fonte_piloto"
    orphan = source_dir / "gen-20260101T000000Z-deadbeef"
    orphan.mkdir()
    foreign = source_dir / "anotacoes-do-operador"
    foreign.mkdir()

    state = _publish(store, "v2")

    assert not orphan.exists()
    assert foreign.exists()
    assert {p.name for p in source_dir.glob("gen-*")} == {
        state["current"]["generation"],
        state["previous"]["generation"],
    }


def test_failure_record_never_renews_last_success(tmp_path: Path) -> None:
    store = CaptureStore(tmp_path)
    before = _publish(store, "v1")

    after = store.record_failure(
        "fonte_piloto", SHEET_1, Code.NOT_FOUND, "r2", datetime(2030, 1, 1, tzinfo=UTC)
    )

    assert after["last_success_at"] == before["last_success_at"]
    assert after["current"] == before["current"]
    assert after["last_attempt"]["code"] == "not_found"
    assert after["eligibility"] == "eligible"


def test_local_keys_reject_path_traversal(tmp_path: Path) -> None:
    store = CaptureStore(tmp_path)
    with pytest.raises(DriveCaptureError):
        store.read_state("../fora")


# -- relatório sanitizado ----------------------------------------------------------------


def _sensitive_run(tmp_path: Path) -> tuple[Collector, dict]:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET, name=SENSITIVE_NAME, content=xlsx_bytes(SENSITIVE_CONTENT))
    drive.add(FOLDER_A, FOLDER, name="Pasta Protestos Fulano")
    drive.add("SHEETdiaria0000000001", GOOGLE_SHEET, parents=(FOLDER_A,), name=SENSITIVE_NAME)
    drive.add(DOC_1, GOOGLE_DOC)
    drive.fail("meta", DOC_1, Code.PERMISSION_DENIED)
    config = make_config(
        tmp_path,
        files=[
            {
                "alias": "financeiro_piloto",
                "family": "gerenciamento_financeiro",
                "file_id": SHEET_1,
            },
            {"alias": "relato_equipe", "family": "relatorios_colaboradores", "file_id": DOC_1},
        ],
        folders=[
            {
                "alias": "protestos_dia",
                "family": "protestos",
                "folder_id": FOLDER_A,
                "include": dict(FOLDER_RULE, name_pattern="escritura *"),
            }
        ],
    )
    collector = Collector(config, make_client(drive, config), CaptureStore(config.data_dir))
    return collector, build_report(collector.run(None), config)


def test_report_contains_no_ids_titles_content_paths_or_hashes(tmp_path: Path) -> None:
    collector, report = _sensitive_run(tmp_path)
    text = json.dumps(report, ensure_ascii=False) + render_markdown(report)

    for forbidden in (
        SHEET_1,
        DOC_1,
        FOLDER_A,
        "SHEETdiaria",
        "Fulano",
        "Escritura",
        "R$",
        "CPF",
        IDENTITY,
        str(tmp_path),
        "docs.google.com",
    ):
        assert forbidden not in text, forbidden
    state = collector.store.read_state("financeiro_piloto")
    assert state["current"]["sha256"] not in text


def test_report_contract_and_family_coverage(tmp_path: Path) -> None:
    _, report = _sensitive_run(tmp_path)

    assert (report["contract"], report["contract_version"]) == (
        "cartorio_system.drive_capture.report",
        CONTRACT_VERSION,
    )
    assert report["run"]["status"] == "partial"
    assert report["run"]["identity_verified"] is True
    families = {f["family"]: f["status"] for f in report["families"]}
    assert families == {
        "gerenciamento_financeiro": "complete",
        "protestos": "complete",
        "documentos_em_andamento": "not_configured",
        "relatorios_colaboradores": "failed",
    }
    failed = next(s for s in report["sources"] if s["alias"] == "relato_equipe")
    assert (failed["result"], failed["code"], failed["last_success_at"]) == (
        "failed",
        "permission_denied",
        None,
    )
    assert "não provam que um serviço avançou" in report["notice"]


# -- CLI ---------------------------------------------------------------------------------


def test_cli_without_config_fails_explicitly(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    code = cli.main(["collect", "--config", str(tmp_path / "ausente.yaml")])

    assert code == 2
    err = capsys.readouterr().err
    assert "config_invalid" in err and "drive_capture.config.example.yaml" in err


def test_cli_without_credential_fails_before_any_network(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "version: 1\ncredentials_file: sa.json\n"
        f"expected_identity: {IDENTITY}\n"
        f"files:\n  - {{alias: financeiro_piloto, family: protestos, file_id: {SHEET_1}}}\n",
        encoding="utf-8",
    )

    code = cli.main(["check", "--config", str(config_path)])

    assert code == 2
    assert "credentials_missing" in capsys.readouterr().err


def test_cli_collect_writes_sanitized_reports(
    tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET, name=SENSITIVE_NAME)
    config = make_config(
        tmp_path,
        files=[
            {"alias": "financeiro_piloto", "family": "gerenciamento_financeiro", "file_id": SHEET_1}
        ],
    )
    monkeypatch.setattr(cli, "load_config", lambda _path: config)
    monkeypatch.setattr(
        cli,
        "_make_collector",
        lambda cfg: (Collector(cfg, make_client(drive, cfg), CaptureStore(cfg.data_dir)), IDENTITY),
    )
    report_path = tmp_path / "exports" / "relatorio.json"

    assert cli.main(["collect", "--report-json", str(report_path)]) == 0
    assert cli.main(["check"]) == 0

    out = capsys.readouterr().out
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["totals"]["captured"] == 1
    assert (config.data_dir / "reports" / "latest.md").is_file()
    for forbidden in (SHEET_1, "Fulano", IDENTITY, IDENTITY.split("@")[1], str(tmp_path)):
        assert forbidden not in out


def test_cli_keeps_http_libraries_quiet_even_with_debug_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = logging.getLogger()
    monkeypatch.setattr(root, "level", root.level)
    monkeypatch.setattr(cli, "setup_logging", lambda: root.setLevel(logging.DEBUG))

    cli.main(["check", "--config", str(tmp_path / "ausente.yaml")])

    for name in ("urllib3", "urllib3.connectionpool", "google.auth.transport.requests"):
        assert not logging.getLogger(name).isEnabledFor(logging.DEBUG), name
        assert not logging.getLogger(name).isEnabledFor(logging.INFO), name
