"""Piloto OPS-2 — importação verificada para fora do host (``app.ops.offsite``).

A lógica roda em qualquer bancada com a plataforma injetada, como o modo cópia do
ensaio. Modos POSIX e links simbólicos só onde existem (CI Linux).
"""

from __future__ import annotations

import errno
import hashlib
import io
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
# Permissão negada por modo não vale para root: o teste precisa de um usuário comum.
NOT_ROOT = pytest.mark.skipif(
    os.name == "posix" and os.geteuid() == 0, reason="root ignora o modo do diretório"
)
NO_LEFTOVERS = {
    "counts": {"orphan": 0, "active": 0, "unproven": 0, "unexpected": 0},
    "entries": [],
    "removed": 0,
    "removal_failed": 0,
}


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
    assert report["staging"] == {"used": True, "removed": True, "leftovers": NO_LEFTOVERS}
    assert report["schema_version"] == "1.1"
    # A geração publicada tem só o par: o marcador do preparo nunca chega a ela.
    assert sorted(p.name for p in folder.iterdir()) == [
        f"backup-{stamp}.{e}" for e in ("dump", "json")
    ]
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
    assert report["staging"] == {"used": False, "removed": None, "leftovers": NO_LEFTOVERS}
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
    real_copy = offsite._copy_into

    def no_space(handle, work, name):
        real_copy(io.BytesIO(b"PGDMP-pela-metade"), work, name)
        raise OSError(errno.ENOSPC, "sem espaço")

    monkeypatch.setattr(offsite, "_copy_into", no_space)
    before = fingerprint(source)

    report = run(source, destination)

    assert outcome(report) == ("failed", "destination_write_failed", 1)
    assert report["detail"] == {"error_class": "OSError", "errno": "ENOSPC"}
    assert report["staging"] == {"used": True, "removed": True, "leftovers": NO_LEFTOVERS}
    assert staging_entries(destination) == []
    assert not generation(destination, NEWER).exists()
    assert report["destination"]["last_valid_generation"] == stamp_of(OLDER)
    assert is_valid(generation(destination, OLDER), OLDER)
    assert fingerprint(source) == before


def test_corruption_during_the_copy_is_caught_before_promotion(source, destination, monkeypatch):
    real_copy = offsite._copy_into

    def corrupting(handle, work, name):
        data = handle.read()
        real_copy(io.BytesIO(data[:-1] + b"X"), work, name)

    monkeypatch.setattr(offsite, "_copy_into", corrupting)
    report = run(source, destination)
    assert outcome(report) == ("failed", "staged_copy_invalid", 1)
    assert report["detail"] == {"staged": "digest_mismatch"}
    assert not generation(destination, NEWER).exists()
    assert staging_entries(destination) == []


def test_source_that_changes_during_the_copy_is_not_promoted(source, destination, monkeypatch):
    def other_pair(src, work, stamp, manifest_raw):
        write_publication(work.path, NEWER, content=b"PGDMP-trocado-no-meio")

    monkeypatch.setattr(offsite, "_stage", other_pair)
    report = run(source, destination)
    assert outcome(report) == ("failed", "source_changed_during_copy", 1)
    assert not generation(destination, NEWER).exists()
    assert staging_entries(destination) == []


def test_interruption_before_promotion_leaves_no_partial_generation(
    source, destination, monkeypatch
):
    assert run(source, destination, stamp=stamp_of(OLDER))["verdict"] == "published"

    def interrupted(*args):
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
    # OPS-3 (S4): a sobra sem marcador é relatada, nunca presumida órfã — nem a pedido.
    leftovers = report["staging"]["leftovers"]
    assert leftovers["counts"] == {"orphan": 0, "active": 0, "unproven": 1, "unexpected": 0}
    assert [(e["name"], e["state"]) for e in leftovers["entries"]] == [(leftover.name, "unproven")]
    again = run(source, destination, remove_orphan_staging=True)
    assert again["staging"]["leftovers"]["removed"] == 0
    assert leftover.exists() and is_valid(leftover, NEWER)


