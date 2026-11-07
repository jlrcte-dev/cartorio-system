"""Cluster PostgreSQL descartável para as provas de bancada (CARTORIO-OPS-1).

Cada cluster nasce num diretório criado pelo próprio ensaio (``initdb``), escuta só em
``127.0.0.1`` numa porta livre, sem socket Unix, com ``pg_hba`` restrito a
``127.0.0.1/32`` e senhas geradas na hora. Antes de qualquer escrita, a identidade é
COMPROVADA, não presumida: o servidor que responde na porta precisa ler, do próprio
diretório de dados (``pg_read_file``), o token que o ensaio plantou ali, e reportar o
``cluster_name``, a porta e o ``listen_addresses`` que o ensaio definiu. "Estar vazio"
nunca é prova — mesma regra da suíte do PR #5.

Limpeza com escopo: só se remove diretório que carrega o marcador desta execução.
"""

from __future__ import annotations

import contextlib
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import psycopg

LOOPBACK = "127.0.0.1"
SUPERUSER = "drill_super"
IDENTITY_FILE = "cartorio_ops_identity"
WORK_MARKER = ".cartorio-ops-drill"

# Variáveis libpq que redirecionam ou alteram a conexão mesmo com host, porta, banco e
# usuário explícitos — mesma proteção da suíte do PR #5, ampliada para o ensaio.
FORBIDDEN_LIBPQ_ENV = ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS")

_VERSION = re.compile(r"\(PostgreSQL\)\s+(\d+)(?:\.(\d+))?")


class DrillRefused(Exception):
    """Alvo ou ambiente sem garantia: o ensaio não começa (ou não continua)."""

    def __init__(self, reason: str, **facts: object) -> None:
        super().__init__(reason)
        self.reason = reason
        self.facts = facts


class DrillFailed(Exception):
    """Uma verificação do ensaio falhou."""

    def __init__(self, reason: str, **facts: object) -> None:
        super().__init__(reason)
        self.reason = reason
        self.facts = facts


def require_clean_libpq_env(environ: Mapping[str, str]) -> None:
    offending = sorted(name for name in FORBIDDEN_LIBPQ_ENV if environ.get(name))
    if offending:
        raise DrillRefused("libpq_env_override", variables=offending)


def subprocess_env(base: Mapping[str, str], **extra: str) -> dict[str, str]:
    """Ambiente dos subprocessos: sem nenhuma ``PG*`` nem ``DATABASE_URL`` herdada."""
    env = {
        key: value
        for key, value in base.items()
        if not key.upper().startswith("PG") and key.upper() != "DATABASE_URL"
    }
    env.update(extra)
    return env


def require_loopback(host: str) -> None:
    if host != LOOPBACK:
        raise DrillRefused("target_not_local", host_class="external")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((LOOPBACK, 0))
        return int(sock.getsockname()[1])


def pg_binary(pg_bin: Path, name: str) -> Path:
    found = shutil.which(name, path=str(pg_bin))
    if found is None:
        raise DrillRefused("pg_binary_missing", binary=name)
    return Path(found)


