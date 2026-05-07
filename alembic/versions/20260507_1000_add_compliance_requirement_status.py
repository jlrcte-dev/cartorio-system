"""add compliance requirement status

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-05-07 10:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f4a5b6c7d8e9"
down_revision: str | None = "e3f4a5b6c7d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ENUM_OPTS: dict = {"native_enum": False}

_STATUS_VALUE_ENUM = sa.Enum(
    "EVIDENCE_PENDING",
    "EVIDENCE_AVAILABLE",
    "HAS_OPEN_FINDINGS",
    "NEEDS_HUMAN_REVIEW",
    "UNDER_REVIEW",
    name="compliance_requirement_status_value_enum",
    length=32,
    **_ENUM_OPTS,
)


def upgrade() -> None:
    op.create_table(
        "compliance_requirement_statuses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("requirement_id", sa.Integer(), nullable=False),
        sa.Column("status", _STATUS_VALUE_ENUM, nullable=False),
        sa.Column(
            "evidence_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "finding_link_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "high_risk_link_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "critical_risk_link_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("last_evidence_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_link_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "human_review_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("status_note", sa.String(length=500), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=200), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint(
            "requirement_id",
            name="uq_compliance_requirement_status_requirement",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("compliance_requirement_statuses", schema=None) as batch_op:
        batch_op.create_index(
            "ix_compliance_requirement_status_status", ["status"]
        )
        batch_op.create_index(
            "ix_compliance_requirement_status_human_review_required",
            ["human_review_required"],
        )
        batch_op.create_index(
            "ix_compliance_requirement_status_computed_at", ["computed_at"]
        )

    op.create_table(
        "compliance_requirement_status_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("requirement_id", sa.Integer(), nullable=False),
        sa.Column("previous_status", _STATUS_VALUE_ENUM, nullable=True),
        sa.Column("new_status", _STATUS_VALUE_ENUM, nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("finding_link_count", sa.Integer(), nullable=False),
        sa.Column("high_risk_link_count", sa.Integer(), nullable=False),
        sa.Column("critical_risk_link_count", sa.Integer(), nullable=False),
        sa.Column("human_review_required", sa.Boolean(), nullable=False),
        sa.Column("change_reason", sa.String(length=64), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["compliance_requirements.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table(
        "compliance_requirement_status_history", schema=None
    ) as batch_op:
        batch_op.create_index(
            "ix_compliance_requirement_status_history_requirement_id",
            ["requirement_id"],
        )
        batch_op.create_index(
            "ix_compliance_requirement_status_history_new_status", ["new_status"]
        )
        batch_op.create_index(
            "ix_compliance_requirement_status_history_computed_at", ["computed_at"]
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "compliance_requirement_status_history", schema=None
    ) as batch_op:
        batch_op.drop_index("ix_compliance_requirement_status_history_computed_at")
        batch_op.drop_index("ix_compliance_requirement_status_history_new_status")
        batch_op.drop_index("ix_compliance_requirement_status_history_requirement_id")
    op.drop_table("compliance_requirement_status_history")

    with op.batch_alter_table("compliance_requirement_statuses", schema=None) as batch_op:
        batch_op.drop_index("ix_compliance_requirement_status_computed_at")
        batch_op.drop_index("ix_compliance_requirement_status_human_review_required")
        batch_op.drop_index("ix_compliance_requirement_status_status")
    op.drop_table("compliance_requirement_statuses")