def test_overlapping_runs_of_the_same_copy_end_idempotent(source, destination, monkeypatch):
    real_rename = os.rename
    armed = {"on": True}
    nested: list[dict] = []

    def rename_after_another_run(src, dst, **kwargs):
        if armed["on"]:
            armed["on"] = False
            nested.append(run(source, destination))
        return real_rename(src, dst, **kwargs)

    monkeypatch.setattr(offsite.os, "rename", rename_after_another_run)
    report = run(source, destination)

    assert outcome(nested[0]) == ("published", "copy_verified", 0)
    assert outcome(report) == ("already_published", "same_copy_already_published", 0)
    assert report["staging"] == {"used": True, "removed": True, "leftovers": NO_LEFTOVERS}
    assert staging_entries(destination) == []
    assert is_valid(generation(destination, NEWER), NEWER)


def test_overlapping_run_with_other_content_is_a_collision(source, destination, monkeypatch):
    real_rename = os.rename
    armed = {"on": True}

    def rename_after_foreign_publication(src, dst, **kwargs):
        if armed["on"]:
            armed["on"] = False
            write_publication(generation(destination, NEWER), NEWER, content=b"PGDMP-alheio")
        return real_rename(src, dst, **kwargs)

    monkeypatch.setattr(offsite.os, "rename", rename_after_foreign_publication)
    report = run(source, destination)

    assert outcome(report) == ("failed", "generation_collision", 1)
    folder = generation(destination, NEWER)
    assert (folder / f"backup-{stamp_of(NEWER)}.dump").read_bytes() == b"PGDMP-alheio"
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
@pytest.mark.parametrize("part", ["root", offsite.GENERATIONS, offsite.STAGING])
def test_linked_destination_is_refused_and_its_target_untouched(tmp_path, source, part):
    target = tmp_path / "alvo"
    target.mkdir(mode=0o700)
    destination = tmp_path / "destino"
    if part == "root":
        destination.symlink_to(target, target_is_directory=True)
    else:
        destination.mkdir(mode=0o700)
        (destination / part).symlink_to(target, target_is_directory=True)

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


# ---------------------------------------------------------------------------
# OPS-3 — endurecimento (S1 caminho, S2 recusa × falha, S4 sobras de .preparo)
# ---------------------------------------------------------------------------


def _deny(monkeypatch, name: str, error: int, *functions: str) -> None:
    """``os.<função>`` falha com ``error`` só para o componente ``name`` — o resto passa."""
    for function in functions:
        real = getattr(os, function)

        def failing(path, *args, _real=real, **kwargs):
            if isinstance(path, str | os.PathLike) and os.path.basename(os.fspath(path)) == name:
                raise OSError(error, os.strerror(error))
            return _real(path, *args, **kwargs)

        monkeypatch.setattr(os, function, failing)


def _killed_during_copy(source: Path, destination: Path, monkeypatch) -> Path:
    """Execução morta no meio da cópia, como num SIGKILL: o ``finally`` não remove o
    preparo, o marcador fica e a trava morre com o processo (aqui, com o descritor)."""

    def dies(*args):
        raise KeyboardInterrupt

    with monkeypatch.context() as patch:
        patch.setattr(offsite, "_stage", dies)
        patch.setattr(offsite, "_remove_own", lambda staging, name: False)
        with pytest.raises(KeyboardInterrupt):
            run(source, destination, platform=sys.platform)
    [name] = staging_entries(destination)
    return destination / offsite.STAGING / name


def test_destination_with_dotdot_is_refused_before_anything_is_written(tmp_path, source):
    report = run(source, tmp_path / "base" / ".." / "destino")

    assert outcome(report) == ("refused", "destination_not_canonical", 2)
    assert report["detail"] == {"part": "root"}
    assert sorted(p.name for p in tmp_path.iterdir()) == ["origem"]


@POSIX_ONLY
@pytest.mark.parametrize("layout", ["parent", "parent_with_copies", "grandparent"])
def test_ancestor_symlink_in_the_destination_is_refused_and_its_target_untouched(
    tmp_path, source, layout
):
    """S1 (sonda ANC): link num ancestral do destino nunca é atravessado — nem para criar,
    nem para ler a última cópia válida que esteja do outro lado."""
    target = tmp_path / "alvo"
    target.mkdir(mode=0o700)
    link = tmp_path / "atalho"
    link.symlink_to(target, target_is_directory=True)
    destination = link / "destino"
    if layout == "parent_with_copies":
        assert run(source, target / "destino", platform=sys.platform)["verdict"] == "published"
    elif layout == "grandparent":
        destination = link / "meio" / "destino"
    before = fingerprint(target)
    listing = sorted(p.relative_to(target).as_posix() for p in target.rglob("*"))

    report = run(source, destination, platform=sys.platform)

    assert outcome(report) == ("refused", "destination_symlink", 2)
    assert report["detail"] == {"part": "ancestor"}
    assert report["destination"]["last_valid_generation"] is None
    assert fingerprint(target) == before
    assert sorted(p.relative_to(target).as_posix() for p in target.rglob("*")) == listing