def tool_version(binary: Path) -> tuple[str, int]:
    proc = subprocess.run(
        [str(binary), "--version"],
        capture_output=True,
        text=True,
        timeout=30,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    match = _VERSION.search(proc.stdout)
    if proc.returncode != 0 or match is None:
        raise DrillRefused("pg_binary_unusable", binary=binary.name)
    version = match.group(1) + (f".{match.group(2)}" if match.group(2) else "")
    return version, int(match.group(1))


def verify_identity(
    *, cluster_name: str, token: str, port: int, observed: Mapping[str, Any]
) -> None:
    """Puro: compara o que o servidor reportou com o que o ensaio criou."""
    if observed.get("listen_addresses") != LOOPBACK:
        raise DrillRefused("target_not_isolated")
    if (
        observed.get("cluster_name") != cluster_name
        or str(observed.get("port")) != str(port)
        or observed.get("token") != token
    ):
        raise DrillRefused("target_identity_unproven")


def verify_restore_target(
    *, expected_marker: str, expected_owner: str, observed: Mapping[str, Any]
) -> None:
    """Puro: o banco de destino precisa ter sido criado por ESTA execução e estar vazio."""
    if observed.get("comment") != expected_marker or observed.get("owner") != expected_owner:
        raise DrillRefused("target_not_created_by_this_run")
    if observed.get("user_relations") != 0:
        raise DrillRefused("target_not_empty", user_relations=observed.get("user_relations"))


def ansi_safe(path: Path, platform: str = sys.platform) -> bool:
    """No Windows, initdb/pg_ctl recebem argv na página de código ANSI: um caminho
    não-ASCII pode chegar corrompido ao servidor e quebrar a prova de identidade."""
    return platform != "win32" or str(path).isascii()


def create_work_dir(root: Path, run_id: str) -> Path:
    if not root.is_dir():
        raise DrillRefused("work_root_missing")
    if not ansi_safe(root.resolve()):
        raise DrillRefused("work_root_not_ascii")
    path = root / f"cartorio-ops-drill-{run_id}"
    try:
        path.mkdir()
    except FileExistsError as exc:
        raise DrillRefused("work_dir_reused") from exc
    (path / WORK_MARKER).write_text(run_id, encoding="ascii")
    return path


def remove_work_dir(path: Path, run_id: str) -> bool:
    """Remove só o diretório que carrega o marcador desta execução."""
    marker = path / WORK_MARKER
    try:
        if marker.read_text(encoding="ascii") != run_id:
            return False
    except OSError:
        return False
    for attempt in range(6):
        try:
            shutil.rmtree(path)
            return True
        except OSError:
            # Windows libera handles do postgres com atraso depois do pg_ctl stop.
            time.sleep(0.5 * (attempt + 1))
    return not path.exists()


def run_tool(
    cmd: list[str], *, env: Mapping[str, str], log: Path, timeout: float = 120
) -> subprocess.CompletedProcess[str]:
    """Executa uma ferramenta com saída num arquivo de log — nunca em PIPE: no Windows
    o postgres herdaria o handle e o ``pg_ctl start`` nunca terminaria de ser lido."""
    with log.open("a", encoding="utf-8") as handle:
        handle.write(f"$ {Path(cmd[0]).name} {' '.join(cmd[1:])}\n")
        handle.flush()
        return subprocess.run(
            cmd,
            stdout=handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            env=dict(env),
            timeout=timeout,
            text=True,
            check=False,
        )


@dataclass
class Cluster:
    label: str
    run_id: str
    pg_bin: Path
    root: Path
    port: int = 0
    password: str = ""
    token: str = ""
    # not_started | start_attempted | running | stopped | uncertain. A partir da
    # tentativa de partida o servidor PODE existir (o pg_ctl pode ter estourado o prazo
    # com o postmaster ainda subindo): só a confirmação por `pg_ctl status` volta a
    # garantir que não há processo usando o diretório.
    state: str = "not_started"
    # Ponto único de endereço: toda conexão, URL e ferramenta usa ``address()``.
    host: str = LOOPBACK
    system_identifier: str | None = None
    server_version: str | None = None
    server_major: int | None = None

    def address(self) -> str:
        """O host deste cluster, depois do guarda: nada fora do loopback."""
        require_loopback(self.host)
        return self.host

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def log(self) -> Path:
        return self.root / "tools.log"

    @property
    def cluster_name(self) -> str:
        return f"cartorio_ops_{self.label}_{self.run_id.replace('-', '_').lower()}"

    def initialize(self, env: Mapping[str, str]) -> None:
        self.root.mkdir()
        self.password = secrets.token_urlsafe(24)
        self.token = secrets.token_hex(16)
        self.port = free_port()
        pwfile = self.root / "initdb.pw"
        pwfile.write_text(self.password, encoding="ascii")
        try:
            result = run_tool(
                [
                    str(pg_binary(self.pg_bin, "initdb")),
                    "-D",
                    str(self.data_dir),
                    "-U",
                    SUPERUSER,
                    "--auth=scram-sha-256",
                    f"--pwfile={pwfile}",
                    "--encoding=UTF8",
                    "--locale=C",
                    "--no-sync",
                    "--no-instructions",
                ],
                env=env,
                log=self.log,
            )
        finally:
            pwfile.unlink(missing_ok=True)
        if result.returncode != 0:
            raise DrillFailed("initdb_failed", cluster=self.label, exit_code=result.returncode)
        (self.data_dir / IDENTITY_FILE).write_text(self.token, encoding="ascii")
        with (self.data_dir / "postgresql.conf").open("a", encoding="utf-8") as conf:
            conf.write(
                "\n# cartorio-ops: bancada descartavel (rede so em loopback)\n"
                f"listen_addresses = '{LOOPBACK}'\n"
                f"port = {self.port}\n"
                "unix_socket_directories = ''\n"
                f"cluster_name = '{self.cluster_name}'\n"
                "max_connections = 20\n"
            )
        (self.data_dir / "pg_hba.conf").write_text(
            f"host all all {LOOPBACK}/32 scram-sha-256\n", encoding="utf-8"
        )

    def start(self, env: Mapping[str, str]) -> None:
        self.state = "start_attempted"
        try:
            result = run_tool(
                [
                    str(pg_binary(self.pg_bin, "pg_ctl")),
                    "start",
                    "-D",
                    str(self.data_dir),
                    "-l",
                    str(self.root / "server.log"),
                    "-w",
                    "-t",
                    "90",
                ],
                env=env,
                log=self.log,
                timeout=150,
            )
        except subprocess.TimeoutExpired as exc:
            raise DrillFailed("cluster_start_timeout", cluster=self.label) from exc
        if result.returncode != 0:
            raise DrillFailed("cluster_start_failed", cluster=self.label)
        self.state = "running"

    def server_running(self, env: Mapping[str, str]) -> bool | None:
        """``pg_ctl status`` no diretório desta execução: True rodando, False parado
        (saída 3), None incerto (diretório inacessível, erro ou prazo estourado)."""
        try:
            result = run_tool(
                [str(pg_binary(self.pg_bin, "pg_ctl")), "status", "-D", str(self.data_dir)],
                env=env,
                log=self.log,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if result.returncode == 0:
            return True
        if result.returncode == 3:
            return False
        return None

    def stop(self, env: Mapping[str, str]) -> str:
        """Para e CONFIRMA a parada. Retorna not_started, stopped ou uncertain; só os dois
        primeiros autorizam remover o diretório."""
        if self.state in ("not_started", "stopped"):
            return self.state
        # Quem decide é a confirmação por `pg_ctl status`, não o retorno do stop.
        with contextlib.suppress(OSError, subprocess.TimeoutExpired):
            run_tool(
                [
                    str(pg_binary(self.pg_bin, "pg_ctl")),
                    "stop",
                    "-D",
                    str(self.data_dir),
                    "-m",
                    "fast",
                    "-w",
                    "-t",
                    "90",
                ],
                env=env,
                log=self.log,
                timeout=150,
            )
        self.state = "stopped" if self.server_running(env) is False else "uncertain"
        return self.state

    def connect(
        self, dbname: str = "postgres", user: str = SUPERUSER, password: str | None = None
    ) -> psycopg.Connection[tuple[Any, ...]]:
        host = self.address()  # o guarda vem antes até de importar o driver
        import psycopg

        return psycopg.connect(
            host=host,
            hostaddr=host,
            port=self.port,
            dbname=dbname,
            user=user,
            password=self.password if password is None else password,
            connect_timeout=10,
            autocommit=True,
        )

    def prove_identity(self) -> None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT current_setting('cluster_name'), current_setting('port'),"
                " current_setting('listen_addresses'), pg_read_file(%s),"
                " (pg_control_system()).system_identifier::text,"
                " current_setting('server_version'), current_setting('server_version_num')",
                (IDENTITY_FILE,),
            ).fetchone()
        observed = {
            "cluster_name": row[0],
            "port": row[1],
            "listen_addresses": row[2],
            "token": row[3],
        }
        verify_identity(
            cluster_name=self.cluster_name, token=self.token, port=self.port, observed=observed
        )
        self.system_identifier = row[4]
        self.server_version = row[5]
        self.server_major = int(row[6]) // 10000

    def describe(self) -> dict[str, Any]:
        return {
            "cluster_name": self.cluster_name,
            "system_identifier": self.system_identifier,
            "listen": LOOPBACK,
            "identity_proof": "token_in_data_dir+cluster_name+port+listen_addresses",
        }


# Estados que autorizam remover o diretório de um cluster.
STOPPED_STATES = ("not_started", "stopped")


def stop_all(clusters: list[Cluster], env: Mapping[str, str]) -> dict[str, str]:
    """Dá a ordem de parada a TODOS os clusters; um que quebra vira ``uncertain`` sem
    impedir a parada dos demais."""
    states: dict[str, str] = {}
    for cluster in clusters:
        try:
            states[cluster.label] = cluster.stop(env)
        except Exception:
            states[cluster.label] = "uncertain"
    return states
