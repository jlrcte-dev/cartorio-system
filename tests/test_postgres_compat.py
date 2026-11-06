"""Compatibilidade PostgreSQL da Fase B de homologação.

Os testes que precisam de conexão real (marcados `_requires_real_postgres`) exigem
`CARTORIO_TEST_POSTGRES_URL` apontando para a bancada descartável conhecida desta
Fase B -- usuário e banco precisam casar exatamente com `_EXPECTED_BANCADA_USER` /
`_EXPECTED_BANCADA_DBNAME`. Isso é deliberado: "estar vazio" não é suficiente para
provar que um banco é o nosso, então a restrição é por identidade, não por estado.
Sem a variável, esses casos são pulados -- não entram no gate padrão (`pytest`), que
continua só contra SQLite. Com a variável definida, identidade errada, esquema de
URL inválido ou driver ausente são falha explícita, nunca skip silencioso: quem
definiu a variável pediu este teste.

Dentro da bancada (já restrita por identidade), cada execução cria um schema
PostgreSQL próprio, com nome único por sessão de teste, migra só dentro dele, e
descarta exatamente esse schema ao final -- nunca `public`, nunca o banco inteiro.
Isso limita o que qualquer execução pode apagar ao que ela mesma criou, mesmo que a
bancada venha a ter outro conteúdo coexistindo (de uma execução anterior que tenha
falhado em limpar, por exemplo).

Os testes de validação de URL (`test_require_postgres_url_*`) são puros -- não abrem
conexão nenhuma -- e por isso sempre rodam, mesmo no gate padrão sem Postgres.

Nenhum dado real: tudo aqui é sintético.
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote, urlsplit

import httpx
import pytest

POSTGRES_URL = os.environ.get("CARTORIO_TEST_POSTGRES_URL")

# Identidade da bancada descartável desta Fase B. Não é configurável por env var de
# propósito: a restrição é "exatamente esta bancada conhecida", não "qualquer coisa
# que o operador decida apontar hoje".
_EXPECTED_BANCADA_USER = "cartorio_fase_b"
_EXPECTED_BANCADA_DBNAME = "cartorio_fase_b_test"

_requires_real_postgres = pytest.mark.skipif(
    POSTGRES_URL is None,
    reason=("requer CARTORIO_TEST_POSTGRES_URL (bancada descartável conhecida desta Fase B)"),
)

REPO_ROOT = Path(__file__).resolve().parent.parent

_DSN_SECRET_RE = re.compile(r"://([^:/@\s]+):([^@/\s]+)@")


def _sanitize(text: str) -> str:
    """Redige credenciais de DSN antes de incluir texto em evidência/mensagem de falha."""
    return _DSN_SECRET_RE.sub(r"://\1:***@", text)


def _require_postgres_url(url: str | None) -> str:
    """Recusa qualquer alvo que não seja, por identidade, a bancada descartável
    conhecida desta Fase B. Validação pura, sem conexão: roda sempre, mesmo sem
    bancada. "Estar vazio" nunca é suficiente aqui -- só identidade."""
    if not url:
        raise RuntimeError("CARTORIO_TEST_POSTGRES_URL não definida.")
    if url.startswith("sqlite"):
        raise RuntimeError(
            f"CARTORIO_TEST_POSTGRES_URL precisa ser PostgreSQL; recebeu SQLite: {_sanitize(url)}"
        )
    if not (url.startswith("postgresql://") or url.startswith("postgresql+psycopg://")):
        raise RuntimeError(
            f"CARTORIO_TEST_POSTGRES_URL com esquema não suportado: {_sanitize(url)}"
        )

    parsed = urlsplit(url)
    dbname = parsed.path.lstrip("/")
    if parsed.username != _EXPECTED_BANCADA_USER or dbname != _EXPECTED_BANCADA_DBNAME:
        raise RuntimeError(
            "CARTORIO_TEST_POSTGRES_URL não aponta para a bancada descartável "
            f"conhecida desta Fase B (esperado usuário={_EXPECTED_BANCADA_USER!r}, "
            f"banco={_EXPECTED_BANCADA_DBNAME!r}; recebeu "
            f"usuário={parsed.username!r}, banco={dbname!r}). Estar vazio não basta "
            "-- precisa ser exatamente esta bancada."
        )
    return url


def _psycopg_conninfo(url: str) -> str:
    """psycopg.connect() só entende o esquema libpq puro, sem o `+psycopg` do SQLAlchemy."""
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _scoped_url(base_url: str, schema: str) -> str:
    """URL da mesma bancada, mas com `search_path` fixado no schema exclusivo desta
    execução -- Alembic, o app e os INSERTs diretos passam a resolver tabelas sem
    qualificação (`financial_entries`, não `esquema.financial_entries`) contra esse
    schema, nunca contra `public`."""
    separator = "&" if "?" in base_url else "?"
    options = quote(f"-c search_path={schema}", safe="")
    return f"{base_url}{separator}options={options}"


def _create_schema(base_url: str, schema: str) -> None:
    import psycopg
    from psycopg import sql

    with psycopg.connect(_psycopg_conninfo(base_url)) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))


def _drop_schema(base_url: str, schema: str) -> None:
    """Descarta exatamente o schema desta execução -- nunca `public`, nunca o
    banco inteiro. Idempotente: seguro mesmo se o schema nunca tiver sido criado."""
    import psycopg
    from psycopg import sql

    with psycopg.connect(_psycopg_conninfo(base_url)) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))


def _run_alembic(
    *args: str, database_url: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"alembic {' '.join(args)} falhou (exit {result.returncode}):\n"
            f"{_sanitize(result.stdout + result.stderr)}"
        )
    return result


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def postgres_db() -> Iterator[str]:
    """Schema PostgreSQL exclusivo desta sessão de testes, dentro da bancada
    descartável conhecida.

    Recusa prosseguir se a URL não apontar, por identidade, para a bancada
    conhecida (nunca por "estar vazio"). Cria um schema com nome único, migra só
    nele, e sempre o descarta no `finally` -- inclusive se o setup ou qualquer
    teste (incluindo o smoke HTTP) falhar. Nunca toca em `public` ou em qualquer
    outro schema que porventura já exista na bancada.
    """
    base_url = _require_postgres_url(POSTGRES_URL)
    schema = f"fase_b_test_{uuid.uuid4().hex[:12]}"
    scoped_url = _scoped_url(base_url, schema)

    _create_schema(base_url, schema)
    try:
        _run_alembic("upgrade", "head", database_url=scoped_url)
    except Exception:
        _drop_schema(base_url, schema)
        raise
    try:
        yield scoped_url
    finally:
        _drop_schema(base_url, schema)


def test_require_postgres_url_rejects_sqlite() -> None:
    with pytest.raises(RuntimeError, match="SQLite"):
        _require_postgres_url("sqlite:///./cartorio.db")


def test_require_postgres_url_rejects_unsupported_scheme() -> None:
    with pytest.raises(RuntimeError, match="esquema não suportado"):
        _require_postgres_url("mysql://user:pass@host/db")


def test_require_postgres_url_rejects_empty() -> None:
    with pytest.raises(RuntimeError, match="não definida"):
        _require_postgres_url(None)


def test_require_postgres_url_rejects_wrong_identity() -> None:
    """Um banco vazio, mas com usuário/nome diferentes da bancada conhecida, é
    recusado -- "vazio" nunca foi, nem deveria ser, suficiente."""
    with pytest.raises(RuntimeError, match="bancada descartável conhecida"):
        _require_postgres_url("postgresql://outro_usuario:senha@127.0.0.1:5432/outro_banco")


@_requires_real_postgres
def test_alembic_upgrade_head_on_empty_postgres(postgres_db: str) -> None:
    """A fixture já aplicou `upgrade head` no schema exclusivo desta sessão;
    aqui confirmamos que o resultado é, de fato, a head esperada."""
    current = _run_alembic("current", database_url=postgres_db)
    assert "f4a5b6c7d8e9" in current.stdout + current.stderr


@_requires_real_postgres
def test_alembic_check_reports_no_drift(postgres_db: str) -> None:
    """`alembic check` roda sozinho no schema recém-criado pela fixture, sem drift."""
    result = _run_alembic("check", database_url=postgres_db)
    assert "No new upgrade operations detected." in result.stdout + result.stderr


@_requires_real_postgres
def test_alembic_tolerates_percent_in_url(postgres_db: str) -> None:
    """Regressão do bug de interpolação do ConfigParser.

    `config.set_main_option`/`get_section` interpolavam "%" -- uma URL real com esse
    caractere (comum em senha/host percent-encoded) quebrava `alembic/env.py` antes
    desta Fase B. O valor abaixo decodifica para um "%" literal na querystring: uma
    URL sintética, no sentido do diagnóstico original, não uma credencial real.
    """
    separator = "&" if "?" in postgres_db else "?"
    synthetic_url = f"{postgres_db}{separator}application_name=fase-b%25literal"
    result = _run_alembic("current", database_url=synthetic_url)
    assert "f4a5b6c7d8e9" in result.stdout + result.stderr


@_requires_real_postgres
def test_boolean_defaults_resolve_to_false_on_insert(postgres_db: str) -> None:
    """As 5 colunas Boolean com DEFAULT (`false`, não `0`) resolvem no INSERT real.

    `retention_rules` (4 colunas) e `compliance_requirement_statuses.human_review_required`
    (a 5a, via a linha-pai obrigatória em `compliance_requirements`). Tudo numa
    transação revertida ao final -- nada fica no schema, mesmo além do que a
    fixture já descarta.
    """
    import psycopg

    suffix = uuid.uuid4().hex[:8]
    with psycopg.connect(_psycopg_conninfo(postgres_db)) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO retention_rules
                    (codigo, assunto, documento, fase_corrente_text, fase_corrente_kind,
                     source_norm, source_version, source_file, source_code)
                VALUES (%s, 'assunto teste', 'documento teste', '5 anos', 'DURATION',
                        'norma-teste', 'v1', 'arquivo-teste', 'COD-01')
                RETURNING eliminacao, guarda_permanente, requer_microfilmagem, requer_digitalizacao
                """,
                (f"TEST-RR-{suffix}",),
            )
            assert cur.fetchone() == (False, False, False, False)

            cur.execute(
                """
                INSERT INTO compliance_requirements
                    (code, source, article_label, article_text, classification, stage)
                VALUES (%s, 'LGPD', 'Art. teste', 'texto sintetico de teste',
                        'OBRIGATORIO_LGPD', 'ETAPA_1')
                RETURNING id
                """,
                (f"TEST-REQ-{suffix}",),
            )
            (requirement_id,) = cur.fetchone()

            cur.execute(
                """
                INSERT INTO compliance_requirement_statuses
                    (requirement_id, status, computed_at)
                VALUES (%s, 'EVIDENCE_PENDING', now())
                RETURNING human_review_required
                """,
                (requirement_id,),
            )
            assert cur.fetchone() == (False,)
        conn.rollback()


