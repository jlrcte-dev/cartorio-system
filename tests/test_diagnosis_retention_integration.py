"""Integração TEMP-001/002/003 ↔ DocumentDiagnosis (Sprint retention-1B).

Estes testes validam que as regras de temporalidade documental são
plugadas no pipeline principal apenas quando o chamador injeta a lista
de RetentionRule. O pipeline continua read-only e jamais recomenda
descarte automático.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.modules.audit.diagnosis.analyzer import DocumentAnalyzer
from app.modules.retention.enums import RetentionPhaseKind
from app.modules.retention.models import RetentionRule

# ---------------------------------------------------------------------------
# Bloqueio de operações destrutivas — herdado da Sprint 1A.
# ---------------------------------------------------------------------------


@pytest.fixture
def block_destructive_calls(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError(
            "Operação destrutiva detectada — pipeline retention/audit deve ser read-only"
        )

    monkeypatch.setattr(os, "remove", fail)
    monkeypatch.setattr(os, "unlink", fail)
    monkeypatch.setattr(os, "rename", fail)
    monkeypatch.setattr(os, "replace", fail)
    monkeypatch.setattr(shutil, "move", fail)
    monkeypatch.setattr(shutil, "rmtree", fail)
    monkeypatch.setattr(Path, "unlink", fail)
    monkeypatch.setattr(Path, "rename", fail)
    monkeypatch.setattr(Path, "replace", fail)
    yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _file_entry(
    name: str,
    *,
    path_relative: str | None = None,
    parent_path: str = ".",
    size_bytes: int = 1024,
    extension: str | None = None,
    modified_at: str = "2024-01-01T00:00:00+00:00",
) -> dict:
    if extension is None:
        extension = ("." + name.rsplit(".", 1)[1].lower()) if "." in name else ""
    if path_relative is None:
        path_relative = name
    return {
        "name": name,
        "extension": extension,
        "path_relative": path_relative,
        "parent_path": parent_path,
        "entry_type": "file",
        "depth": 1,
        "size_bytes": size_bytes,
        "modified_at": modified_at,
        "created_at": modified_at,
        "error": None,
    }


def _write_inventory(tmp: Path, files: list[dict], run_id: str = "run-temp-1B") -> Path:
    tmp.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": {
            "run_id": run_id,
            "run_name": "retention-1B",
            "root_path": "[root]",
            "started_at": "2026-05-06T10:00:00+00:00",
            "finished_at": "2026-05-06T10:01:00+00:00",
            "duration_seconds": 60.0,
            "total_files": len(files),
            "total_directories": 0,
            "total_size_bytes": sum(f.get("size_bytes", 0) for f in files),
            "errors_count": 0,
            "excluded_count": 0,
        },
        "parameters": {
            "max_depth": None,
            "follow_symlinks": False,
            "include_hidden": True,
            "fail_fast": False,
            "exclude_patterns": [],
        },
        "files": files,
        "directories": [],
        "errors": [],
    }
    path = tmp / "file_inventory.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 1. TEMP-001 no pipeline principal
# ---------------------------------------------------------------------------


def test_pipeline_emits_temp_001_for_unclassified_document(tmp_path, block_destructive_calls):
    """Arquivo em diretório documental, sem regra associada, gera TEMP-001."""

    rules = [
        _rule(
            codigo="3-1-1-3",
            documento="Livro de registro de nascimento — assento",
            guarda_permanente=True,
        )
    ]
    files = [
        _file_entry(
            "arquivo_avulso.txt",
            path_relative="registros/avulsos/arquivo_avulso.txt",
            parent_path="registros/avulsos",
        )
    ]
    inv = _write_inventory(tmp_path / "inv", files)

    result = DocumentAnalyzer(
        inventory_path=inv,
        retention_rules=rules,
        include_low_priority=True,  # TEMP-001 tem prioridade BACKLOG
    ).run()

    temps = [c for c in result.candidates if c.rule_id == "TEMP-001"]
    assert len(temps) == 1
    assert "candidato à revisão" in temps[0].description.lower()
    assert "não executar descarte automático" in temps[0].description.lower()


# ---------------------------------------------------------------------------
# 2. TEMP-002 no pipeline principal
# ---------------------------------------------------------------------------


def test_pipeline_emits_temp_002_for_potentially_expired_document(
    tmp_path, block_destructive_calls
):
    """Arquivo casado com regra DURATION e prazo aparentemente vencido gera TEMP-002."""

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
        _file_entry(
            "declaracao_nascido_vivo_dnv.pdf",
            path_relative="rcpn/dnv/declaracao_nascido_vivo_dnv.pdf",
            parent_path="rcpn/dnv",
            modified_at="2020-01-01T00:00:00+00:00",
        )
    ]
    inv = _write_inventory(tmp_path / "inv", files)

    result = DocumentAnalyzer(inventory_path=inv, retention_rules=rules).run()

    temps = [c for c in result.candidates if c.rule_id == "TEMP-002"]
    assert len(temps) == 1
    assert "potencialmente vencido" in temps[0].title.lower()
    assert "não executar descarte automático" in temps[0].description.lower()


def test_pipeline_does_not_emit_temp_002_for_permanent_rule(tmp_path, block_destructive_calls):
    """Regra de guarda permanente nunca produz TEMP-002, mesmo com arquivo antigo."""

    rules = [
        _rule(
            codigo="3-1-1-3",
            documento="Livro de registro de nascimento — assento",
            guarda_permanente=True,
        )
    ]
    files = [
        _file_entry(
            "livro_registro_nascimento_assento.pdf",
            path_relative="rcpn/livros/livro_registro_nascimento_assento.pdf",
            parent_path="rcpn/livros",
            modified_at="1995-01-01T00:00:00+00:00",
        )
    ]
    inv = _write_inventory(tmp_path / "inv", files)

    result = DocumentAnalyzer(inventory_path=inv, retention_rules=rules).run()

    temps = [c for c in result.candidates if c.rule_id == "TEMP-002"]
    assert temps == []


# ---------------------------------------------------------------------------
# 3. TEMP-003 no pipeline principal
# ---------------------------------------------------------------------------


def test_pipeline_emits_temp_003_for_permanent_in_suspicious_location(
    tmp_path, block_destructive_calls
):
    """Arquivo de guarda permanente em diretório suspeito gera TEMP-003."""

    rules = [
        _rule(
            codigo="3-5-1-2",
            documento="Testamentos públicos",
            guarda_permanente=True,
        )
    ]
    files = [
        _file_entry(
            "testamento_publico_001.pdf",
            path_relative="notas/_old/testamento_publico_001.pdf",
            parent_path="notas/_old",
        )
    ]
    inv = _write_inventory(tmp_path / "inv", files)

    result = DocumentAnalyzer(inventory_path=inv, retention_rules=rules).run()

    temps = [c for c in result.candidates if c.rule_id == "TEMP-003"]
    assert len(temps) == 1
    assert "_old" in temps[0].related_file_path
    assert "candidato à revisão" in temps[0].description.lower()


# ---------------------------------------------------------------------------
# 4. Pipeline continua funcionando sem regra retention correspondente
# ---------------------------------------------------------------------------


def test_pipeline_runs_without_retention_rules_argument(tmp_path, block_destructive_calls):
    """Sem `retention_rules`, o pipeline não emite findings TEMP-*."""

    files = [
        _file_entry(
            "qualquer.pdf",
            path_relative="registros/qualquer.pdf",
            parent_path="registros",
        )
    ]
    inv = _write_inventory(tmp_path / "inv", files)

    result = DocumentAnalyzer(inventory_path=inv, include_low_priority=True).run()

    temp_ids = {c.rule_id for c in result.candidates if c.rule_id.startswith("TEMP-")}
    assert temp_ids == set()


def test_pipeline_with_empty_retention_rules_emits_no_temp_findings(
    tmp_path, block_destructive_calls
):
    """Lista vazia de regras: TEMP-002/003 ficam silenciosos; TEMP-001 só
    dispara em diretórios documentais — em pasta neutra, não dispara."""

    files = [
        _file_entry(
            "qualquer.pdf",
            path_relative="docs/qualquer.pdf",
            parent_path="docs",
            modified_at="2020-01-01T00:00:00+00:00",
        )
    ]
    inv = _write_inventory(tmp_path / "inv", files)

    result = DocumentAnalyzer(
        inventory_path=inv, retention_rules=[], include_low_priority=True
    ).run()

    temp_ids = {c.rule_id for c in result.candidates if c.rule_id.startswith("TEMP-")}
    assert temp_ids == set()


def test_pipeline_with_empty_rules_still_flags_unclassified_in_document_dir(
    tmp_path, block_destructive_calls
):
    """Mesmo com lista vazia, arquivo em diretório documental dispara TEMP-001
    (não há regra para casar)."""

    files = [
        _file_entry(
            "avulso.pdf",
            path_relative="registros/avulsos/avulso.pdf",
            parent_path="registros/avulsos",
        )
    ]
    inv = _write_inventory(tmp_path / "inv", files)

    result = DocumentAnalyzer(
        inventory_path=inv, retention_rules=[], include_low_priority=True
    ).run()

    temps = [c for c in result.candidates if c.rule_id == "TEMP-001"]
    assert len(temps) == 1


# ---------------------------------------------------------------------------
# 5. Linguagem conservadora obrigatória — pipeline integrado
# ---------------------------------------------------------------------------


def test_no_temp_finding_recommends_automatic_disposal(tmp_path, block_destructive_calls):
    """Garantia: nenhum finding TEMP-* emitido pelo pipeline sugere descarte automático."""

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
    files = [
        _file_entry(
            "declaracao_nascido_vivo_dnv.pdf",
            path_relative="rcpn/dnv/declaracao_nascido_vivo_dnv.pdf",
            parent_path="rcpn/dnv",
            modified_at=(datetime.now(UTC) - timedelta(days=900)).isoformat(),
        ),
        _file_entry(
            "livro_registro_nascimento_assento.pdf",
            path_relative="rcpn/_old/livro_registro_nascimento_assento.pdf",
            parent_path="rcpn/_old",
        ),
        _file_entry(
            "avulso.pdf",
            path_relative="registros/avulsos/avulso.pdf",
            parent_path="registros/avulsos",
        ),
    ]
    inv = _write_inventory(tmp_path / "inv", files)

    result = DocumentAnalyzer(
        inventory_path=inv, retention_rules=rules, include_low_priority=True
    ).run()

    temps = [c for c in result.candidates if c.rule_id.startswith("TEMP-")]
    assert temps, "Esperado pelo menos um finding TEMP-* neste cenário."

    forbidden = (
        "excluir automaticamente",
        "remover automaticamente",
        "deletar automaticamente",
        "apagar automaticamente",
        "executar descarte automaticamente",
        "descartar automaticamente",
    )
    for f in temps:
        full_text = " ".join(
            [f.title, f.description, f.recommended_action, f.evidence_summary, f.notes]
        ).lower()
        for phrase in forbidden:
            assert phrase not in full_text, f"finding {f.rule_id} contém frase proibida: {phrase!r}"
        assert "não executar descarte automático" in f.description.lower()


# ---------------------------------------------------------------------------
# 6. Coexistência com regras DIAG-* tradicionais
# ---------------------------------------------------------------------------


def test_pipeline_preserves_diag_rules_when_retention_enabled(tmp_path, block_destructive_calls):
    """Habilitar retention não suprime nenhuma regra DIAG-* já existente."""

    rules = [
        _rule(
            codigo="3-5-1-2",
            documento="Testamentos públicos",
            guarda_permanente=True,
        )
    ]
    files = [
        # Dispara DIAG-001 (senha)
        _file_entry(
            "senha_sistema.txt",
            path_relative="dados/senha_sistema.txt",
            parent_path="dados",
        ),
        # Dispara DIAG-002 (executável)
        _file_entry(
            "instalar.exe",
            path_relative="dados/instalar.exe",
            parent_path="dados",
            extension=".exe",
        ),
        # Dispara TEMP-003 (permanente em local suspeito)
        _file_entry(
            "testamento_publico.pdf",
            path_relative="notas/_old/testamento_publico.pdf",
            parent_path="notas/_old",
        ),
    ]
    inv = _write_inventory(tmp_path / "inv", files)

    result = DocumentAnalyzer(inventory_path=inv, retention_rules=rules).run()

    rule_ids = {c.rule_id for c in result.candidates}
    assert "DIAG-001" in rule_ids
    assert "DIAG-002" in rule_ids
    assert "TEMP-003" in rule_ids


# ---------------------------------------------------------------------------
# 7. Garantia estrutural: analyzer continua sem dependências de banco
# ---------------------------------------------------------------------------


def test_analyzer_module_stays_database_free():
    """A integração não pode acoplar o analyzer ao banco — retention é injetado."""

    import app.modules.audit.diagnosis.analyzer as ana_mod

    assert not hasattr(ana_mod, "Session")
    assert not hasattr(ana_mod, "AsyncSession")
    assert not hasattr(ana_mod, "get_db")
    assert not hasattr(ana_mod, "SessionLocal")
