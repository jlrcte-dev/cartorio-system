"""add retention rules

Revision ID: b8e2d3f4a6c7
Revises: a7f1c2d3e4b5
Create Date: 2026-05-05 11:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8e2d3f4a6c7"
down_revision: str | None = "a7f1c2d3e4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ENUM_OPTS: dict = {"native_enum": False}


def upgrade() -> None:
    op.create_table(
        "retention_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(length=32), nullable=False),
        sa.Column("assunto", sa.String(length=200), nullable=False),
        sa.Column("documento", sa.String(length=300), nullable=False),
        sa.Column("fase_corrente_text", sa.String(length=64), nullable=False),
        sa.Column(
            "fase_corrente_kind",
            sa.Enum(
                "PERMANENT",
                "DURATION",
                "NONE",
                name="retention_phase_kind_enum",
                length=16,
                **_ENUM_OPTS,
            ),
            nullable=False,
        ),
        sa.Column("fase_corrente_years", sa.Integer(), nullable=True),
        sa.Column("fase_corrente_months", sa.Integer(), nullable=True),
        sa.Column("fase_intermediaria_text", sa.String(length=64), nullable=True),
        sa.Column(
            "eliminacao",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "guarda_permanente",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "requer_microfilmagem",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "requer_digitalizacao",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("base_legal", sa.Text(), nullable=True),
        sa.Column("alteracoes", sa.Text(), nullable=True),
        sa.Column("source_norm", sa.String(length=64), nullable=False),
        sa.Column("source_version", sa.String(length=64), nullable=False),
        sa.Column("source_file", sa.String(length=500), nullable=False),
        sa.Column("source_code", sa.String(length=32), nullable=False),
        sa.Column("source_notes", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo", "documento", name="uq_retention_rules_codigo_documento"),
    )

    with op.batch_alter_table("retention_rules", schema=None) as batch_op:
        batch_op.create_index("ix_retention_rules_codigo", ["codigo"])
        batch_op.create_index("ix_retention_rules_assunto", ["assunto"])
        batch_op.create_index("ix_retention_rules_source_norm", ["source_norm"])


def downgrade() -> None:
    with op.batch_alter_table("retention_rules", schema=None) as batch_op:
        batch_op.drop_index("ix_retention_rules_source_norm")
        batch_op.drop_index("ix_retention_rules_assunto")
        batch_op.drop_index("ix_retention_rules_codigo")
    op.drop_table("retention_rules")