@POSIX_ONLY
def test_ancestor_swapped_for_a_link_mid_run_never_redirects_the_publication(
    tmp_path, source, monkeypatch
):
    """S1 (TOCTOU): o ancestral, já validado, vira link no meio da cópia. Escrita,
    conferência e promoção seguem presas aos diretórios abertos: a geração nasce no
    diretório original, e nada aparece no alvo do link."""
    base = tmp_path / "base"
    elsewhere = tmp_path / "alheio"
    elsewhere.mkdir(mode=0o700)
    real_stage = offsite._stage

    def stage_then_swap(src, work, stamp, manifest_raw):
        real_stage(src, work, stamp, manifest_raw)
        base.rename(tmp_path / "base-original")
        base.symlink_to(elsewhere, target_is_directory=True)

    monkeypatch.setattr(offsite, "_stage", stage_then_swap)
    report = run(source, base / "destino", platform=sys.platform)

    assert outcome(report) == ("published", "copy_verified", 0)
    moved = tmp_path / "base-original" / "destino"
    assert is_valid(generation(moved, NEWER), NEWER)
    assert staging_entries(moved) == []
    assert list(elsewhere.iterdir()) == []
    # O caminho informado passa agora por um link: o leitor não o segue.
    assert report["destination"]["last_valid_generation"] is None


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (errno.EACCES, ("refused", "destination_unusable", 2)),
        (errno.EPERM, ("refused", "destination_unusable", 2)),
        (errno.EIO, ("failed", "io_error", 1)),
    ],
    ids=["EACCES", "EPERM", "EIO"],
)
def test_destination_that_cannot_be_inspected_is_classified_by_errno(
    tmp_path, source, monkeypatch, error, expected
):
    """S2: sem permissão para inspecionar o destino é recusa; erro de E/S de verdade
    continua falha. Nada é criado em nenhum dos casos."""
    _deny(monkeypatch, "destino", error, "stat", "lstat", "open")
    report = run(source, tmp_path / "destino")
    monkeypatch.undo()

    assert outcome(report) == expected
    error_class = "OSError" if error == errno.EIO else "PermissionError"
    assert report["detail"] == {
        "part": "root",
        "error_class": error_class,
        "errno": errno.errorcode[error],
    }
    assert sorted(os.listdir(tmp_path)) == ["origem"]


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (errno.EACCES, ("refused", "destination_unusable", 2)),
        (errno.EROFS, ("refused", "destination_unusable", 2)),
        (errno.EIO, ("failed", "destination_write_failed", 1)),
        (errno.ENOSPC, ("failed", "destination_write_failed", 1)),
    ],
    ids=["EACCES", "EROFS", "EIO", "ENOSPC"],
)
def test_destination_that_cannot_be_created_is_classified_by_errno(
    tmp_path, source, monkeypatch, error, expected
):
    """S2: criar o destino sem permissão ou em sistema só de leitura é recusa; falta de
    espaço e erro de E/S são falha operacional — nem todo ``OSError`` é recusa."""
    _deny(monkeypatch, "destino", error, "mkdir")
    report = run(source, tmp_path / "destino")
    monkeypatch.undo()

    assert outcome(report) == expected
    assert (report["detail"]["part"], report["detail"]["errno"]) == (
        "root",
        errno.errorcode[error],
    )
    assert sorted(os.listdir(tmp_path)) == ["origem"]


