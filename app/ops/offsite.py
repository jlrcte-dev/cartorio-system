"""Cópia verificada fora do host — piloto da CARTORIO-OPS-2, endurecido na OPS-3.

Importa uma publicação da rotina de backup — ``backup-<carimbo>.dump`` +
``backup-<carimbo>.json``, o contrato que :mod:`app.ops.backup` já avalia — de uma origem
que só é lida para um destino privado, onde ela vira uma **geração**::

    <destino>/geracoes/<carimbo>/backup-<carimbo>.dump
    <destino>/geracoes/<carimbo>/backup-<carimbo>.json
    <destino>/.preparo/<carimbo>-<sufixo>/   preparo de uma execução, no mesmo sistema de arquivos

A origem é avaliada por :func:`evaluate_publication` contra o banco esperado, informado à
parte. O par é copiado para um diretório de preparo novo, conferido de novo ali pela
mesma função e só então promovido por ``rename`` do diretório inteiro: quem lê vê a
geração completa ou não a vê, e nunca olha o preparo. A mesma cópia repetida é
idempotente; uma geração do mesmo carimbo com outro conteúdo, ou inválida, é colisão
visível e fica intocada. Falha ou interrupção nunca alteram geração publicada, e a origem
nunca é escrita.

**Caminho do destino (OPS-3).** O destino é aberto componente a componente, a partir da
raiz do sistema de arquivos, sem seguir link em nenhum deles — ancestral inclusive. No
POSIX, tudo o que vem depois (criar, conferir, promover, remover o próprio preparo) é
relativo aos diretórios já abertos: trocar um componente do caminho por um link no meio
da execução não muda onde se escreve. Caminho com ``..`` é recusado.

**Preparo de execução interrompida (OPS-3).** Cada execução trava (``flock``) o próprio
preparo enquanto vive e grava nele um marcador com a máquina e o boot; a trava morre com o
processo. Toda importação inventaria o resto de ``.preparo/`` sem seguir nada; só o que
tem nome do formato, é diretório de verdade do mesmo dono, sem escrita de grupo ou outros,
tem a trava livre e o marcador coerente com o nome, escrito nesta máquina neste boot, é
``orphan`` — e só sai com ``--remove-orphan-staging``, ainda com a trava na mão. O resto
nunca é tocado.

Como o modo cópia do ensaio (ADR-014), só roda onde o isolamento é comprovável por modo
POSIX. Transporte de rede, agenda, retenção e canal de alerta são etapas posteriores.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import sys
from collections.abc import Callable, Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO

from app.ops.backup import (
    STAMP,
    Evaluation,
    evaluate_publication,
    parse_stamp,
    scan_directory,
)
from app.ops.config import DATABASE_NAME
from app.ops.drill import copy_mode_supported
from app.ops.pgcluster import PRIVATE_DIR_MODE, PRIVATE_FILE_MODE
from app.ops.report import Clock, utc_iso, utc_now

try:
    import fcntl
except ImportError:  # Windows: sem trava; ali a importação real é recusada antes
    fcntl = None  # type: ignore[assignment]

IMPORT_SCHEMA = "cartorio_system.ops.offsite_import"
SCHEMA_VERSION = "1.1"
GENERATIONS = "geracoes"
STAGING = ".preparo"
RUN_MARKER = ".cartorio-offsite-run"
RUN_SCHEMA = "cartorio_system.ops.offsite_staging"
# Gerações avaliadas, da mais nova para a mais velha, até achar uma válida.
MAX_EVALUATED = 10
# Entradas de .preparo listadas no relatório (as mais antigas); as contagens vão inteiras.
LISTED_LEFTOVERS = 20
LEFTOVER_STATES = ("orphan", "active", "unproven", "unexpected")

_GENERATION = re.compile(rf"^{STAMP}$")
_WORK = re.compile(rf"^({STAMP})-([0-9a-f]{{8}})$")
_EXIT = {"published": 0, "already_published": 0, "failed": 1, "refused": 2}
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_NEW_FILE = os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW | _CLOEXEC | getattr(os, "O_BINARY", 0)
_READ_FILE = os.O_RDONLY | _NOFOLLOW | getattr(os, "O_NONBLOCK", 0) | _CLOEXEC
_DIR_FLAGS = getattr(os, "O_DIRECTORY", 0) | _NOFOLLOW | _CLOEXEC
# Atravessar um diretório só exige busca (``x``); O_PATH não pede leitura dele.
_SEARCH = getattr(os, "O_PATH", os.O_RDONLY)
_CHUNK = 1024 * 1024
_MAX_MARKER_BYTES = 4096
# Destino que, como configurado, não pode ser usado: recusa (2). Os demais erros de
# sistema de arquivos são falha operacional (1) — nunca todo OSError vira recusa.
_UNUSABLE = frozenset({errno.EACCES, errno.EPERM, errno.EROFS, errno.ENAMETOOLONG})


class OffsiteError(Exception):
    """Interrompe a importação com motivo estável. ``verdict``: ``failed`` (evidência de
    problema na origem ou no destino) ou ``refused`` (configuração ou plataforma)."""

    def __init__(self, verdict: str, reason: str, **facts: object) -> None:
        super().__init__(reason)
        self.verdict = verdict
        self.reason = reason
        self.facts = facts


class _Unfit(Exception):
    """Componente do destino que não é diretório de verdade (``kind``: ``symlink`` ou
    ``not_directory``), caminho com ``..`` (``not_canonical``) ou arquivo lido que não é
    regular (``not_regular``)."""

    def __init__(self, kind: str, part: str) -> None:
        super().__init__(kind)
        self.kind = kind
        self.part = part


class _WalkError(Exception):
    """Erro de sistema ao abrir (``writing=False``) ou criar (``writing=True``) um
    componente do destino. Quem chama decide entre recusa e falha."""

    def __init__(self, error: OSError, part: str, *, writing: bool) -> None:
        super().__init__(part)
        self.error = error
        self.part = part
        self.writing = writing


@dataclass(frozen=True)
class _Dir:
    """Diretório do destino, aberto sem seguir link.

    No POSIX, ``fd`` ancora cada operação feita através dele (``dir_fd``): trocar um
    componente do caminho depois da abertura não muda onde se lê nem onde se escreve.
    Fora do POSIX ``fd`` é ``None`` e vale o caminho, conferido componente a componente
    por ``lstat`` — só a bancada de testes passa por aí, porque lá a importação real é
    recusada antes (``offsite_unsupported_platform``)."""

    path: Path
    fd: int | None

    def _at(self, name: str) -> tuple[str, dict[str, int]]:
        if self.fd is None:
            return str(self.path / name), {}
        return name, {"dir_fd": self.fd}

    def lstat(self, name: str) -> os.stat_result:
        target, at = self._at(name)
        return os.stat(target, follow_symlinks=False, **at)

    def exists(self, name: str) -> bool:
        try:
            self.lstat(name)
        except FileNotFoundError:
            return False
        return True

    def info(self) -> os.stat_result:
        return os.fstat(self.fd) if self.fd is not None else self.path.lstat()

    def writable(self) -> bool:
        if self.fd is None:
            return os.access(self.path, os.W_OK | os.X_OK)
        return os.access(".", os.W_OK | os.X_OK, dir_fd=self.fd)

    def mkdir(self, name: str) -> None:
        target, at = self._at(name)
        os.mkdir(target, PRIVATE_DIR_MODE, **at)

    def make_private(self) -> None:
        """Recém-criado aqui: 0700 mesmo sob umask que tira permissão de grupo ou outros.
        Umask que tira leitura do próprio dono impede reabrir o diretório: recusa."""
        if self.fd is not None:
            os.fchmod(self.fd, PRIVATE_DIR_MODE)

    def child(self, name: str, part: str, *, search: bool, stack: ExitStack) -> _Dir:
        """``name`` aberto sem seguir link. ``search``: só para atravessar ou ler arquivos
        dentro dele (``O_PATH``); sem ele, aberto para leitura (listar, travar, ``fsync``,
        ``fchmod``)."""
        if self.fd is None:
            _require_directory(self.lstat(name), part)
            return _Dir(self.path / name, None)
        try:
            fd = os.open(name, (_SEARCH if search else os.O_RDONLY) | _DIR_FLAGS, dir_fd=self.fd)
        except OSError as exc:
            # Link ou não diretório no instante da abertura: recusa, mesmo que o lstat de
            # agora (corrida) já veja outra coisa — nunca o erro cru.
            if exc.errno == errno.ELOOP:
                raise _Unfit("symlink", part) from exc
            if exc.errno == errno.ENOTDIR:
                _require_directory(self.lstat(name), part)
                raise _Unfit("not_directory", part) from exc
            raise
        stack.callback(os.close, fd)
        _require_directory(os.fstat(fd), part)
        return _Dir(self.path / name, fd)

    def create_file(self, name: str) -> int:
        """Arquivo novo já em 0600: nunca sobrescreve nem segue link."""
        target, at = self._at(name)
        return os.open(target, _NEW_FILE, PRIVATE_FILE_MODE, **at)

    def read_file(self, name: str) -> BinaryIO:
        target, at = self._at(name)
        fd = os.open(target, _READ_FILE, **at)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise _Unfit("not_regular", name)
        return os.fdopen(fd, "rb")

    def unlink(self, name: str) -> None:
        target, at = self._at(name)
        os.unlink(target, **at)

    def rename(self, name: str, other: _Dir, new: str) -> None:
        source, _ = self._at(name)
        target, _ = other._at(new)
        os.rename(source, target, src_dir_fd=self.fd, dst_dir_fd=other.fd)

    def rmtree(self, name: str) -> None:
        target, at = self._at(name)
        shutil.rmtree(target, **at)

    def sync(self) -> None:
        """Persiste as entradas criadas ou renomeadas (diretório aberto para leitura)."""
        if self.fd is not None:
            os.fsync(self.fd)

    def entries(self) -> list[os.DirEntry[str]]:
        with os.scandir(self.fd if self.fd is not None else self.path) as found:
            return list(found)


def _require_directory(info: os.stat_result, part: str) -> None:
    if stat.S_ISLNK(info.st_mode):
        raise _Unfit("symlink", part)
    if not stat.S_ISDIR(info.st_mode):
        raise _Unfit("not_directory", part)


def _step(
    parent: _Dir, name: str, part: str, stack: ExitStack, *, create: bool, search: bool
) -> tuple[_Dir, bool]:
    """Abre ``name`` sob ``parent``; com ``create``, o que falta nasce 0700. Devolve o
    diretório e se ele foi criado agora."""
    try:
        return parent.child(name, part, search=search, stack=stack), False
    except FileNotFoundError as exc:
        if not create:
            raise _WalkError(exc, part, writing=False) from exc
    except OSError as exc:
        raise _WalkError(exc, part, writing=False) from exc
    try:
        parent.mkdir(name)
    except FileExistsError:
        # Criado por outra execução entre a abertura e o mkdir: vale como existente.
        try:
            return parent.child(name, part, search=search, stack=stack), False
        except OSError as exc:
            raise _WalkError(exc, part, writing=False) from exc
    except OSError as exc:
        raise _WalkError(exc, part, writing=True) from exc
    try:
        child = parent.child(name, part, search=False, stack=stack)
        child.make_private()
    except OSError as exc:
        raise _WalkError(exc, part, writing=True) from exc
    return child, True


def _walk(
    destination: Path, stack: ExitStack, *, create: bool, final_search: bool
) -> tuple[_Dir, bool]:
    """O destino aberto a partir da raiz, sem seguir link em nenhum componente. Partes:
    ``ancestor`` para os componentes acima dele, ``root`` para ele."""
    path = destination.absolute()
    if ".." in path.parts:
        raise _Unfit("not_canonical", "root")
    anchor, *names = path.parts
    fd: int | None = None
    if os.name == "posix":
        fd = os.open(anchor, _SEARCH | getattr(os, "O_DIRECTORY", 0) | _CLOEXEC)
        stack.callback(os.close, fd)
    current, created = _Dir(Path(anchor), fd), False
    for index, name in enumerate(names):
        last = index == len(names) - 1
        part = "root" if last else "ancestor"
        search = final_search if last else True
        current, created = _step(current, name, part, stack, create=create, search=search)
    return current, created


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


def _open_copies(destination: Path, stack: ExitStack) -> _Dir:
    """Só leitura: ``geracoes/`` do destino, sem seguir link em nenhum componente. Link,
    arquivo ou ``..`` no caminho levantam ``NotADirectoryError`` — nunca são seguidos;
    os demais ``OSError`` saem como vieram (ausente, sem permissão)."""
    try:
        root, _ = _walk(destination, stack, create=False, final_search=True)
        folder, _ = _step(root, GENERATIONS, GENERATIONS, stack, create=False, search=False)
    except _Unfit as exc:
        raise NotADirectoryError(exc.part) from None
    except _WalkError as exc:
        raise exc.error from None
    return folder


def _scan_generations(folder: _Dir) -> Generations:
    stamps: list[str] = []
    ignored = 0
    for entry in folder.entries():
        if _GENERATION.match(entry.name) and entry.is_dir(follow_symlinks=False):
            stamps.append(entry.name)
        else:
            ignored += 1
    return Generations(sorted(stamps, reverse=True), ignored)


def list_generations(destination: Path) -> Generations:
    """Só diretórios de verdade com nome de carimbo, dentro de ``geracoes/``. O preparo
    fica fora dessa pasta: nenhum leitor o enxerga."""
    with ExitStack() as stack:
        return _scan_generations(_open_copies(destination, stack))


def _evaluate_generation(
    folder: _Dir, stamp: str, now: datetime, expected_database: str | None
) -> Evaluation:
    with ExitStack() as stack:
        try:
            generation = folder.child(stamp, GENERATIONS, search=True, stack=stack)
        except _Unfit:
            return Evaluation(stamp, "invalid", "reference_outside_dir")
        except FileNotFoundError:
            return Evaluation(stamp, "unavailable", "manifest_missing")
        except PermissionError:
            return Evaluation(stamp, "unreadable", "manifest_unreadable")
        return evaluate_publication(
            generation.path, stamp, now, expected_database, dir_fd=generation.fd
        )


def read_copies(destination: Path, expected_database: str | None, now: datetime) -> CopyState:
    """A geração mais nova e a última válida (podem ser a mesma), com o mesmo juízo da
    origem: manifesto, referência confinada, tamanho, digest, ponto de recuperação, banco."""
    with ExitStack() as stack:
        folder = _open_copies(destination, stack)
        generations = _scan_generations(folder)
        latest: Evaluation | None = None
        last_valid: Evaluation | None = None
        invalid_newer = 0
        for stamp in generations.stamps[:MAX_EVALUATED]:
            evaluation = _evaluate_generation(folder, stamp, now, expected_database)
            if latest is None:
                latest = evaluation
            if evaluation.state == "valid" and evaluation.recovery_point is not None:
                last_valid = evaluation
                break
            invalid_newer += 1
    return CopyState(generations, latest, last_valid, invalid_newer)


def _io_facts(exc: OSError) -> dict[str, object]:
    return {
        "error_class": type(exc).__name__,
        "errno": errno.errorcode.get(exc.errno) if exc.errno is not None else None,
    }


def _usable(directory: _Dir, part: str) -> None:
    """Diretório existente é usado como está — modo, dono e conteúdo — se for do mesmo
    dono, sem escrita de grupo ou outros e gravável. Conferido no próprio diretório
    aberto (``fstat``), não no caminho."""
    info = directory.info()
    mode = f"{stat.S_IMODE(info.st_mode):04o}"
    if os.name == "posix":
        if info.st_uid != os.geteuid():
            raise OffsiteError("refused", "destination_not_owned", part=part, mode=mode)
        if info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise OffsiteError("refused", "destination_writable_by_others", part=part, mode=mode)
    if not directory.writable():
        raise OffsiteError("refused", "destination_not_writable", part=part, mode=mode)


def _destination_dir(open_dir: Callable[[], tuple[_Dir, bool]], part: str) -> tuple[_Dir, bool]:
    """Abre (ou cria) um diretório do destino e o confere. Contrato recusa × falha:

    - recusa (2): link, não diretório ou ``..`` no caminho; dono, modo ou escrita
      impróprios; erro de permissão, sistema só de leitura ou nome longo demais
      (``destination_unusable``) — o destino, como configurado, não serve;
    - falha (1): qualquer outro erro do sistema de arquivos — ``destination_write_failed``
      ao criar, ``io_error`` ao abrir. Nada é presumido recusa só por ser ``OSError``."""
    try:
        directory, created = open_dir()
    except _Unfit as exc:
        raise OffsiteError("refused", f"destination_{exc.kind}", part=exc.part) from exc
    except _WalkError as exc:
        facts = {"part": exc.part, **_io_facts(exc.error)}
        if exc.error.errno in _UNUSABLE:
            raise OffsiteError("refused", "destination_unusable", **facts) from exc.error
        reason = "destination_write_failed" if exc.writing else "io_error"
        raise OffsiteError("failed", reason, **facts) from exc.error
    _usable(directory, part)
    return directory, created


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


def _copy_into(source: BinaryIO, work: _Dir, name: str) -> None:
    """Arquivo novo já em 0600 (nunca sobrescreve), gravado em disco antes de fechar."""
    with os.fdopen(work.create_file(name), "wb") as handle:
        shutil.copyfileobj(source, handle, _CHUNK)
        handle.flush()
        os.fsync(handle.fileno())


def _write_into(work: _Dir, name: str, data: bytes) -> None:
    with os.fdopen(work.create_file(name), "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _stage(source: Path, work: _Dir, stamp: str, manifest_raw: bytes) -> None:
    dump = f"backup-{stamp}.dump"
    try:
        handle = (source / dump).open("rb")
    except OSError as exc:
        raise OffsiteError("failed", "source_unreadable", **_io_facts(exc)) from exc
    try:
        with handle:
            _copy_into(handle, work, dump)
        _write_into(work, f"backup-{stamp}.json", manifest_raw)
    except OSError as exc:
        raise OffsiteError("failed", "destination_write_failed", **_io_facts(exc)) from exc


def _same_as_published(
    generations: _Dir, stamp: str, manifest_raw: bytes, digest: str, now: datetime, expected: str
) -> None:
    """Já existe geração com este carimbo: idêntica é a mesma cópia (idempotente); com
    outro conteúdo, ou inválida, é colisão — e nada nela é tocado."""
    with ExitStack() as stack:
        try:
            final = generations.child(stamp, GENERATIONS, search=True, stack=stack)
        except _Unfit as exc:
            collision = OffsiteError("failed", "generation_collision", existing="not_a_generation")
            raise collision from exc
        existing = evaluate_publication(final.path, stamp, now, expected, dir_fd=final.fd)
        if existing.state != "valid":
            raise OffsiteError("failed", "generation_collision", existing=existing.reason)
        try:
            with final.read_file(f"backup-{stamp}.json") as handle:
                same_manifest = handle.read() == manifest_raw
        except (OSError, _Unfit):
            same_manifest = False
    if not same_manifest or existing.facts.get("sha256") != digest:
        raise OffsiteError("failed", "generation_collision", existing="different_content")


def _promote(staging: _Dir, name: str, generations: _Dir, stamp: str) -> bool:
    """``rename`` do diretório inteiro. ``False`` se o destino já existe — outra execução
    publicou o mesmo carimbo durante o preparo; quem chama compara o conteúdo."""
    if generations.exists(stamp):
        return False
    try:
        staging.rename(name, generations, stamp)
    except OSError as exc:
        if generations.exists(stamp):
            return False
        raise OffsiteError("failed", "promotion_failed", **_io_facts(exc)) from exc
    return True


def _remove_own(staging: _Dir, name: str) -> bool:
    """Remove só o preparo desta execução (nome com sufixo aleatório próprio). Depois da
    promoção ele já não existe: virou a geração."""
    try:
        if not staging.exists(name):
            return True
        staging.rmtree(name)
    except OSError:
        return False
    return True


def _isolation(work: _Dir, stamp: str) -> dict[str, Any] | None:
    """Modos da geração promovida, lidos pelo diretório aberto (é o mesmo, renomeado)."""
    if os.name != "posix":
        return None
    files = [work.lstat(f"backup-{stamp}.{ext}") for ext in ("dump", "json")]
    return {
        "generation_dir": f"{stat.S_IMODE(work.info().st_mode):04o}",
        "files": [f"{stat.S_IMODE(info.st_mode):04o}" for info in files],
    }


# ---------------------------------------------------------------------------
# Preparo: trava, marcador e inventário das sobras
# ---------------------------------------------------------------------------


def _try_lock(directory: _Dir) -> str:
    """``locked`` (trava obtida: nenhum processo vivo a segura), ``held`` (outro processo
    a segura agora) ou ``unknown`` (sem trava nesta plataforma ou sistema de arquivos)."""
    if fcntl is None or directory.fd is None:
        return "unknown"
    try:
        fcntl.flock(directory.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return "held"
    except OSError:
        return "unknown"
    return "locked"


def _host_token() -> str | None:
    """Esta máquina neste boot, resumida (``machine-id`` + ``boot_id``, nunca no relatório).
    A trava só prova algo entre processos do mesmo kernel: num destino compartilhado por
    rede, outra máquina poderia segurá-la sem que este processo veja. Sem os dois (fora
    do Linux, contêiner sem ``machine-id``), não há prova — e nenhuma sobra vira órfã."""
    try:
        machine = Path("/etc/machine-id").read_bytes().strip()
        boot = Path("/proc/sys/kernel/random/boot_id").read_bytes().strip()
    except OSError:
        return None
    if not machine or not boot:
        return None
    return hashlib.sha256(machine + b"\0" + boot).hexdigest()[:32]


def _claim(work: _Dir, name: str, now: datetime) -> None:
    """Trava o próprio preparo pela vida do processo e, só com a trava obtida e a máquina
    identificada, grava o marcador. Sem os dois, nada de marcador: a sobra nunca vira
    ``orphan``."""
    host = _host_token()
    if host is None or _try_lock(work) != "locked":
        return
    match = _WORK.match(name)
    if match is None:  # o nome é gerado aqui; nunca acontece
        return
    marker = {
        "schema": RUN_SCHEMA,
        "schema_version": "1.0",
        "stamp": match.group(1),
        "run": match.group(2),
        "host": host,
        "started_at": utc_iso(now),
    }
    _write_into(work, RUN_MARKER, json.dumps(marker).encode("ascii"))


def _open_work(staging: _Dir, name: str, now: datetime, stack: ExitStack) -> _Dir:
    """O preparo recém-criado desta execução, aberto, privado, travado e marcado."""
    try:
        work = staging.child(name, STAGING, search=False, stack=stack)
        work.make_private()
        _claim(work, name, now)
    except OSError as exc:
        raise OffsiteError("failed", "destination_write_failed", **_io_facts(exc)) from exc
    except _Unfit as exc:  # trocado por link entre o mkdir e a abertura
        raise OffsiteError("failed", "destination_write_failed", part=STAGING) from exc
    return work


def _marker_start(directory: _Dir, match: re.Match[str]) -> datetime | None:
    """Início gravado pelo marcador, se ele for desta implementação, coerente com o nome e
    escrito nesta máquina neste boot — só aí a trava livre prova que o escritor morreu."""
    host = _host_token()
    if host is None:
        return None
    try:
        with directory.read_file(RUN_MARKER) as handle:
            raw = handle.read(_MAX_MARKER_BYTES + 1)
        marker = json.loads(raw) if len(raw) <= _MAX_MARKER_BYTES else None
    except (OSError, ValueError, _Unfit):
        return None
    if not isinstance(marker, dict) or marker.get("schema") != RUN_SCHEMA:
        return None
    if (marker.get("stamp"), marker.get("run")) != (match.group(1), match.group(2)):
        return None
    if marker.get("host") != host:
        return None
    started = marker.get("started_at")
    if not isinstance(started, str):
        return None
    try:
        moment = datetime.fromisoformat(started.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else None  # sem fuso não se compara


def _not_private(info: os.stat_result) -> bool:
    """Link, de outro dono ou gravável por grupo ou outros (dono e modo só no POSIX)."""
    if stat.S_ISLNK(info.st_mode):
        return True
    if os.name != "posix":
        return False
    return info.st_uid != os.geteuid() or bool(info.st_mode & (stat.S_IWGRP | stat.S_IWOTH))


def _same_entry(a: os.stat_result, b: os.stat_result) -> bool:
    return (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino)


def _hours(now: datetime, then: datetime) -> float:
    return round((now - then).total_seconds() / 3600, 2)


def _mtime_hours(now: datetime, mtime: float) -> float | None:
    """Idade pela modificação; ``None`` se o sistema de arquivos guarda um instante que o
    Python não representa — uma sobra estranha nunca derruba a importação."""
    try:
        return _hours(now, datetime.fromtimestamp(mtime, tz=now.tzinfo))
    except (OverflowError, OSError, ValueError):
        return None


def _leftover(staging: _Dir, name: str, now: datetime, *, remove: bool) -> dict[str, Any] | None:
    """Uma entrada de ``.preparo/`` que não é desta execução. Provas, nesta ordem, antes
    de abrir qualquer coisa: nome do formato, diretório de verdade, do mesmo dono e sem
    escrita de grupo ou outros. Aberto sem seguir link, precisa ser o mesmo que o
    ``lstat`` viu; trava presa é ``active``; trava livre sem marcador coerente é
    ``unproven``. Só ``orphan`` pode sair — com ``remove``, ainda com a trava, e se o nome
    continuar apontando para o mesmo diretório. ``None``: sumiu durante o inventário."""
    match = _WORK.match(name)
    if match is None:
        return {"state": "unexpected"}  # nome alheio: nem ecoado
    found: dict[str, Any] = {"name": name}
    try:
        info = staging.lstat(name)
    except FileNotFoundError:
        return None
    except OSError:
        return found | {"state": "unproven", "age_hours": None}
    found["age_hours"] = _mtime_hours(now, info.st_mtime)
    if not stat.S_ISDIR(info.st_mode) or _not_private(info):
        return found | {"state": "unexpected"}
    with ExitStack() as stack:
        try:
            entry = staging.child(name, STAGING, search=False, stack=stack)
        except FileNotFoundError:
            return None
        except (OSError, _Unfit):
            return found | {"state": "unproven"}
        if not _same_entry(entry.info(), info):
            return found | {"state": "unproven"}
        lock = _try_lock(entry)
        if lock == "held":
            return found | {"state": "active"}
        started = _marker_start(entry, match) if lock == "locked" else None
        if started is None:
            return found | {"state": "unproven"}
        found |= {"state": "orphan", "age_hours": _hours(now, started)}
        if not remove:
            return found
        try:
            if not _same_entry(staging.lstat(name), info):
                return found | {"removal": "failed"}
            staging.rmtree(name)
        except OSError:
            return found | {"removal": "failed"}
        return found | {"removal": "removed"}


def _inspect_staging(
    root: _Dir, now: datetime, *, remove: bool, stack: ExitStack
) -> dict[str, Any] | None:
    """Inventário de ``.preparo/`` (sem criá-lo). ``None`` quando ele não pode ser lido
    com segurança (link, não diretório, de outro dono, aberto a grupo ou outros) — nesse
    caso nada nele é aberto, e a importação recusa ``.preparo`` se precisar dele."""
    try:
        staging = root.child(STAGING, STAGING, search=False, stack=stack)
    except FileNotFoundError:
        return _leftover_summary([])
    except (OSError, _Unfit):
        return None
    if _not_private(staging.info()):
        return None
    try:
        names = [entry.name for entry in staging.entries()]
    except OSError:
        return None
    found = [_leftover(staging, name, now, remove=remove) for name in names]
    return _leftover_summary([item for item in found if item is not None])


def _leftover_summary(found: list[dict[str, Any]]) -> dict[str, Any]:
    counts = dict.fromkeys(LEFTOVER_STATES, 0)
    for item in found:
        counts[item["state"]] += 1
    named = [item for item in found if "name" in item]
    named.sort(key=lambda item: -(item.get("age_hours") or 0.0))
    return {
        "counts": counts,
        "entries": named[:LISTED_LEFTOVERS],
        "removed": sum(1 for item in found if item.get("removal") == "removed"),
        "removal_failed": sum(1 for item in found if item.get("removal") == "failed"),
    }


# ---------------------------------------------------------------------------
# Importação
# ---------------------------------------------------------------------------


def _import(
    source: Path,
    destination: Path,
    expected: str,
    now: datetime,
    stamp: str | None,
    platform: str,
    report: dict[str, Any],
    remove_orphans: bool,
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

    with ExitStack() as stack:
        root, created = _destination_dir(
            lambda: _walk(destination, stack, create=True, final_search=False), "root"
        )
        report["destination"]["root"] = "created" if created else "existing"
        generations, _ = _destination_dir(
            lambda: _step(root, GENERATIONS, GENERATIONS, stack, create=True, search=False),
            GENERATIONS,
        )
        report["destination"]["generation"] = stamp
        report["staging"]["leftovers"] = _inspect_staging(
            root, now, remove=remove_orphans, stack=stack
        )
        if generations.exists(stamp):
            _same_as_published(generations, stamp, manifest_raw, digest, now, expected)
            return "already_published"

        staging, _ = _destination_dir(
            lambda: _step(root, STAGING, STAGING, stack, create=True, search=False), STAGING
        )
        name = f"{stamp}-{secrets.token_hex(4)}"
        try:
            staging.mkdir(name)
        except OSError as exc:
            raise OffsiteError("failed", "destination_write_failed", **_io_facts(exc)) from exc
        report["staging"]["used"] = True
        try:
            work = _open_work(staging, name, now, stack)
            _stage(source, work, stamp, manifest_raw)
            staged = evaluate_publication(staging.path / name, stamp, now, expected, dir_fd=work.fd)
            if staged.state != "valid":
                raise OffsiteError("failed", "staged_copy_invalid", staged=staged.reason)
            if staged.facts.get("sha256") != digest:
                raise OffsiteError("failed", "source_changed_during_copy")
            # A geração publicada tem só o par: o marcador sai antes da promoção, e a
            # trava segue presa até o fim (sem marcador, a sobra nunca é ``orphan``).
            if work.exists(RUN_MARKER):
                work.unlink(RUN_MARKER)
            work.sync()
            if not _promote(staging, name, generations, stamp):
                _same_as_published(generations, stamp, manifest_raw, digest, now, expected)
                return "already_published"
            generations.sync()
            report["destination"]["isolation"] = _isolation(work, stamp)
            return "published"
        finally:
            report["staging"]["removed"] = _remove_own(staging, name)


def run_import(
    source: Path,
    destination: Path,
    expected_database: str,
    *,
    now: datetime,
    stamp: str | None = None,
    platform: str = sys.platform,
    remove_orphan_staging: bool = False,
) -> dict[str, Any]:
    """Importa a publicação mais recente (ou ``stamp``) e devolve o relatório
    ``cartorio_system.ops.offsite_import`` 1.1 — sem caminho e sem nome de banco."""
    report: dict[str, Any] = {
        "schema": IMPORT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "started_at": utc_iso(now),
        "verdict": "failed",
        "reason": "not_finished",
        "source": {"stamp": stamp},
        "destination": {},
        "staging": {"used": False, "removed": None, "leftovers": None},
    }
    try:
        outcome = _import(
            source,
            destination,
            expected_database,
            now,
            stamp,
            platform,
            report,
            remove_orphan_staging,
        )
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
    Só leitura, e o leitor nunca segue link em nenhum componente do caminho."""
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
        "--destination",
        type=Path,
        required=True,
        help="raiz privada das cópias externas (caminho canônico: sem link nem '..')",
    )
    parser.add_argument(
        "--expected-database",
        required=True,
        help="banco de que a cópia precisa ser (configuração à parte, nunca do manifesto)",
    )
    parser.add_argument("--stamp", help="importa esta publicação (AAAAMMDDTHHMMSSZ)")
    parser.add_argument(
        "--remove-orphan-staging",
        action="store_true",
        help=(
            "remove de .preparo/ só o preparo comprovadamente órfão (marcador desta "
            "implementação e trava livre); o resto é só relatado"
        ),
    )
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
        remove_orphan_staging=args.remove_orphan_staging,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(report["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
