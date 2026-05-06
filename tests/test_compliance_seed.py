"""Testes do seed `matriz_v1` do módulo compliance."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.compliance.enums import (
    DeadlineUnit,
    RequirementClassification,
    RequirementSource,
    ServentiaClass,
)
from app.modules.compliance.models import (
    ComplianceEvidenceTemplate,
    CompliancePolicyDocument,
    ComplianceRequirement,
    ComplianceRequirementDeadline,
    ComplianceRequirementPolicy,
    ComplianceSeedMeta,
)
from app.modules.compliance.seed import compute_checksum, run_seed
from app.modules.compliance.seed_data import (
    SEED_DEADLINES,
    SEED_EVIDENCE_TEMPLATES,
    SEED_POLICIES,
    SEED_REQUIREMENT_POLICIES,
    SEED_REQUIREMENTS,
)


def test_seed_dataset_minimum_volumes() -> None:
    assert len(SEED_REQUIREMENTS) >= 30
    assert len(SEED_POLICIES) >= 30
    assert len(SEED_REQUIREMENT_POLICIES) >= 60
    assert len(SEED_DEADLINES) >= 80
    assert len(SEED_EVIDENCE_TEMPLATES) >= 90


def test_seed_no_duplicate_codes() -> None:
    req_codes = [r["code"] for r in SEED_REQUIREMENTS]
    pol_codes = [p["code"] for p in SEED_POLICIES]
    assert len(req_codes) == len(set(req_codes))
    assert len(pol_codes) == len(set(pol_codes))


def test_seed_links_reference_existing_codes() -> None:
    req_codes = {r["code"] for r in SEED_REQUIREMENTS}
    pol_codes = {p["code"] for p in SEED_POLICIES}
    for link in SEED_REQUIREMENT_POLICIES:
        assert link["requirement_code"] in req_codes
        assert link["policy_code"] in pol_codes


def test_seed_runs_and_persists(db_session: Session) -> None:
    meta = run_seed(db_session)
    db_session.commit()

    assert meta.seed_name == "matriz_v1"
    assert meta.seed_version == "V1.0_MAR2026"
    assert meta.data_checksum == compute_checksum()

    requirement_count = db_session.scalar(
        select(ComplianceRequirement.__table__.c.id).limit(1)  # type: ignore[arg-type]
    )
    assert requirement_count is not None

    assert db_session.query(ComplianceRequirement).count() == len(SEED_REQUIREMENTS)
    assert db_session.query(CompliancePolicyDocument).count() == len(SEED_POLICIES)
    assert db_session.query(ComplianceRequirementPolicy).count() == len(SEED_REQUIREMENT_POLICIES)
    assert db_session.query(ComplianceRequirementDeadline).count() == len(SEED_DEADLINES)
    assert db_session.query(ComplianceEvidenceTemplate).count() == len(SEED_EVIDENCE_TEMPLATES)


def test_seed_is_idempotent(db_session: Session) -> None:
    meta1 = run_seed(db_session)
    db_session.commit()
    checksum1 = meta1.data_checksum
    seeded_at1 = meta1.seeded_at

    # Segunda execução não deve duplicar nada nem alterar checksum.
    meta2 = run_seed(db_session)
    db_session.commit()

    assert meta2.id == meta1.id
    assert meta2.data_checksum == checksum1
    # Como o checksum é igual, não devemos atualizar o registro: seeded_at
    # deve permanecer o mesmo.
    assert meta2.seeded_at == seeded_at1

    assert db_session.query(ComplianceRequirement).count() == len(SEED_REQUIREMENTS)
    assert db_session.query(ComplianceRequirementPolicy).count() == len(SEED_REQUIREMENT_POLICIES)


def test_seed_meta_records_counts(db_session: Session) -> None:
    meta = run_seed(db_session)
    db_session.commit()

    assert meta.record_count_requirements == len(SEED_REQUIREMENTS)
    assert meta.record_count_policies == len(SEED_POLICIES)
    assert meta.record_count_requirement_policies == len(SEED_REQUIREMENT_POLICIES)
    assert meta.record_count_deadlines == len(SEED_DEADLINES)
    assert meta.record_count_evidence_templates == len(SEED_EVIDENCE_TEMPLATES)


def test_seed_meta_singleton(db_session: Session) -> None:
    run_seed(db_session)
    db_session.commit()
    run_seed(db_session)
    db_session.commit()
    metas = db_session.scalars(select(ComplianceSeedMeta)).all()
    assert len(metas) == 1


def test_art3_caput_has_c3_deadline_90_dias(db_session: Session) -> None:
    """Requisito explicitamente exigido pela spec da Sprint LGPD/Compliance-1."""
    run_seed(db_session)
    db_session.commit()

    req = db_session.scalar(
        select(ComplianceRequirement).where(ComplianceRequirement.code == "ART_3_CAPUT")
    )
    assert req is not None
    deadline = next(
        (d for d in req.deadlines if d.serventia_class == ServentiaClass.C3),
        None,
    )
    assert deadline is not None
    assert deadline.value == 90
    assert deadline.unit == DeadlineUnit.DIAS


def test_art_6_i_classification_is_lgpd_obligation(db_session: Session) -> None:
    """Art. 6º I usa source PROV_213, mas é obrigação LGPD."""
    run_seed(db_session)
    db_session.commit()

    req = db_session.scalar(
        select(ComplianceRequirement).where(ComplianceRequirement.code == "ART_6_I")
    )
    assert req is not None
    assert req.source == RequirementSource.PROV_213
    assert req.classification == RequirementClassification.OBRIGATORIO_LGPD


def test_anexo_iii_uses_anexo_iii_source(db_session: Session) -> None:
    run_seed(db_session)
    db_session.commit()

    req = db_session.scalar(
        select(ComplianceRequirement).where(ComplianceRequirement.code == "ANEXO_III_4_8")
    )
    assert req is not None
    assert req.source == RequirementSource.ANEXO_III


def test_checksum_changes_when_data_changes(monkeypatch) -> None:
    from app.modules.compliance import seed as seed_module

    base = compute_checksum()
    extra_req = {
        "code": "TEST_FAKE_REQ",
        "source": RequirementSource.MATRIZ_INOVA,
        "article_label": "Test",
        "article_text": "Test article",
        "classification": RequirementClassification.COMPLEMENTAR_GOVERNANCA,
        "stage": seed_module.SEED_REQUIREMENTS[0]["stage"],
        "notes": None,
    }
    monkeypatch.setattr(
        seed_module,
        "SEED_REQUIREMENTS",
        [*seed_module.SEED_REQUIREMENTS, extra_req],
    )
    other = compute_checksum()
    assert other != base
