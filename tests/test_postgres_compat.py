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
from urllib.parse import parse_qsl, urlsplit

import httpx
import pytest
from sqlalchemy.engine import make_url

POSTGRES_URL = os.environ.get("CARTORIO_TEST_POSTGRES_URL")

# Identidade da bancada descartável desta Fase B. Não é configurável por env var de
# propósito: a restrição é "exatamente esta bancada conhecida", não "qualquer coisa
# que o operador decida apontar hoje".
_EXPECTED_BANCADA_USER = "cartorio_fase_b"
_EXPECTED_BANCADA_DBNAME = "cartorio_fase_b_test"

# Palavras-chave libpq que redirecionam a conexão (host/porta/banco/usuário/perfil
# inteiro via pg_service.conf). Checar só user/dbname na URI principal não basta --
# libpq aceita essas mesmas chaves na querystring, e podem sobrepor o que já foi
# validado ali. Recusar a presença de qualquer uma, não tentar adivinhar qual vale.
_IDENTITY_OVERRIDE_QUERY_KEYS = {"host", "hostaddr", "port", "dbname", "user", "service"}

# PGHOSTADDR e PGSERVICE são perigosos sempre que preenchidas: PGHOSTADDR substitui
# a resolução de host por um IP direto, e PGSERVICE carrega um perfil inteiro de
# ~/.pg_service.conf (host/porta/banco/usuário juntos) -- nenhuma das duas depende
# de a URL ter ou não esse campo. PGHOST e PGPORT só são perigosas quando a URL não
# define host/porta explicitamente; se a URL já tem os dois, eles vencem e a
# variável de ambiente fica inerte.
_ALWAYS_FORBIDDEN_PG_ENV_VARS = ("PGHOSTADDR", "PGSERVICE")

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

    parsed = make_url(url)
    dbname = parsed.database
    if parsed.username != _EXPECTED_BANCADA_USER or dbname != _EXPECTED_BANCADA_DBNAME:
        raise RuntimeError(
            "CARTORIO_TEST_POSTGRES_URL não aponta para a bancada descartável "
            f"conhecida desta Fase B (esperado usuário={_EXPECTED_BANCADA_USER!r}, "
            f"banco={_EXPECTED_BANCADA_DBNAME!r}; recebeu "
            f"usuário={parsed.username!r}, banco={dbname!r}). Estar vazio não basta "
            "-- precisa ser exatamente esta bancada."
        )

    # A URL devolvida é renderizada pelo mesmo parser que o SQLAlchemy usa.
    # Examine também a query original para recusar chaves com valor vazio.
    original_query = urlsplit(url, allow_fragments=False).query
    query_keys = {key.lower() for key in parsed.query}
    query_keys.update(key.lower() for key, _ in parse_qsl(original_query, keep_blank_values=True))
    overrides = query_keys & _IDENTITY_OVERRIDE_QUERY_KEYS
    if overrides:
        raise RuntimeError(
            "CARTORIO_TEST_POSTGRES_URL tem parâmetro(s) de query que podem sobrepor "
            f"a identidade já validada na URI principal: {sorted(overrides)}. A "
            "autoridade (usuário/banco) validada acima não é garantia nenhuma se a "
            "querystring puder redirecionar a conexão de verdade -- recusado."
        )
    return parsed.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)


def _require_clean_pg_env(url: str) -> None:
    """O ambiente do processo não pode preencher nem redirecionar nada que a URL
    já define ou deveria definir. Roda antes de qualquer conexão da fixture."""
    offending = [name for name in _ALWAYS_FORBIDDEN_PG_ENV_VARS if os.environ.get(name)]

    parsed = make_url(url)
    if not parsed.host and os.environ.get("PGHOST"):
        offending.append("PGHOST")
    if not parsed.port and os.environ.get("PGPORT"):
        offending.append("PGPORT")

    if offending:
        raise RuntimeError(", ".join(sorted(offending)))


def _psycopg_conninfo(url: str) -> str:
    """Reaproveita os parâmetros decodificados da URL, inclusive os espaços de `options`."""
    from psycopg.conninfo import make_conninfo

    parsed = make_url(url)
    params = parsed.translate_connect_args(username="user", database="dbname")
    params.update(parsed.query)
    return make_conninfo(**params)