@POSIX_ONLY
@NOT_ROOT
@pytest.mark.parametrize("parent_mode", [0o600, 0o500], ids=["sem_busca", "sem_escrita"])
def test_unusable_destination_under_a_restricted_parent_is_refused_untouched(
    tmp_path, source, parent_mode
):
    """S2 (sonda NOX): destino inexistente sob um pai sem busca (``x``) ou sem escrita é
    recusa. Antes, sem busca, saía ``failed/io_error``."""
    parent = tmp_path / "pai"
    parent.mkdir(mode=0o700)
    os.chmod(parent, parent_mode)
    try:
        report = run(source, parent / "destino", platform=sys.platform)
    finally:
        os.chmod(parent, 0o700)

    assert outcome(report) == ("refused", "destination_unusable", 2)
    assert report["detail"] == {"part": "root", "error_class": "PermissionError", "errno": "EACCES"}
    assert list(parent.iterdir()) == []


@POSIX_ONLY
def test_unusable_destination_owned_by_another_user_is_refused_untouched(
    source, destination, monkeypatch
):
    destination.mkdir(mode=0o700)
    (destination / "sentinela").write_text("intocada")
    real_uid = os.geteuid()
    monkeypatch.setattr(os, "geteuid", lambda: real_uid + 1)

    report = run(source, destination, platform=sys.platform)

    assert outcome(report) == ("refused", "destination_not_owned", 2)
    assert report["detail"] == {"part": "root", "mode": "0700"}
    assert [p.name for p in destination.iterdir()] == ["sentinela"]


def test_unknown_preparo_entries_are_reported_and_never_touched(source, destination):
    """S4: o inventário de ``.preparo/`` só lê. Nome fora do formato, arquivo e sobra sem
    marcador ficam como estão — também com ``--remove-orphan-staging``."""
    assert run(source, destination, stamp=stamp_of(OLDER))["verdict"] == "published"
    staging = destination / offsite.STAGING
    leftover = f"{stamp_of(NEWER)}-deadbeef"
    write_publication(staging / leftover, NEWER)
    (staging / "alheio").mkdir()
    (staging / "nota.txt").write_text("x")
    tighten(destination)
    before = fingerprint(staging)

    for remove in (False, True):
        report = run(source, destination, remove_orphan_staging=remove)

        leftovers = report["staging"]["leftovers"]
        assert leftovers["counts"] == {"orphan": 0, "active": 0, "unproven": 1, "unexpected": 2}
        assert [(e["name"], e["state"]) for e in leftovers["entries"]] == [(leftover, "unproven")]
        assert (leftovers["removed"], leftovers["removal_failed"]) == (0, 0)
        assert fingerprint(staging) == before and (staging / "alheio").is_dir()
        assert "alheio" not in json.dumps(report) and "nota.txt" not in json.dumps(report)


@POSIX_ONLY
def test_staging_leftover_of_a_killed_run_is_an_orphan_removed_only_on_request(
    source, destination, monkeypatch
):
    """S4 (sonda X3): a execução morta deixa o preparo com o marcador coerente e a trava
    livre — ``orphan``. Sem pedido, só relatado; com pedido, removido. A geração
    publicada nunca é tocada."""
    leftover = _killed_during_copy(source, destination, monkeypatch)
    assert (leftover / offsite.RUN_MARKER).is_file()

    report = run(source, destination, platform=sys.platform)

    assert outcome(report) == ("published", "copy_verified", 0)
    leftovers = report["staging"]["leftovers"]
    assert leftovers["counts"] == {"orphan": 1, "active": 0, "unproven": 0, "unexpected": 0}
    assert leftovers["entries"] == [{"name": leftover.name, "state": "orphan", "age_hours": 0.0}]
    assert leftover.is_dir()
    published = fingerprint(destination / offsite.GENERATIONS)

    report = run(source, destination, platform=sys.platform, remove_orphan_staging=True)

    assert outcome(report) == ("already_published", "same_copy_already_published", 0)
    leftovers = report["staging"]["leftovers"]
    assert (leftovers["removed"], leftovers["removal_failed"]) == (1, 0)
    assert leftovers["entries"][0]["removal"] == "removed"
    assert not leftover.exists()
    assert fingerprint(destination / offsite.GENERATIONS) == published
    assert staging_entries(destination) == []


