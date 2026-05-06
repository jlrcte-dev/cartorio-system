from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.modules.retention import service
from app.modules.retention.enums import (
    RetentionDestination,
    RetentionPhaseKind,
    RetentionStatus,
)
from app.modules.retention.models import RetentionRule
from app.modules.retention.schemas import DocumentMetadata

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rule(**kwargs) -> RetentionRule:
    defaults = dict(
        codigo="3-9-9",
        assunto="Teste",
        documento="Documento de teste",
        fase_corrente_text="Permanente",
        fase_corrente_kind=RetentionPhaseKind.PERMANENT,
        fase_corrente_years=None,
        fase_corrente_months=None,
        fase_intermediaria_text=None,
        eliminacao=False,
        guarda_permanente=True,
        requer_microfilmagem=False,
        requer_digitalizacao=False,
        observacao=None,
        base_legal=None,
        alteracoes=None,
        source_norm="PROVIMENTO_CNJ_50_2015",
        source_version="COMPILADO_LOCAL",
        source_file="_local_data/test.pdf",
        source_code="3-9-9",
        source_notes="teste",
    )
    defaults.update(kwargs)
    return RetentionRule(**defaults)


# ---------------------------------------------------------------------------
# Read-only safety
# ---------------------------------------------------------------------------


@pytest.fixture
def block_destructive_calls(monkeypatch):
    """Falha o teste se qualquer função destrutiva for chamada."""

    def fail(*_args, **_kwargs):
        raise AssertionError("Operação destrutiva detectada — módulo retention deve ser read-only")

    monkeypatch.setattr(os, "remove", fail)
    monkeypatch.setattr(os, "unlink", fail)
    monkeypatch.setattr(os, "rmdir", fail)
    monkeypatch.setattr(os, "rename", fail)
    monkeypatch.setattr(os, "replace", fail)
    monkeypatch.setattr(shutil, "move", fail)
    monkeypatch.setattr(shutil, "rmtree", fail)
    monkeypatch.setattr(Path, "unlink", fail)
    monkeypatch.setattr(Path, "rename", fail)
    monkeypatch.setattr(Path, "replace", fail)
    yield


# ---------------------------------------------------------------------------
# evaluate_document
# ---------------------------------------------------------------------------


def test_permanent_document_returns_permanent_status(block_destructive_calls):
    rule = _make_rule(
        codigo="3-1-1-3",
        documento="Livro de registro de nascimento — assento",
        fase_corrente_text="Permanente",
        fase_corrente_kind=RetentionPhaseKind.PERMANENT,
        guarda_permanente=True,
    )
    metadata = DocumentMetadata(
        name="livro_registro_nascimento_assento_2010.pdf",
        path_relative="rcpn/livros/livro_registro_nascimento_assento_2010.pdf",
        modified_at=datetime(2010, 1, 1, tzinfo=UTC),
    )
    result = service.evaluate_document(metadata, [rule])

    assert result.status == RetentionStatus.PERMANENT
    assert result.destination == RetentionDestination.PERMANENT
    assert result.matched_rule_codigo == "3-1-1-3"
    assert "não executar descarte automático" in result.advisory.lower()


def test_expired_document_marked_for_review(block_destructive_calls):
    rule = _make_rule(
        codigo="3-1-2",
        documento="Declaração de Nascido Vivo (DNV)",
        fase_corrente_text="1 ano",
        fase_corrente_kind=RetentionPhaseKind.DURATION,
        fase_corrente_years=1,
        eliminacao=True,
        guarda_permanente=False,
    )
    now = datetime(2026, 5, 5, tzinfo=UTC)
    metadata = DocumentMetadata(
        name="declaracao_nascido_vivo_dnv_2020.pdf",
        path_relative="rcpn/dnv/declaracao_nascido_vivo_dnv_2020.pdf",
        modified_at=datetime(2020, 1, 1, tzinfo=UTC),
    )
    result = service.evaluate_document(metadata, [rule], now=now)

    assert result.status == RetentionStatus.EXPIRED_REVIEW_REQUIRED
    assert result.is_overdue is True
    assert result.overdue_by_days is not None and result.overdue_by_days > 0
    assert "exige avaliação humana" in result.message.lower()
    assert "não executar descarte automático" in result.message.lower()


