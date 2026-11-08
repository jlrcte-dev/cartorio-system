"""Cópia verificada fora do host — piloto da CARTORIO-OPS-2.

Importa uma publicação da rotina de backup — ``backup-<carimbo>.dump`` +
``backup-<carimbo>.json``, o contrato que :mod:`app.ops.backup` já avalia — de uma origem
que só é lida para um destino privado, onde ela vira uma **geração**::

    <destino>/geracoes/<carimbo>/backup-<carimbo>.dump
    <destino>/geracoes/<carimbo>/backup-<carimbo>.json
    <destino>/.preparo/                  preparo, no mesmo sistema de arquivos

A origem é avaliada por :func:`evaluate_publication` contra o banco esperado, informado à
parte. O par é copiado para um diretório de preparo novo, conferido de novo ali pela
mesma função e só então promovido por ``rename`` do diretório inteiro: quem lê vê a
geração completa ou não a vê, e nunca olha o preparo. A mesma cópia repetida é
idempotente; uma geração do mesmo carimbo com outro conteúdo, ou inválida, é colisão
visível e fica intocada. Falha ou interrupção nunca alteram geração publicada, e a origem
nunca é escrita.

Como o modo cópia do ensaio (ADR-014), só roda onde o isolamento é comprovável por modo
POSIX. Transporte de rede, agenda, retenção e canal de alerta são etapas posteriores.
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import re
import secrets
import shutil
import stat
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO

from app.ops.backup import STAMP, Evaluation, evaluate_publication, parse_stamp, scan_directory
from app.ops.config import DATABASE_NAME
from app.ops.drill import copy_mode_supported
from app.ops.pgcluster import PRIVATE_FILE_MODE, posix_mode, private_mkdir
from app.ops.report import Clock, utc_iso, utc_now

IMPORT_SCHEMA = "cartorio_system.ops.offsite_import"
SCHEMA_VERSION = "1.0"
GENERATIONS = "geracoes"
STAGING = ".preparo"
# Gerações avaliadas, da mais nova para a mais velha, até achar uma válida.
MAX_EVALUATED = 10

_GENERATION = re.compile(rf"^{STAMP}$")
_EXIT = {"published": 0, "already_published": 0, "failed": 1, "refused": 2}
_NEW_FILE = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
_CHUNK = 1024 * 1024


class OffsiteError(Exception):
    """Interrompe a importação com motivo estável. ``verdict``: ``failed`` (evidência de
    problema na origem ou no destino) ou ``refused`` (configuração ou plataforma)."""

    def __init__(self, verdict: str, reason: str, **facts: object) -> None:
        super().__init__(reason)
        self.verdict = verdict
        self.reason = reason
        self.facts = facts


@dataclass
class Generations:
    """Gerações publicadas, da mais nova para a mais velha. ``ignored`` conta o resto de
    ``geracoes/`` (arquivo, link, nome fora do formato): nunca vale como cópia."""

    stamps: list[str]
    ignored: int


@dataclass
class CopyState:
    generations: Generations
    latest: Evaluation | None
    last_valid: Evaluation | None
    invalid_newer: int


def list_generations(destination: Path) -> Generations:
    """Só diretórios de verdade com nome de carimbo, dentro de ``geracoes/``. O preparo
    fica fora dessa pasta: nenhum leitor o enxerga. Raiz ou ``geracoes/`` que não sejam
    diretório de verdade (link, arquivo) levantam ``NotADirectoryError`` — nunca são
    seguidos."""
    for folder in (destination, destination / GENERATIONS):
        info = folder.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise NotADirectoryError(folder.name)
    stamps: list[str] = []
    ignored = 0
    with os.scandir(destination / GENERATIONS) as entries:
        for entry in entries:
            if _GENERATION.match(entry.name) and entry.is_dir(follow_symlinks=False):
                stamps.append(entry.name)
            else:
                ignored += 1
    return Generations(sorted(stamps, reverse=True), ignored)


def read_copies(destination: Path, expected_database: str | None, now: datetime) -> CopyState:
    """A geração mais nova e a última válida (podem ser a mesma), com o mesmo juízo da
    origem: manifesto, referência confinada, tamanho, digest, ponto de recuperação, banco."""
    generations = list_generations(destination)
    latest: Evaluation | None = None
    last_valid: Evaluation | None = None
    invalid_newer = 0
    for stamp in generations.stamps[:MAX_EVALUATED]:
        folder = destination / GENERATIONS / stamp
        evaluation = evaluate_publication(folder, stamp, now, expected_database)
        if latest is None:
            latest = evaluation
        if evaluation.state == "valid" and evaluation.recovery_point is not None:
            last_valid = evaluation
            break
        invalid_newer += 1
    return CopyState(generations, latest, last_valid, invalid_newer)


def _usable_dir(path: Path, part: str) -> str:
    """Diretório do destino. O que não existe nasce 0700 (com os pais que faltarem); o que
    existe é usado como está — modo, dono e conteúdo — se for diretório de verdade, do
    mesmo dono, sem escrita de grupo ou outros e gravável. ``created`` ou ``existing``."""
    created = False
    try:
        info = path.lstat()
    except FileNotFoundError:
        try:
            private_mkdir(path, parents=True)
            created = True
        except FileExistsError:
            pass  # criado por outra execução entre a checagem e o mkdir: vale como existente
        except OSError as exc:
            raise OffsiteError(
                "refused", "destination_unusable", part=part, error_class=type(exc).__name__
            ) from exc
        info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        raise OffsiteError("refused", "destination_symlink", part=part)
    if not stat.S_ISDIR(info.st_mode):
        raise OffsiteError("refused", "destination_not_directory", part=part)
    mode = f"{stat.S_IMODE(info.st_mode):04o}"
    if os.name == "posix":
        if info.st_uid != os.geteuid():
            raise OffsiteError("refused", "destination_not_owned", part=part, mode=mode)
        if info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise OffsiteError("refused", "destination_writable_by_others", part=part, mode=mode)
    if not os.access(path, os.W_OK | os.X_OK):
        raise OffsiteError("refused", "destination_not_writable", part=part, mode=mode)
    return "created" if created else "existing"


def _source_dir(path: Path) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise OffsiteError("refused", "source_missing") from exc
    if stat.S_ISLNK(info.st_mode):
        raise OffsiteError("refused", "source_symlink")
    if not stat.S_ISDIR(info.st_mode):
        raise OffsiteError("refused", "source_not_directory")


def _disjoint(source: Path, destination: Path) -> None:
    """Destino dentro da origem escreveria nela; origem dentro do destino reimportaria
    uma geração sobre si mesma."""
    src, dst = source.resolve(), destination.resolve()
    if dst == src or dst.is_relative_to(src):
        raise OffsiteError("refused", "destination_inside_source")
    if src.is_relative_to(dst):
        raise OffsiteError("refused", "source_inside_destination")


def _select(source: Path, stamp: str | None) -> str:
    try:
        manifests = scan_directory(source).manifests
    except PermissionError as exc:
        raise OffsiteError("refused", "source_unreadable") from exc
    if stamp is not None:
        if stamp not in manifests:
            raise OffsiteError("failed", "publication_not_found")
        return stamp
    if not manifests:
        # Dump sem manifesto é publicação parcial (app.ops.backup): nunca é importado.
        raise OffsiteError("failed", "no_publication")
    return max(manifests)


def _evidence(evaluation: Evaluation) -> dict[str, Any]:
    return {
        "state": evaluation.state,
        "evaluation": evaluation.reason,
        "recovery_point_utc": evaluation.facts.get("recovery_point_utc"),
        "size_bytes": evaluation.facts.get("size_bytes"),
        "sha256": evaluation.facts.get("sha256"),
    }


def _io_facts(exc: OSError) -> dict[str, object]:
    return {
        "error_class": type(exc).__name__,
        "errno": errno.errorcode.get(exc.errno) if exc.errno is not None else None,
    }


def _copy_into(source: BinaryIO, target: Path) -> None:
    """Arquivo novo já em 0600 (nunca sobrescreve), gravado em disco antes de fechar."""
    fd = os.open(target, _NEW_FILE, PRIVATE_FILE_MODE)
    with os.fdopen(fd, "wb") as handle:
        shutil.copyfileobj(source, handle, _CHUNK)
        handle.flush()
        os.fsync(handle.fileno())


def _write_into(target: Path, data: bytes) -> None:
    fd = os.open(target, _NEW_FILE, PRIVATE_FILE_MODE)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _sync_dir(path: Path) -> None:
    """Persiste no diretório a entrada criada ou renomeada (só POSIX abre diretório)."""
    if os.name != "posix":
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _stage(source: Path, work: Path, stamp: str, manifest_raw: bytes) -> None:
    dump = f"backup-{stamp}.dump"
    try:
        handle = (source / dump).open("rb")
    except OSError as exc:
        raise OffsiteError("failed", "source_unreadable", **_io_facts(exc)) from exc
    try:
        with handle:
            _copy_into(handle, work / dump)
        _write_into(work / f"backup-{stamp}.json", manifest_raw)
    except OSError as exc:
        raise OffsiteError("failed", "destination_write_failed", **_io_facts(exc)) from exc


def _same_as_published(
    final: Path, stamp: str, manifest_raw: bytes, digest: str, now: datetime, expected: str
) -> None:
    """Já existe geração com este carimbo: idêntica é a mesma cópia (idempotente); com
    outro conteúdo, ou inválida, é colisão — e nada nela é tocado."""
    info = final.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise OffsiteError("failed", "generation_collision", existing="not_a_generation")
    existing = evaluate_publication(final, stamp, now, expected)
    if existing.state != "valid":
        raise OffsiteError("failed", "generation_collision", existing=existing.reason)
    try:
        same_manifest = (final / f"backup-{stamp}.json").read_bytes() == manifest_raw
    except OSError:
        same_manifest = False
    if not same_manifest or existing.facts.get("sha256") != digest:
        raise OffsiteError("failed", "generation_collision", existing="different_content")


def _promote(work: Path, final: Path) -> bool:
    """``rename`` do diretório inteiro. ``False`` se o destino já existe — outra execução
    publicou o mesmo carimbo durante o preparo; quem chama compara o conteúdo."""
    if os.path.lexists(final):
        return False
    try:
        os.rename(work, final)
    except OSError as exc:
        if os.path.lexists(final):
            return False
        raise OffsiteError("failed", "promotion_failed", **_io_facts(exc)) from exc
    return True


def _remove_own(work: Path) -> bool:
    """Remove só o preparo desta execução (nome com sufixo aleatório próprio). Depois da
    promoção ele já não existe: virou a geração."""
    if not os.path.lexists(work):
        return True
    try:
        shutil.rmtree(work)
    except OSError:
        return False
    return True


def _isolation(final: Path, stamp: str) -> dict[str, Any] | None:
    if os.name != "posix":
        return None
    return {
        "generation_dir": posix_mode(final),
        "files": [posix_mode(final / f"backup-{stamp}.{ext}") for ext in ("dump", "json")],
    }


def _import(
    source: Path,
    destination: Path,
    expected: str,
    now: datetime,
    stamp: str | None,
    platform: str,
    report: dict[str, Any],
) -> str:
    if not copy_mode_supported(platform):
        raise OffsiteError("refused", "offsite_unsupported_platform")
    if not DATABASE_NAME.match(expected):
        raise OffsiteError("refused", "expected_database_invalid")
    if stamp is not None and parse_stamp(stamp) is None:
        raise OffsiteError("refused", "stamp_invalid")
    _source_dir(source)
    _disjoint(source, destination)
    stamp = _select(source, stamp)
    report["source"]["stamp"] = stamp
    evaluation = evaluate_publication(source, stamp, now, expected)
    report["source"].update(_evidence(evaluation))
    if evaluation.state != "valid":
        raise OffsiteError("failed", evaluation.reason)
    digest = str(evaluation.facts["sha256"])
    try:
        manifest_raw = (source / f"backup-{stamp}.json").read_bytes()
    except OSError as exc:
        raise OffsiteError("failed", "source_unreadable", **_io_facts(exc)) from exc

    report["destination"]["root"] = _usable_dir(destination, "root")
    generations = destination / GENERATIONS
    _usable_dir(generations, GENERATIONS)
    final = generations / stamp
    report["destination"]["generation"] = stamp
    if os.path.lexists(final):
        _same_as_published(final, stamp, manifest_raw, digest, now, expected)
        return "already_published"

    staging = destination / STAGING
    _usable_dir(staging, STAGING)
    work = staging / f"{stamp}-{secrets.token_hex(4)}"
    try:
        private_mkdir(work)
    except OSError as exc:
        raise OffsiteError("failed", "destination_write_failed", **_io_facts(exc)) from exc
    report["staging"]["used"] = True
    try:
        _stage(source, work, stamp, manifest_raw)
        staged = evaluate_publication(work, stamp, now, expected)
        if staged.state != "valid":
            raise OffsiteError("failed", "staged_copy_invalid", staged=staged.reason)
        if staged.facts.get("sha256") != digest:
            raise OffsiteError("failed", "source_changed_during_copy")
        _sync_dir(work)
        if not _promote(work, final):
            _same_as_published(final, stamp, manifest_raw, digest, now, expected)
            return "already_published"
        _sync_dir(generations)
        report["destination"]["isolation"] = _isolation(final, stamp)
        return "published"
    finally:
        report["staging"]["removed"] = _remove_own(work)


def run_import(
    source: Path,
    destination: Path,
    expected_database: str,
    *,
    now: datetime,
    stamp: str | None = None,
    platform: str = sys.platform,
) -> dict[str, Any]:
    """Importa a publicação mais recente (ou ``stamp``) e devolve o relatório
    ``cartorio_system.ops.offsite_import`` 1.0 — sem caminho e sem nome de banco."""
    report: dict[str, Any] = {
        "schema": IMPORT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "started_at": utc_iso(now),
        "verdict": "failed",
        "reason": "not_finished",
        "source": {"stamp": stamp},
        "destination": {},
        "staging": {"used": False, "removed": None},
    }
    try:
        outcome = _import(source, destination, expected_database, now, stamp, platform, report)
        reason = "copy_verified" if outcome == "published" else "same_copy_already_published"
        report.update(verdict=outcome, reason=reason)
    except OffsiteError as exc:
        report.update(verdict=exc.verdict, reason=exc.reason)
        if exc.facts:
            report["detail"] = exc.facts
    except OSError as exc:
        # Fora dos pontos previstos: só a classe e o errno saem, nunca o caminho.
        report.update(verdict="failed", reason="io_error", detail=_io_facts(exc))
    report["destination"]["last_valid_generation"] = _last_valid_stamp(
        destination, expected_database, now
    )
    report["exit_code"] = _EXIT[report["verdict"]]
    return report


def _last_valid_stamp(destination: Path, expected_database: str, now: datetime) -> str | None:
    """Prova de que a última geração válida segue legível, qualquer que seja o desfecho.
    Só leitura, e o leitor nunca segue link na raiz nem em ``geracoes/``."""
    try:
        state = read_copies(destination, expected_database, now)
    except OSError:
        return None
    return state.last_valid.stamp if state.last_valid is not None else None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.ops.offsite",
        description=(
            "Importa a publicação mais recente da rotina de backup, verificada, como uma "
            "geração nova num destino privado. Saída: 0 publicada ou já presente, "
            "1 falha, 2 recusa."
        ),
    )
    parser.add_argument("--source", type=Path, required=True, help="diretório da rotina (só lido)")
    parser.add_argument(
        "--destination", type=Path, required=True, help="raiz privada das cópias externas"
    )
    parser.add_argument(
        "--expected-database",
        required=True,
        help="banco de que a cópia precisa ser (configuração à parte, nunca do manifesto)",
    )
    parser.add_argument("--stamp", help="importa esta publicação (AAAAMMDDTHHMMSSZ)")
    return parser


def main(
    argv: Sequence[str] | None = None, *, clock: Clock = utc_now, platform: str = sys.platform
) -> int:
    args = _parser().parse_args(argv)
    report = run_import(
        args.source,
        args.destination,
        args.expected_database,
        now=clock(),
        stamp=args.stamp,
        platform=platform,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(report["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
