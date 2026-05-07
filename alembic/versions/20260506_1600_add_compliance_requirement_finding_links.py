"""add compliance requirement finding links

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-05-06 16:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e3f4a5b6c7d8"
down_revision: str | None = "d2e3f4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ENUM_OPTS: dict = {"native_enum": False}

_LINK_SOURCE_MODULE = sa.Enum(
    "AUDIT",
    "RETENTION",
    "LGPD",
    "MANUAL",
    "EXTERNAL",
    name="compliance_link_source_module_enum",
    length=16,
    **_ENUM_OPTS,
)

_LINK_SOURCE_TYPE = sa.Enum(
    "FINDING",
    "DIAGNOSIS",
    "SIGNAL",
    "ACTION",
    "POLICY",
    "DOCUMENT",
    "MANUAL_NOTE",
    name="compliance_link_source_type_enum",
    length=24,
    **_ENUM_OPTS,
)

_LINK_RISK_LEVEL = sa.Enum(
    "INFO",
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
    name="compliance_link_risk_level_enum",
    length=16,
    **_ENUM_OPTS,
)


def upgrade() -> None:
    op.create_table(
        "compliance_requirement_finding_links",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("requirement_id", sa.Integer(), nullable=False),
        sa.Column("source_module", _LINK_SOURCE_MODULE, nullable=False),
        sa.Column("source_type", _LINK_SOURCE_TYPE, nullable=False),
        sa.Column("source_ref", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("link_reason", sa.Text(), nullable=True),
        sa.Column("risk_level", _LINK_RISK_LEVEL, nullable=True),
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
        sa.UniqueConstraint(
            "requirement_id",
            "source_module",
            "source_type",
            "source_ref",
            name="uq_compliance_requirement_finding_link_source",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("compliance_requirement_finding_links", schema=None) as batch_op:
        batch_op.create_index(
            "ix_compliance_finding_links_requirement_id", ["requirement_id"]
        )
        batch_op.create_index(
            "ix_compliance_finding_links_source_module", ["source_module"]
        )
        batch_op.create_index(
            "ix_compliance_finding_links_risk_level", ["risk_level"]
        )


def downgrade() -> None:
    with op.batch_alter_table("compliance_requirement_finding_links", schema=None) as batch_op:
        batch_op.drop_index("ix_compliance_finding_links_risk_level")
        batch_op.drop_index("ix_compliance_finding_links_source_module")
        batch_op.drop_index("ix_compliance_finding_links_requirement_id")
    op.drop_table("compliance_requirement_finding_links")
