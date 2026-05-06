from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.modules.audit.diagnosis import temp_rules
from app.modules.retention.enums import RetentionPhaseKind
from app.modules.retention.models import RetentionRule


@pytest.fixture
def block_destructive_calls(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("Operação destrutiva detectada — TEMP-* devem ser read-only")

    monkeypatch.setattr(os, "remove", fail)
    monkeypatch.setattr(os, "unlink", fail)
    monkeypatch.setattr(shutil, "move", fail)
    monkeypatch.setattr(shutil, "rmtree", fail)
    monkeypatch.setattr(Path, "unlink", fail)
    monkeypatch.setattr(Path, "rename", fail)
    yield


def _rule(**kwargs) -> RetentionRule:
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


def _file(
    name: str,
    path: str,
    *,
    modified_at: datetime | None = None,
    extension: str = ".pdf",
) -> dict:
    return {
        "name": name,
        "path_relative": path,
        "parent_path": path.rsplit("/", 1)[0] if "/" in path else "",
        "extension": extension,
        "size_bytes": 1024,
        "modified_at": (modified_at or datetime(2025, 1, 1, tzinfo=UTC)).isoformat(),
    }


# ---------------------------------------------------------------------------
# TEMP-001
# ---------------------------------------------------------------------------


def test_temp_001_flags_unclassified_in_document_dir(block_destructive_calls):
    rules = [
        _rule(
            codigo="3-1-1-3",
            documento="Livro de registro de nascimento — assento",
            guarda_permanente=True,
        )
    ]
    files = [
        _file("arquivo_avulso.txt", "registros/avulsos/arquivo_avulso.txt"),
        _file(
            "livro_registro_nascimento_assento.pdf",
            "registros/livros/livro_registro_nascimento_assento.pdf",
        ),
    ]
    findings = temp_rules.rule_temp_001_unclassified(files, rules, scanner_run_id="run-1")

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "TEMP-001"
    assert "registros/avulsos" in finding.related_file_path
    assert "candidato à revisão" in finding.description.lower()
    assert "não executar descarte automático" in finding.description.lower()


def test_temp_001_skips_files_outside_document_dirs(block_destructive_calls):
    rules: list[RetentionRule] = []
    files = [_file("relatorio.xlsx", "financeiro/relatorios/relatorio.xlsx")]
    findings = temp_rules.rule_temp_001_unclassified(files, rules, scanner_run_id="run-1")
    assert findings == []


# ---------------------------------------------------------------------------
# TEMP-002
# ---------------------------------------------------------------------------


def test_temp_002_flags_potentially_expired(block_destructive_calls):
    rules = [
        _rule(
            codigo="3-1-2",
            documento="Declaração de Nascido Vivo (DNV)",
            fase_corrente_text="1 ano",
            fase_corrente_kind=RetentionPhaseKind.DURATION,
            fase_corrente_years=1,
            eliminacao=True,
            guarda_permanente=False,
        )
    ]
    now = datetime(2026, 5, 5, tzinfo=UTC)
    files = [
        _file(
            "declaracao_nascido_vivo_dnv.pdf",
            "rcpn/dnv/declaracao_nascido_vivo_dnv.pdf",
            modified_at=datetime(2020, 1, 1, tzinfo=UTC),
        ),
        _file(
            "declaracao_nascido_vivo_dnv_recente.pdf",
            "rcpn/dnv/declaracao_nascido_vivo_dnv_recente.pdf",
            modified_at=now - timedelta(days=30),
        ),
    ]
    findings = temp_rules.rule_temp_002_expired(files, rules, scanner_run_id="run-2", now=now)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "TEMP-002"
    assert "potencialmente vencido" in finding.title.lower()
    assert "exige avaliação humana" in finding.description.lower()
    assert "não executar descarte automático" in finding.description.lower()
    assert "regra 3-1-2" in finding.evidence_summary.lower()


def test_temp_002_does_not_flag_permanent_rules(block_destructive_calls):
    rules = [
        _rule(
            codigo="3-1-1-3",
            documento="Livro de registro de nascimento — assento",
            guarda_permanente=True,
        )
    ]
    files = [
        _file(
            "livro_registro_nascimento_assento.pdf",
            "rcpn/livros/livro_registro_nascimento_assento.pdf",
            modified_at=datetime(1990, 1, 1, tzinfo=UTC),
        )
    ]
    findings = temp_rules.rule_temp_002_expired(
        files, rules, scanner_run_id="run-2", now=datetime(2026, 5, 5, tzinfo=UTC)
    )
    assert findings == []


# ---------------------------------------------------------------------------
# TEMP-003
# ---------------------------------------------------------------------------


def test_temp_003_flags_permanent_in_suspicious_location(block_destructive_calls):
    rules = [
        _rule(
            codigo="3-5-1-2",
            documento="Testamentos públicos",
            guarda_permanente=True,
        )
    ]
    files = [
        _file(
            "testamento_publico_001.pdf",
            "notas/_old/testamento_publico_001.pdf",
        ),
        _file(
            "testamento_publico_002.pdf",
            "notas/oficial/testamento_publico_002.pdf",
        ),
    ]
    findings = temp_rules.rule_temp_003_permanent_in_suspicious_location(
        files, rules, scanner_run_id="run-3"
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "TEMP-003"
    assert "_old" in finding.related_file_path
    assert "candidato à revisão" in finding.description.lower()
    assert "validar com responsável" in finding.recommended_action.lower()


def test_temp_003_skips_non_permanent(block_destructive_calls):
    rules = [
        _rule(
            codigo="3-1-2",
            documento="Declaração de Nascido Vivo (DNV)",
            fase_corrente_text="1 ano",
            fase_corrente_kind=RetentionPhaseKind.DURATION,
            fase_corrente_years=1,
            eliminacao=True,
            guarda_permanente=False,
        )
    ]
    files = [
        _file(
            "declaracao_nascido_vivo_dnv.pdf",
            "rcpn/_tmp/declaracao_nascido_vivo_dnv.pdf",
        )
    ]
    findings = temp_rules.rule_temp_003_permanent_in_suspicious_location(
        files, rules, scanner_run_id="run-3"
    )
    assert findings == []


# ---------------------------------------------------------------------------
# Conservative language guarantee
# ---------------------------------------------------------------------------


def test_no_finding_recommends_automatic_disposal(block_destructive_calls):
    """Garantia: nenhum finding TEMP-* sugere descarte automático."""

    rules = [
        _rule(
            codigo="3-1-1-3",
            documento="Livro de registro de nascimento — assento",
            guarda_permanente=True,
        ),
        _rule(
            codigo="3-1-2",
            documento="Declaração de Nascido Vivo (DNV)",
            fase_corrente_text="1 ano",
            fase_corrente_kind=RetentionPhaseKind.DURATION,
            fase_corrente_years=1,
            eliminacao=True,
            guarda_permanente=False,
        ),
    ]
    now = datetime(2026, 5, 5, tzinfo=UTC)
    files = [
        _file(
            "declaracao_nascido_vivo_dnv.pdf",
            "rcpn/dnv/declaracao_nascido_vivo_dnv.pdf",
            modified_at=datetime(2020, 1, 1, tzinfo=UTC),
        ),
        _file(
            "livro_registro_nascimento_assento.pdf",
            "rcpn/_old/livro_registro_nascimento_assento.pdf",
        ),
        _file("avulso.pdf", "registros/avulsos/avulso.pdf"),
    ]

    all_findings = (
        temp_rules.rule_temp_001_unclassified(files, rules, scanner_run_id="r")
        + temp_rules.rule_temp_002_expired(files, rules, scanner_run_id="r", now=now)
        + temp_rules.rule_temp_003_permanent_in_suspicious_location(
            files, rules, scanner_run_id="r"
        )
    )

    assert all_findings, "esperado pelo menos um finding"
    forbidden_phrases = (
        "excluir automaticamente",
        "remover automaticamente",
        "deletar automaticamente",
        "apagar automaticamente",
        "executar descarte automaticamente",
    )
    for f in all_findings:
        full_text = " ".join(
            [f.title, f.description, f.recommended_action, f.evidence_summary, f.notes]
        ).lower()
        for phrase in forbidden_phrases:
            assert phrase not in full_text, f"finding {f.rule_id} contém frase proibida: {phrase!r}"
        # Saída obrigatória: proibição explícita de descarte automático.
        assert "não executar descarte automático" in f.description.lower()
