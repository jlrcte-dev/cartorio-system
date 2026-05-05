"""add lgpd actions

Revision ID: a7f1c2d3e4b5
Revises: c3d9a1b2e4f5
Create Date: 2026-05-05 10:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7f1c2d3e4b5"
down_revision: str | None = "c3d9a1b2e4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ENUM_OPTS: dict = {"native_enum": False}


def upgrade() -> None:
    op.create_table(
        "lgpd_actions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("action_code", sa.String(length=10), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "GOVERNANCA",
                "PREPARACAO",
                "IMPLANTACAO",
                "OTHER",
                name="lgpd_action_category_enum",
                length=24,
                **_ENUM_OPTS,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column(
            "action_type",
            sa.Enum(
                "OBRIGATORIO",
                "RECOMENDACAO",
                "OTHER",
                name="lgpd_action_type_enum",
                length=24,
                **_ENUM_OPTS,
            ),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Enum(
                "ALTA",
                "MEDIA",
                "BAIXA",
                "OTHER",
                name="lgpd_action_priority_enum",
                length=16,
                **_ENUM_OPTS,
            ),
            nullable=False,
        ),
        sa.Column("responsible_party", sa.String(length=100), nullable=True),
        sa.Column("planned_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completed_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "IN_PROGRESS",
                "COMPLETED",
                name="lgpd_action_status_enum",
                length=24,
                **_ENUM_OPTS,
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("original_status", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=False, server_default="gestor"),
        sa.Column("updated_by", sa.String(length=64), nullable=False, server_default="gestor"),
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
        sa.UniqueConstraint("action_code", name="uq_lgpd_actions_action_code"),
    )

    with op.batch_alter_table("lgpd_actions", schema=None) as batch_op:
        batch_op.create_index("ix_lgpd_actions_action_code", ["action_code"])
        batch_op.create_index("ix_lgpd_actions_status", ["status"])
        batch_op.create_index("ix_lgpd_actions_category", ["category"])
        batch_op.create_index("ix_lgpd_actions_priority", ["priority"])
        batch_op.create_index("ix_lgpd_actions_action_type", ["action_type"])
        batch_op.create_index("ix_lgpd_actions_responsible_party", ["responsible_party"])
        batch_op.create_index("ix_lgpd_actions_department", ["department"])

    op.create_table(
        "lgpd_action_status_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("action_id", sa.Integer(), nullable=False),
        sa.Column(
            "previous_status",
            sa.Enum(
                "PENDING",
                "IN_PROGRESS",
                "COMPLETED",
                name="lgpd_action_history_prev_status_enum",
                length=24,
                **_ENUM_OPTS,
            ),
            nullable=False,
        ),
        sa.Column(
            "new_status",
            sa.Enum(
                "PENDING",
                "IN_PROGRESS",
                "COMPLETED",
                name="lgpd_action_history_new_status_enum",
                length=24,
                **_ENUM_OPTS,
            ),
            nullable=False,
        ),
        sa.Column("changed_by", sa.String(length=64), nullable=False, server_default="gestor"),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["action_id"],
            ["lgpd_actions.id"],
            ondelete="CASCADE",
            name="fk_lgpd_action_status_history_action_id",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("lgpd_action_status_history", schema=None) as batch_op:
        batch_op.create_index("ix_lgpd_action_status_history_action_id", ["action_id"])
        batch_op.create_index("ix_lgpd_action_status_history_changed_at", ["changed_at"])


def downgrade() -> None:
    with op.batch_alter_table("lgpd_action_status_history", schema=None) as batch_op:
        batch_op.drop_index("ix_lgpd_action_status_history_changed_at")
        batch_op.drop_index("ix_lgpd_action_status_history_action_id")

    op.drop_table("lgpd_action_status_history")

    with op.batch_alter_table("lgpd_actions", schema=None) as batch_op:
        batch_op.drop_index("ix_lgpd_actions_department")
        batch_op.drop_index("ix_lgpd_actions_responsible_party")
        batch_op.drop_index("ix_lgpd_actions_action_type")
        batch_op.drop_index("ix_lgpd_actions_priority")
        batch_op.drop_index("ix_lgpd_actions_category")
        batch_op.drop_index("ix_lgpd_actions_status")
        batch_op.drop_index("ix_lgpd_actions_action_code")

    op.drop_table("lgpd_actions")
