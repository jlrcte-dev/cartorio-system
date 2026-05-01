"""Garante que pytest não toca o banco de produção e que o 500 handler loga."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def test_lifespan_does_not_touch_production_db() -> None:
    """O lifespan não pode mais executar DDL no engine real.

    Captura mtime de `cartorio.db` antes de subir o TestClient. Após o ciclo
    de lifespan + uma chamada de healthcheck, o arquivo não pode ter sido
    criado (se ausente) nem modificado (se presente).
    """
    from app.main import app  # import tardio para garantir captura de estado

    db_path = Path("cartorio.db")
    pre_exists = db_path.exists()
    pre_mtime = db_path.stat().st_mtime_ns if pre_exists else None

    with TestClient(app) as c:
        response = c.get("/api/v1/health")
        assert response.status_code == 200

    if pre_exists:
        assert db_path.stat().st_mtime_ns == pre_mtime, (
            "lifespan modificou cartorio.db — DDL voltou para a aplicação?"
        )
    else:
        assert not db_path.exists(), "lifespan criou cartorio.db — DDL voltou para a aplicação?"


def test_unhandled_exception_is_logged_by_handler(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """O handler 500 deve emitir log.exception com traceback."""
    from app.main import app

    @app.get("/__force_error_for_test")
    def _boom() -> None:
        raise RuntimeError("boom de teste")

    try:
        # raise_server_exceptions=False permite que o handler 500 atue
        with (
            TestClient(app, raise_server_exceptions=False) as c,
            caplog.at_level(logging.ERROR, logger="app.core.errors"),
        ):
            response = c.get("/__force_error_for_test")
            assert response.status_code == 500
            assert response.json() == {"detail": "Erro interno do servidor."}
    finally:
        app.router.routes = [
            r for r in app.router.routes if getattr(r, "path", "") != "/__force_error_for_test"
        ]

    error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert error_records, "Nenhum log de erro foi capturado pelo handler 500"
    assert any("Unhandled error" in r.getMessage() for r in error_records), (
        "Mensagem 'Unhandled error' não foi emitida pelo handler"
    )
    assert any(r.exc_info is not None for r in error_records), (
        "Nenhum log incluiu traceback (exc_info)"
    )
