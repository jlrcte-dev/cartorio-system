"""Configuração do coletor: fronteira explícita, tetos e recusa de entradas inseguras."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.modules.drive_capture.config import (
    GOOGLE_SHEET,
    HARD_CAPS,
    REPO_ROOT,
    load_config,
    parse_config,
)
from app.modules.drive_capture.errors import Code, DriveCaptureError
from tests.drive_capture_support import IDENTITY, make_config

EXAMPLE = REPO_ROOT / "docs" / "modules" / "drive_capture.config.example.yaml"
VALID_ID = "1AAAAAAAAAAAAAAAAAAAAA"


def _file(**overrides: object) -> dict:
    item = {"alias": "financeiro_piloto", "family": "gerenciamento_financeiro", "file_id": VALID_ID}
    item.update(overrides)
    return item


def _invalid(tmp_path: Path, **overrides: object) -> DriveCaptureError:
    with pytest.raises(DriveCaptureError) as excinfo:
        make_config(tmp_path, **overrides)
    assert excinfo.value.code == Code.CONFIG_INVALID
    return excinfo.value


def test_versioned_example_is_fictitious_and_valid(tmp_path: Path) -> None:
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["credentials_file"] = str(tmp_path / "sa.json")
    data["data_dir"] = str(tmp_path / "dados")

    config = parse_config(data, tmp_path)

    assert [f.alias for f in config.files] == ["financeiro_piloto"]
    assert config.accepted_stored_mime_types == frozenset()
    assert config.shared_drive_id is None


def test_missing_config_file_is_explicit(tmp_path: Path) -> None:
    with pytest.raises(DriveCaptureError) as excinfo:
        load_config(tmp_path / "nao-existe.yaml")
    assert excinfo.value.code == Code.CONFIG_INVALID


def test_relative_paths_resolve_against_config_dir(tmp_path: Path) -> None:
    path = tmp_path / "cfg" / "config.yaml"
    path.parent.mkdir()
    path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "credentials_file": "../segredo/sa.json",
                "expected_identity": IDENTITY,
                "files": [_file()],
            }
        ),
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.data_dir == path.parent.resolve()
    assert config.credentials_file == (tmp_path / "segredo" / "sa.json").resolve()


@pytest.mark.parametrize(
    "overrides",
    [
        {"files": [_file(file_id="https://docs.google.com/spreadsheets/d/1AAAAAAAAAAA/edit")]},
        {"files": [_file(alias="Cliente Fulano")]},
        {"files": [_file(family="financeiro_pessoal")]},
        {"files": [_file(), _file(alias="outro_alias")]},
        {"files": [_file(), _file(file_id="1BBBBBBBBBBBBBBBBBBBBBB")]},
        {"files": []},
        {"expected_identity": None, "files": [_file()]},
        {"version": 2, "files": [_file()]},
        {"limits": {"max_file_bytes": HARD_CAPS["max_file_bytes"] + 1}, "files": [_file()]},
        {"limits": {"desconhecido": 1}, "files": [_file()]},
        {"limits": {"max_sources": 0}, "files": [_file()]},
        {"accepted_stored_mime_types": ["image/png"], "files": [_file()]},
        {"folders": [{"alias": "pasta", "family": "protestos", "folder_id": VALID_ID}]},
        {
            "folders": [
                {
                    "alias": "pasta",
                    "family": "protestos",
                    "folder_id": VALID_ID,
                    "include": {"mime_types": ["application/pdf"]},
                }
            ]
        },
        {
            "folders": [
                {
                    "alias": "pasta",
                    "family": "protestos",
                    "folder_id": VALID_ID,
                    "recursive": True,
                    "include": {"mime_types": [GOOGLE_SHEET]},
                }
            ]
        },
    ],
)
def test_unsafe_or_ambiguous_config_is_refused(tmp_path: Path, overrides: dict) -> None:
    error = _invalid(tmp_path, **overrides)
    assert "docs.google.com" not in str(error)
    assert VALID_ID not in str(error)


def test_data_and_credentials_cannot_live_in_versioned_tree(tmp_path: Path) -> None:
    _invalid(tmp_path, data_dir=str(REPO_ROOT / "docs" / "capturas"), files=[_file()])
    _invalid(tmp_path, credentials_file=str(REPO_ROOT / "sa.json"), files=[_file()])

    config = make_config(
        tmp_path,
        data_dir=str(REPO_ROOT / "_local_data" / "drive_capture"),
        files=[_file()],
    )
    assert config.data_dir == (REPO_ROOT / "_local_data" / "drive_capture").resolve()
