"""Compatibilidade PostgreSQL da Fase B de homologação.

Todo este módulo exige um PostgreSQL 18 descartável já de pé, apontado por
`CARTORIO_TEST_POSTGRES_URL` (uma URL para um banco vazio, de uso exclusivo deste
teste). Sem essa variável, o módulo inteiro é pulado -- não entra no gate padrão
(`pytest`), que continua só contra SQLite. Nenhum dado real: tudo aqui é sintético e
descartado ao final (inserts em transação revertida, processos efêmeros encerrados).
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
import pytest

psycopg = pytest.importorskip("psycopg")

POSTGRES_URL = os.environ.get("CARTORIO_TEST_POSTGRES_URL")

pytestmark = pytest.mark.skipif(
    POSTGRES_URL is None,
    reason="requer CARTORIO_TEST_POSTGRES_URL (PostgreSQL descartável, banco vazio)",
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_alembic(*args: str, database_url: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _psycopg_conninfo(url: str) -> str:
    """psycopg.connect() só entende o esquema libpq puro, sem o `+psycopg`
    do SQLAlchemy/Alembic."""
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_alembic_upgrade_head_on_empty_postgres() -> None:
    """`alembic upgrade head` roda limpo e termina em head no PostgreSQL descartável.

    Idempotente de propósito: se o banco já estiver em head (reexecução deste
    teste sem recriar o banco), isto é um no-op válido, não uma falha.
    """
    result = _run_alembic("upgrade", "head", database_url=POSTGRES_URL)
    assert result.returncode == 0, result.stdout + result.stderr

    current = _run_alembic("current", database_url=POSTGRES_URL)
    assert current.returncode == 0, current.stdout + current.stderr
    assert "f4a5b6c7d8e9" in current.stdout + current.stderr


def test_alembic_check_reports_no_drift() -> None:
    result = _run_alembic("check", database_url=POSTGRES_URL)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "No new upgrade operations detected." in result.stdout + result.stderr


def test_alembic_tolerates_percent_in_url() -> None:
    """Regressão do bug de interpolação do ConfigParser.

    `config.set_main_option`/`get_section` interpolam "%" -- uma URL real com esse
    caractere (comum em senha/host percent-encoded) quebrava `alembic/env.py` antes
    desta Fase B. O valor abaixo decodifica para um "%" literal na querystring: uma
    URL sintética, no sentido do diagnóstico original, não uma credencial real.
    """
    separator = "&" if "?" in POSTGRES_URL else "?"
    synthetic_url = f"{POSTGRES_URL}{separator}application_name=fase-b%25literal"
    result = _run_alembic("current", database_url=synthetic_url)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "f4a5b6c7d8e9" in result.stdout + result.stderr


def test_boolean_defaults_resolve_to_false_on_insert() -> None:
    """As 5 colunas Boolean com DEFAULT (`false`, não `0`) resolvem no INSERT real.

    `retention_rules` (4 colunas) e `compliance_requirement_statuses.human_review_required`
    (a 5a, via a linha-pai obrigatória em `compliance_requirements`). Tudo numa
    transação revertida ao final -- nada fica no banco descartável.
    """
    suffix = uuid.uuid4().hex[:8]
    with psycopg.connect(_psycopg_conninfo(POSTGRES_URL)) as conn:
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


def test_api_write_and_read_against_postgres() -> None:
    """Escrita e leitura reais pela API HTTP, com o processo apontando para o Postgres."""
    port = _free_port()
    env = os.environ.copy()
    env["DATABASE_URL"] = POSTGRES_URL
    env["APP_NAME"] = "Cartorio System - Fase B Postgres (teste)"
    env["DEBUG"] = "false"
    env["PYTHONDONTWRITEBYTECODE"] = "1"

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
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        base = f"http://127.0.0.1:{port}/api/v1"
        health = None
        for _ in range(50):
            try:
                health = httpx.get(f"{base}/health", timeout=1).json()
                break
            except httpx.TransportError:
                time.sleep(0.2)
        assert health is not None, "API nao respondeu a tempo"
        assert health["app"] == "Cartorio System - Fase B Postgres (teste)"

        code = f"PGTEST-{uuid.uuid4().hex[:12]}"
        created = httpx.post(
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
            timeout=5,
        )
        assert created.status_code == 201, created.text
        finding_id = created.json()["id"]

        fetched = httpx.get(f"{base}/audit/findings/{finding_id}", timeout=5).json()
        assert fetched["finding_code"] == code
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
