"""finance core hardening - direction source audit

Revision ID: b377f12ba37a
Revises: 8857af05ac59
Create Date: 2026-05-01 13:36:48.868340

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b377f12ba37a"
down_revision: str | None = "8857af05ac59"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SOURCE_ENUM = sa.Enum(
    "MANUAL",
    "IMPORT_XLSX",
    "ENGEGRAPH_EXPORT",
    "BANK_STATEMENT",
    "ACCOUNTING",
    "OTHER",
    name="entry_source_enum",
    native_enum=False,
    length=24,
)
DIRECTION_ENUM = sa.Enum(
    "INFLOW",
    "OUTFLOW",
    name="entry_direction_enum",
    native_enum=False,
    length=16,
)


def upgrade() -> None:
    # 1) Adiciona colunas novas em modo permissivo (direction nullable; created/updated_by com default).
    with op.batch_alter_table("financial_entries", schema=None) as batch_op:
        batch_op.add_column(sa.Column("direction", sa.String(length=16), nullable=True))
        batch_op.add_column(
            sa.Column(
                "created_by",
                sa.String(length=64),
                server_default="gestor",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_by",
                sa.String(length=64),
                server_default="gestor",
                nullable=False,
            )
        )

    # 2) Backfill direction conforme regra por entry_type.
    op.execute(
        "UPDATE financial_entries SET direction = 'INFLOW' "
        "WHERE entry_type = 'RECEITA' AND direction IS NULL"
    )
    op.execute(
        "UPDATE financial_entries SET direction = 'OUTFLOW' "
        "WHERE entry_type IN ('DESPESA', 'REPASSE') AND direction IS NULL"
    )
    # AJUSTE pré-existente sem direction → assume INFLOW como padrão seguro;
    # gestor pode reclassificar manualmente.
    op.execute(
        "UPDATE financial_entries SET direction = 'INFLOW' "
        "WHERE entry_type = 'AJUSTE' AND direction IS NULL"
    )

    # 3) Backfill source: qualquer texto fora do enum vira MANUAL; NULL vira MANUAL.
    op.execute(
        "UPDATE financial_entries SET source = 'MANUAL' "
        "WHERE source IS NULL OR source NOT IN "
        "('MANUAL', 'IMPORT_XLSX', 'ENGEGRAPH_EXPORT', 'BANK_STATEMENT', "
        "'ACCOUNTING', 'OTHER')"
    )

    # 4) Aperta as restrições: direction NOT NULL + tipo Enum, source NOT NULL + tipo Enum,
    #    cria index em direction.
    with op.batch_alter_table("financial_entries", schema=None) as batch_op:
        batch_op.alter_column(
            "direction",
            existing_type=sa.String(length=16),
            type_=DIRECTION_ENUM,
            existing_nullable=True,
            nullable=False,
        )
        batch_op.alter_column(
            "source",
            existing_type=sa.VARCHAR(length=64),
            type_=SOURCE_ENUM,
            existing_nullable=True,
            nullable=False,
            server_default="MANUAL",
        )
        batch_op.create_index(
            batch_op.f("ix_financial_entries_direction"),
            ["direction"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("financial_entries", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_financial_entries_direction"))
        batch_op.alter_column(
            "source",
            existing_type=SOURCE_ENUM,
            type_=sa.VARCHAR(length=64),
            existing_nullable=False,
            nullable=True,
            server_default=None,
        )
        batch_op.drop_column("updated_by")
        batch_op.drop_column("created_by")
        batch_op.drop_column("direction")