@_requires_real_postgres
def test_api_write_and_read_against_postgres(postgres_db: str, tmp_path: Path) -> None:
    """Escrita e leitura reais pela API HTTP, com o processo apontando para o
    schema exclusivo desta sessão.

    Saída do Uvicorn vai para arquivo temporário (nunca `PIPE`, que pode travar sob
    buffer cheio); `httpx.Client(trust_env=False)` ignora proxy de ambiente; o
    processo é sempre encerrado no `finally`, com timeout e kill forçado se preciso.
    """
    port = _free_port()
    env = os.environ.copy()
    env["DATABASE_URL"] = postgres_db
    env["APP_NAME"] = "Cartorio System - Fase B Postgres (teste)"
    env["DEBUG"] = "false"
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    log_path = tmp_path / "uvicorn.log"
    base = f"http://127.0.0.1:{port}/api/v1"

    with log_path.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=REPO_ROOT,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
    try:
        with httpx.Client(trust_env=False, timeout=5) as client:
            health = None
            for _ in range(50):
                if process.poll() is not None:
                    pytest.fail(
                        f"uvicorn encerrou sozinho (exit {process.returncode}):\n"
                        f"{_sanitize(log_path.read_text(encoding='utf-8'))}"
                    )
                try:
                    health = client.get(f"{base}/health").json()
                    break
                except httpx.TransportError:
                    time.sleep(0.2)
            assert health is not None, _sanitize(log_path.read_text(encoding="utf-8"))
            assert health["app"] == "Cartorio System - Fase B Postgres (teste)"

            code = f"PGTEST-{uuid.uuid4().hex[:12]}"
            created = client.post(
                f"{base}/audit/findings",
                json={
                    "finding_code": code,
                    "title": f"Teste sintetico {code}",
                    "description": "Registro ficticio da Fase B (PostgreSQL).",
                    "category": "SYSTEM",
                    "origin": "MANUAL",
                    "severity": "LOW",
                    "probability": "LOW",
                    "impact": "LOW",
                    "priority": "BACKLOG",
                    "evidence_summary": "Teste automatizado de compatibilidade.",
                    "recommended_action": "Nenhuma -- registro de teste.",
                },
            )
            assert created.status_code == 201, _sanitize(created.text)
            finding_id = created.json()["id"]

            fetched = client.get(f"{base}/audit/findings/{finding_id}").json()
            assert fetched["finding_code"] == code
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
