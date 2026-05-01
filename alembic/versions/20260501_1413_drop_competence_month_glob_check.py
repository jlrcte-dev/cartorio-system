"""drop competence_month glob check

Revision ID: 455f4efec848
Revises: b377f12ba37a
Create Date: 2026-05-01 14:13:21.030120

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "455f4efec848"
down_revision: str | None = "b377f12ba37a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CHECK_NAME = "ck_financial_entries_competence_month_format"
CHECK_SQL = "competence_month GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]'"


def upgrade() -> None:
    """Remove a CheckConstraint específica de SQLite (GLOB).

    A validação de formato `YYYY-MM` agora é responsabilidade exclusiva do
    Pydantic. Isso é essencial para portabilidade futura para Postgres, que
    não suporta o operador GLOB.
    """
    with op.batch_alter_table("financial_entries", schema=None) as batch_op:
        batch_op.drop_constraint(CHECK_NAME, type_="check")


def downgrade() -> None:
    with op.batch_alter_table("financial_entries", schema=None) as batch_op:
        batch_op.create_check_constraint(CHECK_NAME, CHECK_SQL)
