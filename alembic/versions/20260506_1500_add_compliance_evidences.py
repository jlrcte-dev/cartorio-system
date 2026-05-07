"""add compliance evidences

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4b5a6
Create Date: 2026-05-06 15:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d2e3f4a5b6c7"
down_revision: str | None = "c1d2e3f4b5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ENUM_OPTS: dict = {"native_enum": False}

_EVIDENCE_TYPE = sa.Enum(
    "DOCUMENT",
    "POLICY",
    "REPORT",
    "SCREENSHOT",
    "LOG",
    "DECLARATION",
    "CONTRACT",
    "CERTIFICATE",
    "MEETING_MINUTES",
    "CONFIGURATION",
    "EXTERNAL_REFERENCE",
    "OTHER",
    name="compliance_evidence_type_enum",
    length=24,
    **_ENUM_OPTS,
)

_EVIDENCE_STATUS = sa.Enum(
    "COLLECTED",
    "UNDER_REVIEW",
    "ACCEPTED",
    "REJECTED",
    "EXPIRED",
    "NEEDS_UPDATE",
    name="compliance_evidence_status_enum",
    length=24,
    **_ENUM_OPTS,
)

_EVIDENCE_SOURCE_MODULE = sa.Enum(
    "MANUAL",
    "EXTERNAL",
    "AUDIT",
    "RETENTION",
    "LGPD",
    "SYSTEM",
    name="compliance_evidence_source_module_enum",
    length=16,
    **_ENUM_OPTS,
)


def upgrade() -> None:
    op.create_table(
        "compliance_evidences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("requirement_id", sa.Integer(), nullable=False),
        sa.Column("evidence_template_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence_type", _EVIDENCE_TYPE, nullable=False),
        sa.Column(
            "status",
            _EVIDENCE_STATUS,
            nullable=False,
            server_default=sa.text("'COLLECTED'"),
        ),
        sa.Column(
            "source_module",
            _EVIDENCE_SOURCE_MODULE,
            nullable=False,
            server_default=sa.text("'MANUAL'"),
        ),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("source_ref", sa.String(length=200), nullable=True),
        sa.Column("file_reference", sa.String(length=500), nullable=True),
        sa.Column("responsible_name", sa.String(length=200), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["compliance_requirements.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_template_id"],
            ["compliance_evidence_templates.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("compliance_evidences", schema=None) as batch_op:
        batch_op.create_index("ix_compliance_evidences_requirement_id", ["requirement_id"])
        batch_op.create_index("ix_compliance_evidences_template_id", ["evidence_template_id"])
        batch_op.create_index("ix_compliance_evidences_status", ["status"])
        batch_op.create_index("ix_compliance_evidences_source", ["source_module"])
        batch_op.create_index("ix_compliance_evidences_collected_at", ["collected_at"])


def downgrade() -> None:
    with op.batch_alter_table("compliance_evidences", schema=None) as batch_op:
        batch_op.drop_index("ix_compliance_evidences_collected_at")
        batch_op.drop_index("ix_compliance_evidences_source")
        batch_op.drop_index("ix_compliance_evidences_status")
        batch_op.drop_index("ix_compliance_evidences_template_id")
        batch_op.drop_index("ix_compliance_evidences_requirement_id")
    op.drop_table("compliance_evidences")