@POSIX_ONLY
def test_staging_leftover_with_a_live_lock_is_active_and_never_removed(
    source, destination, monkeypatch
):
    import fcntl

    leftover = _killed_during_copy(source, destination, monkeypatch)
    holder = os.open(leftover, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(holder, fcntl.LOCK_EX)  # um escritor vivo segura a trava
        report = run(source, destination, platform=sys.platform, remove_orphan_staging=True)

        assert outcome(report) == ("published", "copy_verified", 0)
        leftovers = report["staging"]["leftovers"]
        assert leftovers["counts"] == {"orphan": 0, "active": 1, "unproven": 0, "unexpected": 0}
        assert leftovers["removed"] == 0
        assert (leftover / offsite.RUN_MARKER).is_file()
    finally:
        os.close(holder)

    again = run(source, destination, platform=sys.platform, remove_orphan_staging=True)
    assert again["staging"]["leftovers"]["removed"] == 1
    assert not leftover.exists()


@POSIX_ONLY
def test_cleanup_by_another_run_never_removes_a_staging_leftover_in_progress(
    source, destination, monkeypatch
):
    """S4: outra importação, com limpeza pedida, roda enquanto esta copia. O preparo desta
    está travado: é ``active`` para a outra e segue intacto até a promoção."""
    real_stage = offsite._stage
    armed = {"on": True}
    nested: list[dict] = []

    def stage_while_another_cleans(src, work, stamp, manifest_raw):
        real_stage(src, work, stamp, manifest_raw)
        if armed.pop("on", False):
            other = run(
                source,
                destination,
                platform=sys.platform,
                stamp=stamp_of(OLDER),
                remove_orphan_staging=True,
            )
            nested.append(other)

    monkeypatch.setattr(offsite, "_stage", stage_while_another_cleans)
    report = run(source, destination, platform=sys.platform)

    assert outcome(nested[0]) == ("published", "copy_verified", 0)
    leftovers = nested[0]["staging"]["leftovers"]
    assert leftovers["counts"] == {"orphan": 0, "active": 1, "unproven": 0, "unexpected": 0}
    assert leftovers["removed"] == 0
    assert outcome(report) == ("published", "copy_verified", 0)
    assert staging_entries(destination) == []
    assert is_valid(generation(destination, NEWER), NEWER)
    assert is_valid(generation(destination, OLDER), OLDER)


@POSIX_ONLY
def test_staging_leftovers_that_are_links_or_open_to_others_are_never_touched(
    tmp_path, source, destination, monkeypatch
):
    leftover = _killed_during_copy(source, destination, monkeypatch)
    os.chmod(leftover, 0o777)  # marcador válido, mas aberto a todos: não prova nada
    target = tmp_path / "alvo"
    target.mkdir(mode=0o700)
    (target / "dado").write_text("intocado")
    linked = destination / offsite.STAGING / f"{stamp_of(NEWER)}-cafebabe"
    linked.symlink_to(target, target_is_directory=True)
    before = fingerprint(target)

    report = run(source, destination, platform=sys.platform, remove_orphan_staging=True)

    assert outcome(report) == ("published", "copy_verified", 0)
    leftovers = report["staging"]["leftovers"]
    assert leftovers["counts"] == {"orphan": 0, "active": 0, "unproven": 0, "unexpected": 2}
    assert leftovers["removed"] == 0
    assert stat.S_IMODE(leftover.lstat().st_mode) == 0o777
    assert (leftover / offsite.RUN_MARKER).is_file()
    assert linked.is_symlink() and fingerprint(target) == before


@POSIX_ONLY
@pytest.mark.parametrize("forgery", ["other_run", "naive_start", "linked_marker", "not_json"])
def test_staging_leftover_with_a_forged_marker_is_unproven_and_kept(
    tmp_path, source, destination, monkeypatch, forgery
):
    leftover = _killed_during_copy(source, destination, monkeypatch)
    marker = leftover / offsite.RUN_MARKER
    data = json.loads(marker.read_text(encoding="ascii"))
    marker.unlink()
    if forgery == "other_run":
        marker.write_text(json.dumps(data | {"run": "0" * 8}), encoding="ascii")
    elif forgery == "naive_start":  # sem fuso: não dá idade nem prova
        marker.write_text(json.dumps(data | {"started_at": "2026-11-07T12:00:00"}), "ascii")
    elif forgery == "linked_marker":
        real = tmp_path / "marcador.json"
        real.write_text(json.dumps(data), encoding="ascii")
        marker.symlink_to(real)
    else:
        marker.write_text("{nao e json", encoding="ascii")

    report = run(source, destination, platform=sys.platform, remove_orphan_staging=True)

    leftovers = report["staging"]["leftovers"]
    assert leftovers["counts"] == {"orphan": 0, "active": 0, "unproven": 1, "unexpected": 0}
    assert leftovers["removed"] == 0
    assert leftover.is_dir()


@POSIX_ONLY
def test_staging_leftover_from_another_machine_or_boot_is_unproven_and_kept(
    source, destination, monkeypatch
):
    """S4 (revisão): a trava só prova algo dentro do mesmo kernel. Num destino de rede
    compartilhado, outra máquina poderia segurá-la sem que esta veja — então o marcador
    de outra máquina, ou de outro boot, nunca vira ``orphan``."""
    leftover = _killed_during_copy(source, destination, monkeypatch)
    marker = json.loads((leftover / offsite.RUN_MARKER).read_text(encoding="ascii"))
    assert marker["host"] == offsite._host_token() and len(marker["host"]) == 32
    monkeypatch.setattr(offsite, "_host_token", lambda: "f" * 32)

    report = run(source, destination, platform=sys.platform, remove_orphan_staging=True)

    leftovers = report["staging"]["leftovers"]
    assert leftovers["counts"] == {"orphan": 0, "active": 0, "unproven": 1, "unexpected": 0}
    assert leftovers["removed"] == 0
    assert (leftover / offsite.RUN_MARKER).is_file()
    assert marker["host"] not in json.dumps(report)


def test_run_that_cannot_lock_its_preparo_writes_no_marker(source, destination, monkeypatch):
    """Sem a trava (outro processo a segura, ou o sistema de arquivos não a oferece), a
    execução segue sem marcador: se morrer, a sobra nunca pode ser tida como órfã."""
    monkeypatch.setattr(offsite, "_host_token", lambda: "a" * 32)
    monkeypatch.setattr(offsite, "_try_lock", lambda directory: "held")
    seen: list[list[str]] = []

    def dies(src, work, stamp, manifest_raw):
        seen.append(sorted(os.listdir(work.path)))
        raise KeyboardInterrupt

    monkeypatch.setattr(offsite, "_stage", dies)
    monkeypatch.setattr(offsite, "_remove_own", lambda staging, name: False)
    with pytest.raises(KeyboardInterrupt):
        run(source, destination)

    assert seen == [[]]
    [name] = staging_entries(destination)
    assert not (destination / offsite.STAGING / name / offsite.RUN_MARKER).exists()


def test_leftover_age_from_an_unrepresentable_mtime_is_unknown_not_a_crash():
    assert offsite._mtime_hours(NOW, (NOW - timedelta(hours=3)).timestamp()) == 3.0
    assert offsite._mtime_hours(NOW, 1e20) is None


@POSIX_ONLY
def test_staging_leftover_removal_failure_is_reported_and_the_import_is_unaffected(
    source, destination, monkeypatch
):
    leftover = _killed_during_copy(source, destination, monkeypatch)
    real_rmtree = offsite._Dir.rmtree

    def failing(self, name):
        if name == leftover.name:
            raise OSError(errno.EIO, "falha simulada")
        return real_rmtree(self, name)

    monkeypatch.setattr(offsite._Dir, "rmtree", failing)

    report = run(source, destination, platform=sys.platform, remove_orphan_staging=True)

    assert outcome(report) == ("published", "copy_verified", 0)
    leftovers = report["staging"]["leftovers"]
    assert (leftovers["removed"], leftovers["removal_failed"]) == (0, 1)
    assert leftovers["entries"][0]["removal"] == "failed"
    assert leftover.is_dir()
    assert is_valid(generation(destination, NEWER), NEWER)


def test_cli_passes_the_explicit_orphan_cleanup_request(source, destination, capsys):
    argv = ["--source", str(source), "--destination", str(destination)]
    argv += ["--expected-database", DB, "--remove-orphan-staging"]
    assert offsite.main(argv, clock=fixed_clock(), platform="linux") == 0
    report = json.loads(capsys.readouterr().out)
    assert report["staging"]["leftovers"] == NO_LEFTOVERS
