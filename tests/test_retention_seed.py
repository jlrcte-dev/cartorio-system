from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from app.modules.retention import repository, seed


@pytest.fixture
def block_destructive_calls(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("Operação destrutiva detectada — seed deve ser read-only")

    monkeypatch.setattr(os, "remove", fail)
    monkeypatch.setattr(os, "unlink", fail)
    monkeypatch.setattr(shutil, "move", fail)
    monkeypatch.setattr(shutil, "rmtree", fail)
    monkeypatch.setattr(Path, "unlink", fail)
    monkeypatch.setattr(Path, "rename", fail)
    yield


def test_seed_population_count(db_session, block_destructive_calls):
    result = seed.run(db_session)
    db_session.commit()

    assert result["rules_in_seed"] == len(seed.SEED_RULES)
    assert 15 <= result["count_after"] <= 25
    assert result["count_after"] == len(seed.SEED_RULES)


def test_seed_is_idempotent(db_session, block_destructive_calls):
    first = seed.run(db_session)
    db_session.commit()
    second = seed.run(db_session)
    db_session.commit()

    assert first["count_after"] == second["count_after"]
    assert repository.count(db_session) == len(seed.SEED_RULES)


def test_seed_preserves_normative_provenance(db_session, block_destructive_calls):
    seed.run(db_session)
    db_session.commit()

    rules = repository.list_all(db_session)
    assert rules, "seed deve persistir pelo menos uma regra"
    for rule in rules:
        assert rule.source_norm == "PROVIMENTO_CNJ_50_2015"
        assert rule.source_version == "COMPILADO_LOCAL"
        assert rule.source_file == seed.SOURCE_FILE
        assert rule.source_code == rule.codigo
        assert rule.source_notes is not None
        assert "validad" in rule.source_notes.lower()


def test_seed_covers_required_scenarios(db_session, block_destructive_calls):
    seed.run(db_session)
    db_session.commit()
    rules = repository.list_all(db_session)

    has_permanent = any(r.guarda_permanente for r in rules)
    has_1y = any(r.fase_corrente_years == 1 for r in rules)
    has_5y = any(r.fase_corrente_years == 5 for r in rules)
    has_10y = any(r.fase_corrente_years == 10 for r in rules)
    has_media = any(r.requer_digitalizacao or r.requer_microfilmagem for r in rules)
    has_rcpn = any("Pessoas Naturais" in r.assunto for r in rules)
    has_notas = any("Notas" in r.assunto for r in rules)
    has_comuns = any("Comuns" in r.assunto or "administrativos" in r.assunto for r in rules)

    assert has_permanent, "deve cobrir guarda permanente"
    assert has_1y, "deve cobrir prazo de 1 ano"
    assert has_5y, "deve cobrir prazo de 5 anos"
    assert has_10y, "deve cobrir prazo de 10 anos"
    assert has_media, "deve cobrir eliminação dependente de digitalização/microfilmagem"
    assert has_rcpn, "deve cobrir RCPN"
    assert has_notas, "deve cobrir Ofício de Notas"
    assert has_comuns, "deve cobrir documentos comuns/administrativos"


def test_seed_uses_unique_codigo_documento(db_session, block_destructive_calls):
    seed.run(db_session)
    db_session.commit()
    rules = repository.list_all(db_session)
    keys = {(r.codigo, r.documento) for r in rules}
    assert len(keys) == len(rules), "chave (codigo, documento) deve ser única"