def test_unclassified_document_returns_needs_classification(block_destructive_calls):
    rule = _make_rule(
        codigo="3-1-1-3",
        documento="Livro de registro de nascimento — assento",
        guarda_permanente=True,
    )
    metadata = DocumentMetadata(
        name="documento_qualquer.txt",
        path_relative="diversos/documento_qualquer.txt",
    )
    result = service.evaluate_document(metadata, [rule])

    assert result.status == RetentionStatus.NEEDS_CLASSIFICATION
    assert result.matched_rule_codigo is None
    assert "candidato à revisão de temporalidade" in result.message.lower()


def test_legal_hold_overrides_expired_term(block_destructive_calls):
    rule = _make_rule(
        codigo="3-1-2",
        documento="Declaração de Nascido Vivo (DNV)",
        fase_corrente_text="1 ano",
        fase_corrente_kind=RetentionPhaseKind.DURATION,
        fase_corrente_years=1,
        eliminacao=True,
        guarda_permanente=False,
    )
    now = datetime(2026, 5, 5, tzinfo=UTC)
    metadata = DocumentMetadata(
        name="declaracao_nascido_vivo_dnv_2020.pdf",
        path_relative="rcpn/dnv/declaracao_nascido_vivo_dnv_2020.pdf",
        modified_at=datetime(2020, 1, 1, tzinfo=UTC),
        legal_hold=True,
    )
    result = service.evaluate_document(metadata, [rule], now=now)

    assert result.status == RetentionStatus.BLOCKED_BY_LEGAL_HOLD
    assert result.is_overdue is False
    assert result.matched_rule_codigo is None
    assert "legal hold" in result.message.lower()


def test_active_document_within_term(block_destructive_calls):
    rule = _make_rule(
        codigo="3-9-4",
        documento="Ofícios e requerimentos",
        fase_corrente_text="5 anos",
        fase_corrente_kind=RetentionPhaseKind.DURATION,
        fase_corrente_years=5,
        eliminacao=True,
        guarda_permanente=False,
    )
    now = datetime(2026, 5, 5, tzinfo=UTC)
    metadata = DocumentMetadata(
        name="oficio_requerimento_recente.pdf",
        path_relative="admin/oficios/oficio_requerimento_recente.pdf",
        modified_at=now - timedelta(days=200),
    )
    result = service.evaluate_document(metadata, [rule], now=now)

    assert result.status == RetentionStatus.ACTIVE
    assert result.is_overdue is False


def test_disposal_requires_media_destination(block_destructive_calls):
    rule = _make_rule(
        codigo="3-1-6-2-1",
        documento="Casamentos celebrados",
        fase_corrente_text="3 anos após data do registro",
        fase_corrente_kind=RetentionPhaseKind.DURATION,
        fase_corrente_years=3,
        eliminacao=True,
        guarda_permanente=False,
        requer_microfilmagem=True,
        requer_digitalizacao=True,
    )
    metadata = DocumentMetadata(
        name="casamento_celebrado_001.pdf",
        path_relative="rcpn/casamentos/casamento_celebrado_001.pdf",
        modified_at=datetime(2010, 1, 1, tzinfo=UTC),
    )
    now = datetime(2026, 5, 5, tzinfo=UTC)
    result = service.evaluate_document(metadata, [rule], now=now)

    assert result.destination == RetentionDestination.DISPOSAL_REQUIRES_MEDIA
    assert result.requires_media_before_disposal is True


def test_advisory_present_in_all_outputs(block_destructive_calls):
    """Toda avaliação deve carregar advisory conservador."""

    rule = _make_rule(guarda_permanente=True)
    metadata = DocumentMetadata(name="x.pdf", path_relative="x.pdf")
    result = service.evaluate_document(metadata, [rule])
    advisory_lower = result.advisory.lower()
    assert "exige avaliação humana" in advisory_lower
    assert "não executar descarte automático" in advisory_lower
    assert "validar com responsável" in advisory_lower