def _scoped_url(base_url: str, schema: str) -> str:
    """URL da mesma bancada, mas com `search_path` fixado no schema exclusivo desta
    execução -- Alembic, o app e os INSERTs diretos passam a resolver tabelas sem
    qualificação (`financial_entries`, não `esquema.financial_entries`) contra esse
    schema, nunca contra `public`."""
    parsed = make_url(base_url)
    existing_options = parsed.normalized_query.get("options", ("",))[-1]
    scoped_options = f"{existing_options} -c search_path={schema}".lstrip()
    return parsed.update_query_dict({"options": scoped_options}).render_as_string(
        hide_password=False
    )


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
    conhecida (nunca por "estar vazio"), ou se o ambiente tiver `PG*` que possam
    preencher ou sobrepor o que a URL já define -- tudo antes da primeira conexão.
    Cria um schema com nome único, migra só nele, e sempre o descarta no `finally`
    -- inclusive se o setup ou qualquer teste (incluindo o smoke HTTP) falhar.
    Nunca toca em `public` ou em qualquer outro schema que porventura já exista
    na bancada.
    """
    base_url = _require_postgres_url(POSTGRES_URL)
    _require_clean_pg_env(base_url)
    schema = f"fase_b_test_{uuid.uuid4().hex[:12]}"
    scoped_url = _scoped_url(base_url, schema)

    _create_schema(base_url, schema)
    try:
        _run_alembic("upgrade", "head", database_url=scoped_url)
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


def test_require_postgres_url_rejects_extra_slash_in_database() -> None:
    url = f"postgresql://{_EXPECTED_BANCADA_USER}:senha@127.0.0.1:5432//{_EXPECTED_BANCADA_DBNAME}"
    with pytest.raises(RuntimeError, match="bancada descartável conhecida"):
        _require_postgres_url(url)


@pytest.mark.parametrize(
    "query",
    [
        "dbname=cartorio_fase_b_outro",
        "application_name=lab#tag&dbname=cartorio_fase_b_outro",
        "dbname=",
    ],
)
def test_require_postgres_url_rejects_dbname_override_in_query(query: str) -> None:
    """Usuário e banco corretos na URI principal não bastam se a querystring puder
    redirecionar a conexão para outro banco via `dbname=`."""
    url = (
        f"postgresql://{_EXPECTED_BANCADA_USER}:senha@127.0.0.1:5432/"
        f"{_EXPECTED_BANCADA_DBNAME}?{query}"
    )
    with pytest.raises(RuntimeError, match="sobrepor"):
        _require_postgres_url(url)


@pytest.mark.parametrize("user", ["outro_usuario", ""])
def test_require_postgres_url_rejects_user_override_in_query(user: str) -> None:
    """O mesmo ataque, via `user=` -- a URI principal diz um usuário, a query
    poderia autenticar como outro."""
    url = (
        f"postgresql://{_EXPECTED_BANCADA_USER}:senha@127.0.0.1:5432/"
        f"{_EXPECTED_BANCADA_DBNAME}?user={user}"
    )
    with pytest.raises(RuntimeError, match="sobrepor"):
        _require_postgres_url(url)


_BANCADA_URL_WITH_HOST_AND_PORT = (
    f"postgresql://{_EXPECTED_BANCADA_USER}:senha@127.0.0.1:5432/{_EXPECTED_BANCADA_DBNAME}"
)


def test_scoped_url_adds_search_path_to_existing_options() -> None:
    base_url = _require_postgres_url(
        f"{_BANCADA_URL_WITH_HOST_AND_PORT}?options=-c%20statement_timeout%3D5000"
        "&application_name=fase-b%25literal"
    )
    scoped = make_url(_scoped_url(base_url, "fase_b_test_sintetico"))
    assert scoped.drivername == "postgresql+psycopg"
    assert (
        scoped.query["options"] == "-c statement_timeout=5000 -c search_path=fase_b_test_sintetico"
    )
    assert scoped.query["application_name"] == "fase-b%literal"


def test_require_clean_pg_env_rejects_pghostaddr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PGHOSTADDR", "10.0.0.1")
    with pytest.raises(RuntimeError, match="PGHOSTADDR"):
        _require_clean_pg_env(_BANCADA_URL_WITH_HOST_AND_PORT)


def test_require_clean_pg_env_rejects_pgservice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PGSERVICE", "algum-perfil")
    with pytest.raises(RuntimeError, match="PGSERVICE"):
        _require_clean_pg_env(_BANCADA_URL_WITH_HOST_AND_PORT)


def test_require_clean_pg_env_rejects_pghost_when_url_has_no_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PGHOST", "10.0.0.1")
    url = f"postgresql://{_EXPECTED_BANCADA_USER}:senha@/{_EXPECTED_BANCADA_DBNAME}"
    with pytest.raises(RuntimeError, match="PGHOST"):
        _require_clean_pg_env(url)


def test_require_clean_pg_env_accepts_pghost_when_url_has_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A URL já tem host explícito -- PGHOST fica inerte, não precisa ser recusada."""
    for name in _ALWAYS_FORBIDDEN_PG_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PGHOST", "10.0.0.1")
    _require_clean_pg_env(_BANCADA_URL_WITH_HOST_AND_PORT)


def test_require_clean_pg_env_rejects_pgport_when_url_has_no_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PGPORT", "6543")
    url = f"postgresql://{_EXPECTED_BANCADA_USER}:senha@127.0.0.1/{_EXPECTED_BANCADA_DBNAME}"
    with pytest.raises(RuntimeError, match="PGPORT"):
        _require_clean_pg_env(url)


def test_require_clean_pg_env_accepts_pgport_when_url_has_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A URL já tem porta explícita -- PGPORT fica inerte, não precisa ser recusada."""
    for name in _ALWAYS_FORBIDDEN_PG_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PGPORT", "6543")
    _require_clean_pg_env(_BANCADA_URL_WITH_HOST_AND_PORT)


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
    synthetic_url = (
        make_url(postgres_db)
        .update_query_dict({"application_name": "fase-b%literal"})
        .render_as_string(hide_password=False)
    )
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
