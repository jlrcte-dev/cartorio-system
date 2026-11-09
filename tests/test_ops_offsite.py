"""Piloto OPS-2 — importação verificada para fora do host (``app.ops.offsite``).

A lógica roda em qualquer bancada com a plataforma injetada, como o modo cópia do
ensaio. Modos POSIX e links simbólicos só onde existem (CI Linux).
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import stat
import sys
from datetime import timedelta
from pathlib import Path

import pytest

from app.ops import offsite
from app.ops.backup import evaluate_publication
from tests.ops_support import NOW, REMOVE, fixed_clock, stamp_of, write_publication

DB = "cartorio_lab"
OLDER = NOW - timedelta(hours=25)
NEWER = NOW - timedelta(hours=1)
POSIX_ONLY = pytest.mark.skipif(os.name != "posix", reason="modos POSIX e links: CI Linux")


def run(source: Path, destination: Path, **kwargs):
    kwargs.setdefault("now", NOW)
    kwargs.setdefault("platform", "linux")
    expected = kwargs.pop("expected", DB)
    return offsite.run_import(source, destination, expected, **kwargs)


def outcome(report: dict) -> tuple[str, str, int]:
    return report["verdict"], report["reason"], report["exit_code"]


def fingerprint(root: Path) -> dict[str, tuple[int, int, str]]:
    """Modo, mtime e SHA-256 de cada arquivo: prova de que nada mudou."""
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            info = path.stat()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            result[path.relative_to(root).as_posix()] = (info.st_mode, info.st_mtime_ns, digest)
    return result


def generation(destination: Path, moment) -> Path:
    return destination / offsite.GENERATIONS / stamp_of(moment)


def staging_entries(destination: Path) -> list[str]:
    staging = destination / offsite.STAGING
    return sorted(p.name for p in staging.iterdir()) if staging.exists() else []


def is_valid(folder: Path, moment) -> bool:
    return evaluate_publication(folder, stamp_of(moment), NOW, DB).state == "valid"


def tighten(root: Path) -> None:
    """Pastas criadas pelo teste ficam como as do piloto (0700), qualquer que seja a umask."""
    if os.name == "posix":
        for folder in [root, *[p for p in root.rglob("*") if p.is_dir()]]:
            os.chmod(folder, 0o700)


@pytest.fixture
def source(tmp_path):
    folder = tmp_path / "origem"
    write_publication(folder, OLDER, content=b"PGDMP-geracao-anterior")
    write_publication(folder, NEWER, content=b"PGDMP-geracao-recente")
    return folder


@pytest.fixture
def destination(tmp_path):
    return tmp_path / "destino"


def test_healthy_import_publishes_the_latest_pair_verified_and_leaves_the_source_untouched(
    tmp_path, source, destination
):
    before = fingerprint(source)
    report = run(source, destination)

    assert outcome(report) == ("published", "copy_verified", 0)
    stamp = stamp_of(NEWER)
    folder = generation(destination, NEWER)
    for ext in ("dump", "json"):
        name = f"backup-{stamp}.{ext}"
        assert (folder / name).read_bytes() == (source / name).read_bytes()
    assert is_valid(folder, NEWER)
    assert report["source"] == {
        "stamp": stamp,
        "state": "valid",
        "evaluation": "digest_verified",
        "recovery_point_utc": "2026-11-07T11:00:00Z",
        "size_bytes": len(b"PGDMP-geracao-recente"),
        "sha256": hashlib.sha256(b"PGDMP-geracao-recente").hexdigest(),
    }
    assert report["destination"]["root"] == "created"
    assert report["destination"]["generation"] == stamp
    assert report["destination"]["last_valid_generation"] == stamp
    assert report["staging"] == {"used": True, "removed": True}
    assert staging_entries(destination) == []
    assert fingerprint(source) == before
    text = json.dumps(report)
    assert str(tmp_path) not in text and DB not in text


def test_dump_without_manifest_is_partial_and_never_imported(tmp_path, destination):
    folder = tmp_path / "origem"
    write_publication(folder, OLDER)
    write_publication(folder, NEWER, manifest=False)  # publicação em andamento
    report = run(folder, destination)
    assert outcome(report) == ("published", "copy_verified", 0)
    assert report["source"]["stamp"] == stamp_of(OLDER)

    only_dump = tmp_path / "so-dump"
    write_publication(only_dump, NEWER, manifest=False)
    empty = tmp_path / "destino-vazio"
    assert outcome(run(only_dump, empty)) == ("failed", "no_publication", 1)
    assert not empty.exists()


def test_repeating_the_same_copy_is_idempotent(source, destination):
    assert run(source, destination)["verdict"] == "published"
    before = fingerprint(destination)

    report = run(source, destination)

    assert outcome(report) == ("already_published", "same_copy_already_published", 0)
    assert report["staging"] == {"used": False, "removed": None}
    assert fingerprint(destination) == before
    assert [p.name for p in (destination / offsite.GENERATIONS).iterdir()] == [stamp_of(NEWER)]


@pytest.mark.parametrize("existing", ["different_content", "incomplete"])
def test_generation_with_the_same_stamp_and_other_content_is_a_visible_collision(
    source, destination, existing
):
    folder = generation(destination, NEWER)
    if existing == "different_content":
        write_publication(folder, NEWER, content=b"PGDMP-outra-copia")
        expected_detail = "different_content"
    else:
        write_publication(folder, NEWER, manifest=False)
        expected_detail = "manifest_missing"
    tighten(destination)
    before = fingerprint(destination)

    report = run(source, destination)

    assert outcome(report) == ("failed", "generation_collision", 1)
    assert report["detail"] == {"existing": expected_detail}
    assert fingerprint(destination) == before
    assert staging_entries(destination) == []


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"database": "outro_banco"}, "database_mismatch"),
        ({"sha256": "0" * 64}, "digest_mismatch"),
        ({"tamanho_bytes": 1}, "size_mismatch"),
        ({"sha256": REMOVE}, "manifest_incomplete"),
        ({"database": REMOVE}, "manifest_incomplete"),
        ({"arquivo": "../fora.dump"}, "reference_outside_dir"),
        ({"arquivo": "backup-20200101T000000Z.dump"}, "manifest_inconsistent"),
        ({"gerado_em_utc": "20200101T000000Z"}, "manifest_inconsistent"),
    ],
)
def test_invalid_source_publication_is_refused_and_the_previous_generation_survives(
    tmp_path, destination, overrides, reason
):
    folder = tmp_path / "origem"
    write_publication(folder, OLDER, content=b"PGDMP-anterior")
    assert run(folder, destination)["verdict"] == "published"
    write_publication(folder, NEWER, content=b"PGDMP-recente", overrides=overrides)
    before_source, before_destination = fingerprint(folder), fingerprint(destination)

    report = run(folder, destination)

    assert outcome(report) == ("failed", reason, 1)
    assert fingerprint(folder) == before_source
    assert fingerprint(destination) == before_destination
    assert report["destination"]["last_valid_generation"] == stamp_of(OLDER)
    assert DB not in json.dumps(report) and "outro_banco" not in json.dumps(report)


def test_recovery_point_in_the_future_is_not_imported(tmp_path, destination):
    folder = tmp_path / "origem"
    write_publication(folder, NOW + timedelta(hours=1))
    assert outcome(run(folder, destination)) == ("failed", "recovery_point_in_future", 1)
    assert not destination.exists()


@pytest.mark.parametrize(
    ("case", "reason"),
    [
        ("platform", "offsite_unsupported_platform"),
        ("database", "expected_database_invalid"),
        ("stamp", "stamp_invalid"),
        ("no_source", "source_missing"),
        ("source_file", "source_not_directory"),
        ("inside_source", "destination_inside_source"),
        ("inside_destination", "source_inside_destination"),
        ("destination_file", "destination_not_directory"),
    ],
)
def test_refusals_happen_before_anything_is_written(tmp_path, source, case, reason):
    destination = tmp_path / "destino"
    kwargs: dict = {}
    if case == "platform":
        kwargs["platform"] = "win32"
    elif case == "database":
        kwargs["expected"] = "nome; inválido"
    elif case == "stamp":
        kwargs["stamp"] = "../ontem"
    elif case == "no_source":
        source = tmp_path / "nao-existe"
    elif case == "source_file":
        source = tmp_path / "arquivo"
        source.write_text("x")
    elif case == "inside_source":
        destination = source / "copias"
    elif case == "inside_destination":
        destination = tmp_path
    else:
        destination.write_text("não é diretório")
    before = fingerprint(tmp_path)

    report = run(source, destination, **kwargs)

    assert outcome(report) == ("refused", reason, 2)
    assert fingerprint(tmp_path) == before
    assert not (tmp_path / "destino" / offsite.GENERATIONS).exists()
    assert not (source / "copias").exists()


def test_write_failure_at_the_destination_keeps_the_previous_generation(
    source, destination, monkeypatch
):
    assert run(source, destination, stamp=stamp_of(OLDER))["verdict"] == "published"

    def no_space(handle, target):
        Path(target).write_bytes(b"PGDMP-pela-metade")
        raise OSError(errno.ENOSPC, "sem espaço")

    monkeypatch.setattr(offsite, "_copy_into", no_space)
    before = fingerprint(source)

    report = run(source, destination)

    assert outcome(report) == ("failed", "destination_write_failed", 1)
    assert report["detail"] == {"error_class": "OSError", "errno": "ENOSPC"}
    assert report["staging"] == {"used": True, "removed": True}
    assert staging_entries(destination) == []
    assert not generation(destination, NEWER).exists()
    assert report["destination"]["last_valid_generation"] == stamp_of(OLDER)
    assert is_valid(generation(destination, OLDER), OLDER)
    assert fingerprint(source) == before


def test_corruption_during_the_copy_is_caught_before_promotion(source, destination, monkeypatch):
    def corrupting(handle, target):
        data = handle.read()
        Path(target).write_bytes(data[:-1] + b"X")

    monkeypatch.setattr(offsite, "_copy_into", corrupting)
    report = run(source, destination)
    assert outcome(report) == ("failed", "staged_copy_invalid", 1)
    assert report["detail"] == {"staged": "digest_mismatch"}
    assert not generation(destination, NEWER).exists()
    assert staging_entries(destination) == []


def test_source_that_changes_during_the_copy_is_not_promoted(source, destination, monkeypatch):
    def other_pair(src, work, stamp, manifest_raw):
        write_publication(work, NEWER, content=b"PGDMP-trocado-no-meio")

    monkeypatch.setattr(offsite, "_stage", other_pair)
    report = run(source, destination)
    assert outcome(report) == ("failed", "source_changed_during_copy", 1)
    assert not generation(destination, NEWER).exists()
    assert staging_entries(destination) == []


def test_interruption_before_promotion_leaves_no_partial_generation(
    source, destination, monkeypatch
):
    assert run(source, destination, stamp=stamp_of(OLDER))["verdict"] == "published"

    def interrupted(work, final):
        raise KeyboardInterrupt

    monkeypatch.setattr(offsite, "_promote", interrupted)
    with pytest.raises(KeyboardInterrupt):
        run(source, destination)

    assert not generation(destination, NEWER).exists()
    assert staging_entries(destination) == []
    state = offsite.read_copies(destination, DB, NOW)
    assert state.last_valid is not None and state.last_valid.stamp == stamp_of(OLDER)


def test_leftovers_of_a_killed_run_are_ignored_and_never_deleted(source, destination):
    assert run(source, destination, stamp=stamp_of(OLDER))["verdict"] == "published"
    # Restos de uma execução morta no meio: preparo completo e geração sem dump.
    leftover = destination / offsite.STAGING / f"{stamp_of(NEWER)}-deadbeef"
    write_publication(leftover, NEWER)
    newest = NOW - timedelta(minutes=30)
    broken = generation(destination, newest)
    write_publication(broken, newest)
    (broken / f"backup-{stamp_of(newest)}.dump").unlink()
    (destination / offsite.GENERATIONS / "anotacao.txt").write_text("x")
    tighten(destination)

    state = offsite.read_copies(destination, DB, NOW)

    assert state.generations.stamps == [stamp_of(newest), stamp_of(OLDER)]
    assert state.generations.ignored == 1
    assert state.latest is not None and (state.latest.state, state.latest.reason) == (
        "invalid",
        "artifact_missing",
    )
    assert state.last_valid is not None and state.last_valid.stamp == stamp_of(OLDER)
    report = run(source, destination)
    assert outcome(report) == ("published", "copy_verified", 0)
    assert leftover.exists()


def test_overlapping_runs_of_the_same_copy_end_idempotent(source, destination, monkeypatch):
    real_rename = os.rename
    armed = {"on": True}
    nested: list[dict] = []

    def rename_after_another_run(src, dst):
        if armed["on"]:
            armed["on"] = False
            nested.append(run(source, destination))
        return real_rename(src, dst)

    monkeypatch.setattr(offsite.os, "rename", rename_after_another_run)
    report = run(source, destination)

    assert outcome(nested[0]) == ("published", "copy_verified", 0)
    assert outcome(report) == ("already_published", "same_copy_already_published", 0)
    assert report["staging"] == {"used": True, "removed": True}
    assert staging_entries(destination) == []
    assert is_valid(generation(destination, NEWER), NEWER)


def test_overlapping_run_with_other_content_is_a_collision(source, destination, monkeypatch):
    real_rename = os.rename
    armed = {"on": True}

    def rename_after_foreign_publication(src, dst):
        if armed["on"]:
            armed["on"] = False
            write_publication(Path(dst), NEWER, content=b"PGDMP-de-outra-origem")
        return real_rename(src, dst)

    monkeypatch.setattr(offsite.os, "rename", rename_after_foreign_publication)
    report = run(source, destination)

    assert outcome(report) == ("failed", "generation_collision", 1)
    folder = generation(destination, NEWER)
    assert (folder / f"backup-{stamp_of(NEWER)}.dump").read_bytes() == b"PGDMP-de-outra-origem"
    assert staging_entries(destination) == []


@POSIX_ONLY
def test_new_destination_is_private_under_umask_022(source, destination):
    old = os.umask(0o022)
    try:
        report = run(source, destination, platform=sys.platform)
    finally:
        os.umask(old)
    assert outcome(report) == ("published", "copy_verified", 0)
    folder = generation(destination, NEWER)
    for path in (destination, destination / offsite.GENERATIONS, destination / offsite.STAGING):
        assert stat.S_IMODE(path.stat().st_mode) == 0o700
    assert stat.S_IMODE(folder.stat().st_mode) == 0o700
    assert sorted(stat.S_IMODE(p.stat().st_mode) for p in folder.iterdir()) == [0o600, 0o600]
    assert report["destination"]["isolation"] == {
        "generation_dir": "0700",
        "files": ["0600", "0600"],
    }


@POSIX_ONLY
@pytest.mark.parametrize("mode", [0o770, 0o775, 0o777, 0o1777], ids=lambda m: f"{m:04o}")
def test_destination_writable_by_others_is_refused_untouched(source, destination, mode):
    destination.mkdir()
    os.chmod(destination, mode)
    (destination / "sentinela").write_text("intocada")

    report = run(source, destination, platform=sys.platform)

    assert outcome(report) == ("refused", "destination_writable_by_others", 2)
    assert destination.stat().st_mode & 0o7777 == mode
    assert [p.name for p in destination.iterdir()] == ["sentinela"]


@POSIX_ONLY
@pytest.mark.parametrize("part", ["root", offsite.GENERATIONS])
def test_linked_destination_is_refused_and_its_target_untouched(tmp_path, source, part):
    target = tmp_path / "alvo"
    target.mkdir(mode=0o700)
    destination = tmp_path / "destino"
    if part == "root":
        destination.symlink_to(target, target_is_directory=True)
    else:
        destination.mkdir(mode=0o700)
        (destination / offsite.GENERATIONS).symlink_to(target, target_is_directory=True)

    report = run(source, destination, platform=sys.platform)

    assert outcome(report) == ("refused", "destination_symlink", 2)
    assert report["detail"] == {"part": part}
    assert list(target.iterdir()) == []


@POSIX_ONLY
@pytest.mark.parametrize("what", ["manifest", "dump", "root"])
def test_links_in_the_source_are_never_followed(tmp_path, destination, what):
    real = tmp_path / "real"
    write_publication(real, NEWER)
    source = tmp_path / "origem"
    if what == "root":
        source.symlink_to(real, target_is_directory=True)
        expected = ("refused", "source_symlink", 2)
    else:
        source.mkdir()
        for ext in ("dump", "json"):
            name = f"backup-{stamp_of(NEWER)}.{ext}"
            if (ext == "json") == (what == "manifest"):
                (source / name).symlink_to(real / name)
            else:
                (source / name).write_bytes((real / name).read_bytes())
        expected = ("failed", "reference_outside_dir", 1)

    report = run(source, destination, platform=sys.platform)

    assert outcome(report) == expected
    assert not (destination / offsite.GENERATIONS).exists()


@POSIX_ONLY
def test_linked_generation_is_a_collision_and_its_target_is_untouched(
    tmp_path, source, destination
):
    target = tmp_path / "alvo"
    write_publication(target, NEWER, content=b"PGDMP-alheio")
    (destination / offsite.GENERATIONS).mkdir(parents=True)
    tighten(destination)
    generation(destination, NEWER).symlink_to(target, target_is_directory=True)
    before = fingerprint(target)

    report = run(source, destination, platform=sys.platform)

    assert outcome(report) == ("failed", "generation_collision", 1)
    assert report["detail"] == {"existing": "not_a_generation"}
    assert fingerprint(target) == before


def test_cli_prints_the_report_and_returns_its_exit_code(tmp_path, source, destination, capsys):
    argv = ["--source", str(source), "--destination", str(destination)]
    code = offsite.main([*argv, "--expected-database", DB], clock=fixed_clock(), platform="linux")
    out = capsys.readouterr().out
    report = json.loads(out)
    assert code == report["exit_code"] == 0
    assert report["verdict"] == "published"
    assert str(tmp_path) not in out and DB not in out


def test_cli_refuses_on_windows_before_creating_anything(source, destination, capsys):
    argv = ["--source", str(source), "--destination", str(destination)]
    code = offsite.main([*argv, "--expected-database", DB], clock=fixed_clock(), platform="win32")
    assert code == 2
    assert json.loads(capsys.readouterr().out)["reason"] == "offsite_unsupported_platform"
    assert not destination.exists()


def test_cli_requires_the_expected_database_as_separate_configuration(source, destination):
    with pytest.raises(SystemExit) as exc:
        offsite.main(["--source", str(source), "--destination", str(destination)])
    assert exc.value.code == 2
