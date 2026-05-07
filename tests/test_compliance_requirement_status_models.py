"""Testes de modelo: ComplianceRequirementStatus e history."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.compliance.enums import (
    ComplianceRequirementStatusValue,
    RequirementClassification,
    RequirementSource,
    RequirementStage,
)
from app.modules.compliance.models import (
    ComplianceRequirement,
    ComplianceRequirementStatus,
    ComplianceRequirementStatusHistory,
)


def _seed_requirement(db: Session, code: str = "MOD_ART_1") -> ComplianceRequirement:
    req = ComplianceRequirement(
        code=code,
        source=RequirementSource.PROV_213,
        article_label="Art. 1 — Model Test",
        article_text="Texto de teste de modelo.",
        classification=RequirementClassification.OBRIGATORIO_PROVIMENTO,
        stage=RequirementStage.ETAPA_1,
    )
    db.add(req)
    db.flush()
    return req


def test_status_unique_constraint_per_requirement(db_session: Session) -> None:
    req = _seed_requirement(db_session)
    now = datetime.now(UTC)
    db_session.add(
        ComplianceRequirementStatus(
            requirement_id=req.id,
            status=ComplianceRequirementStatusValue.EVIDENCE_PENDING,
            computed_at=now,
        )
    )
    db_session.flush()

    db_session.add(
        ComplianceRequirementStatus(
            requirement_id=req.id,
            status=ComplianceRequirementStatusValue.EVIDENCE_AVAILABLE,
            computed_at=now,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_status_fk_cascade_on_requirement_delete(db_session: Session) -> None:
    req = _seed_requirement(db_session, "MOD_CASCADE_1")
    now = datetime.now(UTC)
    db_session.add(
        ComplianceRequirementStatus(
            requirement_id=req.id,
            status=ComplianceRequirementStatusValue.EVIDENCE_PENDING,
            computed_at=now,
        )
    )
    db_session.add(
        ComplianceRequirementStatusHistory(
            requirement_id=req.id,
            previous_status=None,
            new_status=ComplianceRequirementStatusValue.EVIDENCE_PENDING,
            evidence_count=0,
            finding_link_count=0,
            high_risk_link_count=0,
            critical_risk_link_count=0,
            human_review_required=False,
            change_reason="first_compute",
            computed_at=now,
        )
    )
    db_session.flush()

    db_session.delete(req)
    db_session.flush()

    remaining_status = db_session.query(ComplianceRequirementStatus).count()
    remaining_history = db_session.query(ComplianceRequirementStatusHistory).count()
    assert remaining_status == 0
    assert remaining_history == 0


def test_status_history_has_no_updated_at() -> None:
    cols = {c.name for c in inspect(ComplianceRequirementStatusHistory).columns}
    assert "updated_at" not in cols, "history não deve ter updated_at"
    assert "created_at" in cols
    assert "computed_at" in cols


def test_status_human_fields_nullable() -> None:
    cols = {c.name: c for c in inspect(ComplianceRequirementStatus).columns}
    assert cols["review_note"].nullable is True
    assert cols["reviewed_by"].nullable is True
    assert cols["reviewed_at"].nullable is True


def test_status_enum_uses_native_enum_false() -> None:
    """Enum do status deve ser não-nativo, conforme padrão do módulo."""

    col = inspect(ComplianceRequirementStatus).columns["status"]
    enum_type = col.type
    assert getattr(enum_type, "native_enum", True) is False


def test_history_enum_uses_native_enum_false() -> None:
    for col_name in ("previous_status", "new_status"):
        col = inspect(ComplianceRequirementStatusHistory).columns[col_name]
        assert getattr(col.type, "native_enum", True) is False


def test_history_no_fk_to_status_table() -> None:
    """Histórico pertence ao requisito, não ao registro atual."""

    fks = ComplianceRequirementStatusHistory.__table__.foreign_keys
    target_tables = {fk.column.table.name for fk in fks}
    assert "compliance_requirement_statuses" not in target_tables
    assert "compliance_requirements" in target_tables
