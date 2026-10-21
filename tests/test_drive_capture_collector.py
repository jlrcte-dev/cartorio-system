"""Coletor somente leitura do Drive: fronteira, captura, consistência e falhas.

Tudo sintético: o Drive é ``FakeDrive`` em memória; nenhuma rede ou credencial.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.modules.drive_capture.collector import Collector
from app.modules.drive_capture.config import CSV, GOOGLE_DOC, GOOGLE_SHEET, XLSX
from app.modules.drive_capture.errors import Code
from app.modules.drive_capture.store import CaptureStore
from tests.drive_capture_support import (
    DOC_1,
    FOLDER,
    FOLDER_A,
    FOLDER_B,
    FOLDER_RULE,
    SHEET_1,
    SHORTCUT,
    SUBFOLDER,
    FakeDrive,
    make_client,
    make_config,
    xlsx_bytes,
)


def _explicit(
    alias: str = "financeiro_diario",
    file_id: str = SHEET_1,
    family: str = "gerenciamento_financeiro",
) -> dict:
    return {"alias": alias, "family": family, "file_id": file_id}


def _folder(alias: str = "protestos_dia", folder_id: str = FOLDER_A, **include: object) -> dict:
    return {
        "alias": alias,
        "family": "protestos",
        "folder_id": folder_id,
        "include": include or dict(FOLDER_RULE),
    }


def _collector(
    tmp_path: Path, drive: FakeDrive, sleeps: list[float] | None = None, **cfg: object
) -> Collector:
    config = make_config(tmp_path, **cfg)
    return Collector(config, make_client(drive, config, sleeps), CaptureStore(config.data_dir))


def _state(collector: Collector, key: str) -> dict:
    state = collector.store.read_state(key)
    assert state is not None
    return state


def _by_alias(result, alias: str):  # noqa: ANN001, ANN202
    matches = [s for s in result.sources if s.alias == alias]
    assert len(matches) == 1, [s.alias for s in result.sources]
    return matches[0]


# -- captura básica ----------------------------------------------------------------------


def test_sheet_is_exported_as_xlsx_with_private_manifest(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET)
    collector = _collector(tmp_path, drive, files=[_explicit()])

    result = collector.run(None)

    outcome = _by_alias(result, "financeiro_diario")
    assert (result.status, outcome.result, outcome.method) == (
        "complete",
        "captured",
        "export_xlsx",
    )
    assert outcome.signals == {
        "version_changed": None,
        "modified_time_changed": None,
        "content_hash_changed": None,
    }
    content_path = collector.store.current_content_path("financeiro_diario")
    assert content_path is not None and content_path.name == "content.xlsx"
    assert content_path.read_bytes() == drive.files[SHEET_1]["content"]
    manifest = json.loads((content_path.parent / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["drive_file_id"] == SHEET_1
    assert manifest["exported_mime"] == XLSX
    assert manifest["acquisition_method"] == "export_xlsx"
    assert manifest["drive_version"] == "1"
    assert len(manifest["sha256"]) == 64
    assert manifest["bytes"] == len(drive.files[SHEET_1]["content"])


def test_google_doc_is_exported_as_docx(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(DOC_1, GOOGLE_DOC)
    collector = _collector(
        tmp_path, drive, files=[_explicit("relato_equipe", DOC_1, "relatorios_colaboradores")]
    )

    outcome = _by_alias(collector.run(None), "relato_equipe")

    assert (outcome.result, outcome.method) == ("captured", "export_docx")
    assert collector.store.current_content_path("relato_equipe").suffix == ".docx"


def test_second_collection_without_change_has_no_change_signal(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET)
    collector = _collector(tmp_path, drive, files=[_explicit()])

    first = collector.run(None)
    second = collector.run(None)

    outcome = _by_alias(second, "financeiro_diario")
    assert outcome.result == "captured"
    assert outcome.signals == {
        "version_changed": False,
        "modified_time_changed": False,
        "content_hash_changed": False,
    }
    state = _state(collector, "financeiro_diario")
    assert state["previous"]["generation"] != state["current"]["generation"]
    assert first.run_id != second.run_id


def test_change_between_runs_is_reported_as_technical_signal(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET)
    collector = _collector(tmp_path, drive, files=[_explicit()])
    collector.run(None)

    drive.touch(SHEET_1, xlsx_bytes("nova-versao"))
    outcome = _by_alias(collector.run(None), "financeiro_diario")

    assert outcome.signals == {
        "version_changed": True,
        "modified_time_changed": True,
        "content_hash_changed": True,
    }


def test_only_current_and_previous_generations_are_kept(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET)
    collector = _collector(tmp_path, drive, files=[_explicit()])
    for _ in range(4):
        collector.run(None)

    source_dir = collector.store.sources_dir / "financeiro_diario"
    generations = sorted(p.name for p in source_dir.iterdir() if p.name.startswith("gen-"))
    state = _state(collector, "financeiro_diario")
    assert generations == sorted([state["current"]["generation"], state["previous"]["generation"]])


# -- fronteira ---------------------------------------------------------------------------


def test_only_configured_ids_are_ever_requested(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET)
    drive.add("SHEETnaoautorizada0001", GOOGLE_SHEET)
    collector = _collector(tmp_path, drive, files=[_explicit()])

    collector.run(None)

    assert all("naoautorizada" not in p for p in drive.paths())
    assert all(
        path in {"about", f"files/{SHEET_1}", f"files/{SHEET_1}/export"} for path in drive.paths()
    )


def test_folder_takes_only_direct_children_matching_rule(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(FOLDER_A, FOLDER)
    drive.add("SHEETdiaria0000000001", GOOGLE_SHEET, parents=(FOLDER_A,))
    drive.add(SUBFOLDER, FOLDER, parents=(FOLDER_A,))
    drive.add("SHEETnasubpasta00001", GOOGLE_SHEET, parents=(SUBFOLDER,))
    drive.add("SHORTCUTparaoutra0001", SHORTCUT, parents=(FOLDER_A,))
    drive.add("DOCnapasta000000000001", GOOGLE_DOC, parents=(FOLDER_A,))
    collector = _collector(tmp_path, drive, folders=[_folder()])

    result = collector.run(None)

    folder = result.folders[0]
    assert (folder.listing, folder.children_seen, folder.eligible) == ("complete", 4, 1)
    assert (folder.ignored_subfolders, folder.ignored_shortcuts, folder.ignored_mime) == (1, 1, 1)
    assert [s.alias for s in result.sources] == ["protestos_dia-0001"]
    touched = " ".join(drive.paths())
    assert "SHEETnasubpasta" not in touched
    assert "SHORTCUTparaoutra" not in touched
    assert "DOCnapasta" not in touched
    listing_params = next(p for _, path, p in drive.calls if path == "files")
    assert listing_params["q"] == f"'{FOLDER_A}' in parents and trashed = false"
    assert "corpora" not in listing_params and "driveId" not in listing_params


def test_shared_drive_options_only_when_declared(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(FOLDER_A, FOLDER)
    collector = _collector(
        tmp_path, drive, folders=[_folder()], shared_drive_id="SHAREDdrive00000000001"
    )

    collector.run(None)

    listing_params = next(p for _, path, p in drive.calls if path == "files")
    assert listing_params["corpora"] == "drive"
    assert listing_params["driveId"] == "SHAREDdrive00000000001"
    assert listing_params["includeItemsFromAllDrives"] == "true"


def test_name_pattern_filters_without_persisting_titles(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(FOLDER_A, FOLDER)
    drive.add(
        "SHEETcontrole00000001",
        GOOGLE_SHEET,
        parents=(FOLDER_A,),
        name="Controle 19-10 Cliente Fulano",
    )
    drive.add("SHEETrascunho00000001", GOOGLE_SHEET, parents=(FOLDER_A,), name="Rascunho Beltrano")
    collector = _collector(
        tmp_path,
        drive,
        folders=[_folder(mime_types=[GOOGLE_SHEET], name_pattern="controle *")],
    )

    result = collector.run(None)

    assert result.folders[0].eligible == 1
    assert result.folders[0].not_matching_pattern == 1
    stored = " ".join(
        p.read_text(encoding="utf-8") for p in collector.config.data_dir.rglob("*.json")
    )
    assert "Fulano" not in stored and "Beltrano" not in stored
    assert all("Fulano" not in str(p) for p in collector.config.data_dir.rglob("*"))


def test_listing_is_paginated(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(FOLDER_A, FOLDER)
    for i in range(5):
        drive.add(f"SHEETdiaria00000000{i:02d}", GOOGLE_SHEET, parents=(FOLDER_A,))
    collector = _collector(tmp_path, drive, folders=[_folder()], limits={"page_size": 2})

    result = collector.run(None)

    assert result.folders[0].listing == "complete"
    assert sum(1 for s in result.sources if s.result == "captured") == 5
    tokens = [p.get("pageToken") for _, path, p in drive.calls if path == "files"]
    assert tokens == [None, "2", "4"]


def test_page_limit_makes_coverage_partial_never_complete(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(FOLDER_A, FOLDER)
    for i in range(5):
        drive.add(f"SHEETdiaria00000000{i:02d}", GOOGLE_SHEET, parents=(FOLDER_A,))
    collector = _collector(
        tmp_path, drive, folders=[_folder()], limits={"page_size": 2, "max_listing_pages": 1}
    )

    result = collector.run(None)

    assert (result.folders[0].listing, result.folders[0].code) == ("partial", "listing_page_limit")
    assert result.status == "partial"


def test_new_daily_file_enters_on_next_run_and_rename_keeps_identity(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(FOLDER_A, FOLDER)
    drive.add("SHEETdiaria0000000001", GOOGLE_SHEET, parents=(FOLDER_A,), name="Dia 18")
    collector = _collector(tmp_path, drive, folders=[_folder()])
    collector.run(None)

    drive.files["SHEETdiaria0000000001"]["name"] = "Dia 18 (renomeado)"
    drive.add("SHEETdiaria0000000002", GOOGLE_SHEET, parents=(FOLDER_A,), name="Dia 19")
    result = collector.run(None)

    assert sorted(s.alias for s in result.sources) == ["protestos_dia-0001", "protestos_dia-0002"]
    assert all(s.result == "captured" for s in result.sources)


def test_explicit_id_inside_authorized_folder_is_deduplicated(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(FOLDER_A, FOLDER)
    drive.add(SHEET_1, GOOGLE_SHEET, parents=(FOLDER_A,))
    collector = _collector(
        tmp_path, drive, files=[_explicit(family="protestos")], folders=[_folder()]
    )

    result = collector.run(None)

    assert [s.alias for s in result.sources] == ["financeiro_diario"]
    assert result.folders[0].already_covered == 1
    assert drive.content_calls() == [f"files/{SHEET_1}/export"]


def test_file_moved_out_of_folder_is_suspended_without_reading_it(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(FOLDER_A, FOLDER)
    drive.add("SHEETdiaria0000000001", GOOGLE_SHEET, parents=(FOLDER_A,))
    collector = _collector(tmp_path, drive, folders=[_folder()])
    collector.run(None)
    before = _state(collector, "protestos_dia-0001")

    drive.files["SHEETdiaria0000000001"]["parents"] = ["FOLDERforadorecorte01"]
    drive.calls.clear()
    result = collector.run(None)

    outcome = _by_alias(result, "protestos_dia-0001")
    assert (outcome.result, outcome.code) == ("failed", Code.OUT_OF_BOUNDARY)
    assert result.folders[0].departed == 1
    assert not any("SHEETdiaria" in p for p in drive.paths())
    after = _state(collector, "protestos_dia-0001")
    assert after["eligibility"] == "suspended"
    assert after["current"] == before["current"]
    assert after["last_success_at"] == before["last_success_at"]


def test_file_moved_between_authorized_folders_stays_in_boundary(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(FOLDER_A, FOLDER)
    drive.add(FOLDER_B, FOLDER)
    drive.add("SHEETdiaria0000000001", GOOGLE_SHEET, parents=(FOLDER_A,))
    collector = _collector(
        tmp_path, drive, folders=[_folder(), _folder("protestos_arquivo", FOLDER_B)]
    )
    collector.run(None)

    drive.files["SHEETdiaria0000000001"]["parents"] = [FOLDER_B]
    result = collector.run(None)

    assert [(s.alias, s.result) for s in result.sources] == [("protestos_dia-0001", "captured")]
    assert all(f.departed == 0 for f in result.folders)


def test_file_moved_during_capture_is_not_promoted(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(FOLDER_A, FOLDER)
    drive.add("SHEETdiaria0000000001", GOOGLE_SHEET, parents=(FOLDER_A,))
    collector = _collector(tmp_path, drive, folders=[_folder()])

    def move() -> None:
        drive.files["SHEETdiaria0000000001"]["parents"] = ["FOLDERforadorecorte01"]

    drive.after_content["SHEETdiaria0000000001"] = move
    result = collector.run(None)

    assert _by_alias(result, "protestos_dia-0001").code == Code.OUT_OF_BOUNDARY
    assert collector.store.current_content_path("protestos_dia-0001") is None


def test_shortcut_id_is_not_followed(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, SHORTCUT)
    collector = _collector(tmp_path, drive, files=[_explicit()])

    outcome = _by_alias(collector.run(None), "financeiro_diario")

    assert outcome.code == Code.SHORTCUT_NOT_FOLLOWED
    assert drive.content_calls() == []


def test_explicit_id_that_is_a_folder_is_refused(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, FOLDER)
    collector = _collector(tmp_path, drive, files=[_explicit()])

    assert _by_alias(collector.run(None), "financeiro_diario").code == Code.IS_FOLDER


def test_empty_authorized_folder_is_valid_and_distinct_from_failure(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(FOLDER_A, FOLDER)
    collector = _collector(tmp_path, drive, folders=[_folder()])

    result = collector.run(None)

    assert result.status == "complete"
    assert (result.folders[0].listing, result.folders[0].eligible) == ("complete", 0)


def test_folder_listing_denied_is_failure_not_empty(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(FOLDER_A, FOLDER)
    drive.fail("list", FOLDER_A, Code.PERMISSION_DENIED)
    collector = _collector(tmp_path, drive, folders=[_folder()])

    result = collector.run(None)

    assert (result.folders[0].listing, result.folders[0].code) == ("failed", Code.PERMISSION_DENIED)
    assert result.status == "partial"


# -- tipos e limites ---------------------------------------------------------------------


def test_stored_file_requires_explicit_acceptance(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, CSV, content=b"a;b\n1;2\n", stored=True)
    refused = _collector(tmp_path / "x", drive, files=[_explicit()])
    assert _by_alias(refused.run(None), "financeiro_diario").code == Code.UNSUPPORTED_MIME
    assert drive.content_calls() == []

    accepted = _collector(
        tmp_path / "y", drive, files=[_explicit()], accepted_stored_mime_types=[CSV]
    )
    outcome = _by_alias(accepted.run(None), "financeiro_diario")
    assert (outcome.result, outcome.method) == ("captured", "download")
    assert accepted.store.current_content_path("financeiro_diario").suffix == ".csv"


def test_stored_download_checks_drive_md5(tmp_path: Path) -> None:
    drive = FakeDrive()
    entry = drive.add(SHEET_1, CSV, content=b"a;b\n", stored=True)
    collector = _collector(tmp_path, drive, files=[_explicit()], accepted_stored_mime_types=[CSV])
    original_meta = drive._meta

    def corrupted_meta(e: dict, fields: str) -> dict:
        meta = original_meta(e, fields)
        if e is entry:
            meta["md5Checksum"] = "0" * 32
        return meta

    drive._meta = corrupted_meta  # type: ignore[method-assign]
    outcome = _by_alias(collector.run(None), "financeiro_diario")

    assert outcome.code == Code.INTEGRITY_MISMATCH
    assert collector.store.current_content_path("financeiro_diario") is None


def test_size_limit_refuses_without_truncating(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET, content=xlsx_bytes("x" * 2000))
    collector = _collector(tmp_path, drive, files=[_explicit()], limits={"max_file_bytes": 1000})

    outcome = _by_alias(collector.run(None), "financeiro_diario")

    assert outcome.code == Code.SIZE_LIMIT
    assert collector.store.current_content_path("financeiro_diario") is None


def test_stored_file_over_limit_is_refused_before_download(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, CSV, content=b"x" * 2000, stored=True)
    collector = _collector(
        tmp_path,
        drive,
        files=[_explicit()],
        accepted_stored_mime_types=[CSV],
        limits={"max_file_bytes": 1000},
    )

    assert _by_alias(collector.run(None), "financeiro_diario").code == Code.SIZE_LIMIT
    assert drive.content_calls() == []


def test_run_byte_budget_and_source_cap_give_partial_coverage(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(FOLDER_A, FOLDER)
    for i in range(4):
        drive.add(
            f"SHEETdiaria00000000{i:02d}",
            GOOGLE_SHEET,
            parents=(FOLDER_A,),
            content=xlsx_bytes("y" * 96),
        )
    collector = _collector(
        tmp_path, drive, folders=[_folder()], limits={"max_sources": 3, "max_run_bytes": 150}
    )

    result = collector.run(None)

    codes = [s.code for s in result.sources]
    assert codes.count(None) == 1
    assert Code.RUN_BUDGET_EXHAUSTED in codes
    assert codes[-1] == Code.SOURCE_CAP
    assert result.status == "partial"


def test_download_restricted_is_not_bypassed(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET, can_download=False)
    collector = _collector(tmp_path, drive, files=[_explicit()])

    assert _by_alias(collector.run(None), "financeiro_diario").code == Code.DOWNLOAD_RESTRICTED
    assert drive.content_calls() == []


def test_export_that_is_not_a_spreadsheet_package_is_rejected(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET, content=b"<html>erro</html>")
    collector = _collector(tmp_path, drive, files=[_explicit()])

    assert _by_alias(collector.run(None), "financeiro_diario").code == Code.UNEXPECTED_RESPONSE


def test_trashed_explicit_source_is_suspended(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET, trashed=True)
    collector = _collector(tmp_path, drive, files=[_explicit()])

    assert _by_alias(collector.run(None), "financeiro_diario").code == Code.TRASHED
    assert _state(collector, "financeiro_diario")["eligibility"] == "suspended"


# -- consistência ------------------------------------------------------------------------


def test_change_during_capture_gets_one_consistency_retry(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET)
    drive.after_content[SHEET_1] = lambda: drive.touch(SHEET_1, xlsx_bytes("editada"))
    collector = _collector(tmp_path, drive, files=[_explicit()])

    outcome = _by_alias(collector.run(None), "financeiro_diario")

    assert (outcome.result, outcome.consistency_retry) == ("captured", True)
    assert outcome.drive_version == "2"
    assert collector.store.current_content_path("financeiro_diario").read_bytes() == xlsx_bytes(
        "editada"
    )


def test_source_changing_twice_is_not_promoted_and_previous_survives(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET)
    collector = _collector(tmp_path, drive, files=[_explicit()])
    collector.run(None)
    before = _state(collector, "financeiro_diario")

    drive.after_content[SHEET_1] = lambda: (
        drive.touch(SHEET_1),
        drive.after_content.__setitem__(SHEET_1, lambda: drive.touch(SHEET_1)),
    )
    outcome = _by_alias(collector.run(None), "financeiro_diario")

    assert outcome.code == Code.SOURCE_CHANGED
    after = _state(collector, "financeiro_diario")
    assert after["current"] == before["current"]
    assert after["last_success_at"] == before["last_success_at"]
    assert after["last_attempt"]["code"] == Code.SOURCE_CHANGED


# -- falhas ------------------------------------------------------------------------------


def test_failure_preserves_last_valid_capture_and_success_date(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET)
    collector = _collector(tmp_path, drive, files=[_explicit()])
    collector.run(None)
    before = _state(collector, "financeiro_diario")
    content_before = collector.store.current_content_path("financeiro_diario").read_bytes()

    drive.fail("export", SHEET_1, Code.PERMISSION_DENIED)
    outcome = _by_alias(collector.run(None), "financeiro_diario")

    after = _state(collector, "financeiro_diario")
    assert outcome.code == Code.PERMISSION_DENIED
    assert outcome.last_success_at == before["last_success_at"]
    assert after["current"] == before["current"]
    assert after["last_attempt"]["result"] == "failed"
    assert collector.store.current_content_path("financeiro_diario").read_bytes() == content_before


def test_one_source_failing_does_not_stop_the_others(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(DOC_1, GOOGLE_DOC)
    collector = _collector(
        tmp_path,
        drive,
        files=[_explicit(), _explicit("relato_equipe", DOC_1, "relatorios_colaboradores")],
    )

    result = collector.run(None)

    assert _by_alias(result, "financeiro_diario").code == Code.NOT_FOUND
    assert _by_alias(result, "relato_equipe").result == "captured"
    assert result.status == "partial"


def test_unexpected_exception_is_isolated_per_source(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET)
    drive.add(DOC_1, GOOGLE_DOC)
    drive.after_content[SHEET_1] = lambda: (_ for _ in ()).throw(RuntimeError("detalhe remoto"))
    collector = _collector(
        tmp_path,
        drive,
        files=[_explicit(), _explicit("relato_equipe", DOC_1, "relatorios_colaboradores")],
    )

    result = collector.run(None)

    assert _by_alias(result, "financeiro_diario").code == Code.UNEXPECTED_ERROR
    assert _by_alias(result, "relato_equipe").result == "captured"


def test_retryable_errors_are_retried_a_bounded_number_of_times(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET)
    drive.fail("export", SHEET_1, Code.RATE_LIMITED, Code.SERVER_ERROR)
    sleeps: list[float] = []
    collector = _collector(tmp_path, drive, sleeps, files=[_explicit()])

    assert _by_alias(collector.run(None), "financeiro_diario").result == "captured"
    assert sleeps == [2.0, 4.0]

    drive.fail("export", SHEET_1, Code.TIMEOUT, Code.TIMEOUT, Code.TIMEOUT)
    assert _by_alias(collector.run(None), "financeiro_diario").code == Code.TIMEOUT


def test_non_retryable_error_is_not_retried(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET)
    drive.fail("export", SHEET_1, Code.EXPORT_SIZE_LIMIT)
    sleeps: list[float] = []
    collector = _collector(tmp_path, drive, sleeps, files=[_explicit()])

    assert _by_alias(collector.run(None), "financeiro_diario").code == Code.EXPORT_SIZE_LIMIT
    assert sleeps == []


@pytest.mark.parametrize(
    "credential_identity", [None, "outra-identidade@projeto.iam.gserviceaccount.com"]
)
def test_identity_mismatch_aborts_before_any_file_access(
    tmp_path: Path, credential_identity: str | None
) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET)
    if credential_identity is None:
        drive.identity = "conta-pessoal@exemplo.com"
    collector = _collector(tmp_path, drive, files=[_explicit()])

    result = collector.run(credential_identity)

    assert (result.status, result.global_code) == ("failed", Code.IDENTITY_MISMATCH)
    assert all(not p.startswith("files") for p in drive.paths())


def test_unexpected_error_outside_sources_becomes_controlled_global_failure(
    tmp_path: Path,
) -> None:
    drive = FakeDrive()
    drive.add(FOLDER_A, FOLDER)
    collector = _collector(tmp_path, drive, folders=[_folder()])

    def broken(_folder_alias: str) -> dict:
        raise RuntimeError(f"falha com {FOLDER_A}")

    collector.store.folder_members = broken  # type: ignore[method-assign]
    result = collector.run(None)

    assert (result.status, result.global_code) == ("failed", Code.UNEXPECTED_ERROR)
    assert not (collector.config.data_dir / "run.lock").exists()


def test_concurrent_run_is_refused_by_lock(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET)
    collector = _collector(tmp_path, drive, files=[_explicit()])
    collector.config.data_dir.mkdir(parents=True)
    (collector.config.data_dir / "run.lock").write_text("{}", encoding="utf-8")

    result = collector.run(None)

    assert result.global_code == Code.RUN_LOCKED
    assert drive.calls == []


def test_preflight_reads_metadata_only_and_writes_nothing(tmp_path: Path) -> None:
    drive = FakeDrive()
    drive.add(SHEET_1, GOOGLE_SHEET)
    drive.add(FOLDER_A, FOLDER)
    drive.add("SHEETdiaria0000000001", GOOGLE_SHEET, parents=(FOLDER_A,))
    collector = _collector(tmp_path, drive, files=[_explicit()], folders=[_folder()])

    result = collector.preflight(None)

    assert [(s.alias, s.result, s.method) for s in result.sources] == [
        ("financeiro_diario", "eligible", "export_xlsx"),
        ("protestos_dia#1", "eligible", "export_xlsx"),
    ]
    assert drive.content_calls() == []
    assert not collector.config.data_dir.exists()
