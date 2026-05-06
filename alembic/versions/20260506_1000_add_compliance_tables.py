"""add compliance tables

Revision ID: c1d2e3f4b5a6
Revises: b8e2d3f4a6c7
Create Date: 2026-05-06 10:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c1d2e3f4b5a6"
down_revision: str | None = "b8e2d3f4a6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ENUM_OPTS: dict = {"native_enum": False}

_REQUIREMENT_SOURCE = sa.Enum(
    "PROV_213",
    "LGPD",
    "ANEXO_III",
    "ANEXO_IV",
    "MATRIZ_INOVA",
    name="compliance_requirement_source_enum",
    length=24,
    **_ENUM_OPTS,
)

_REQUIREMENT_CLASSIFICATION_VALUES = (
    "OBRIGATORIO_LGPD",
    "OBRIGATORIO_PROVIMENTO",
    "COMPLEMENTAR_BOA_PRATICA",
    "COMPLEMENTAR_GOVERNANCA",
)

_REQUIREMENT_STAGE = sa.Enum(
    "ETAPA_1",
    "ETAPA_2",
    "ETAPA_3",
    "ETAPA_3_4",
    "ETAPA_4",
    "ETAPA_5",
    "ETAPAS_1_2",
    "ETAPAS_1_5",
    "TODAS",
    "NAO_APLICAVEL",
    name="compliance_requirement_stage_enum",
    length=24,
    **_ENUM_OPTS,
)

_POLICY_KIND = sa.Enum(
    "POLITICA",
    "PROCEDIMENTO",
    "PLANO",
    "INVENTARIO",
    "DOCUMENTO",
    "DOCUMENTO_TECNICO",
    "MODELO_ATA",
    "CARTAZ",
    "FAQ",
    "GUIA",
    "OUTRO",
    name="compliance_policy_kind_enum",
    length=24,
    **_ENUM_OPTS,
)

_SERVENTIA_CLASS = sa.Enum(
    "C1",
    "C2",
    "C3",
    name="compliance_serventia_class_enum",
    length=4,
    **_ENUM_OPTS,
)

_DEADLINE_UNIT = sa.Enum(
    "DIAS",
    "MESES",
    "AO_FINAL_ETAPA",
    name="compliance_deadline_unit_enum",
    length=24,
    **_ENUM_OPTS,
)


def upgrade() -> None:
    op.create_table(
        "compliance_seed_meta",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("seed_name", sa.String(length=64), nullable=False),
        sa.Column("seed_version", sa.String(length=64), nullable=False),
        sa.Column("source_document", sa.String(length=300), nullable=False),
        sa.Column("source_file_reference", sa.String(length=500), nullable=False),
        sa.Column(
            "record_count_requirements",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "record_count_policies",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "record_count_requirement_policies",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "record_count_deadlines",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "record_count_evidence_templates",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("data_checksum", sa.String(length=128), nullable=False),
        sa.Column(
            "seeded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "seeded_by",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'gestor'"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("seed_name", name="uq_compliance_seed_meta_name"),
    )
    with op.batch_alter_table("compliance_seed_meta", schema=None) as batch_op:
        batch_op.create_index("ix_compliance_seed_meta_seed_name", ["seed_name"], unique=True)

    op.create_table(
        "compliance_requirements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("source", _REQUIREMENT_SOURCE, nullable=False),
        sa.Column("article_label", sa.String(length=120), nullable=False),
        sa.Column("article_text", sa.Text(), nullable=False),
        sa.Column(
            "classification",
            sa.Enum(
                *_REQUIREMENT_CLASSIFICATION_VALUES,
                name="compliance_requirement_classification_enum",
                length=32,
                **_ENUM_OPTS,
            ),
            nullable=False,
        ),
        sa.Column("stage", _REQUIREMENT_STAGE, nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_compliance_requirements_code"),
    )
    with op.batch_alter_table("compliance_requirements", schema=None) as batch_op:
        batch_op.create_index("ix_compliance_requirements_code", ["code"], unique=True)
        batch_op.create_index("ix_compliance_requirements_source", ["source"])
        batch_op.create_index("ix_compliance_requirements_classification", ["classification"])
        batch_op.create_index("ix_compliance_requirements_stage", ["stage"])

    op.create_table(
        "compliance_policies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("kind", _POLICY_KIND, nullable=False),
        sa.Column(
            "classification",
            sa.Enum(
                *_REQUIREMENT_CLASSIFICATION_VALUES,
                name="compliance_policy_classification_enum",
                length=32,
                **_ENUM_OPTS,
            ),
            nullable=False,
        ),
        sa.Column("inova_filename", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.UniqueConstraint("code", name="uq_compliance_policies_code"),
    )
    with op.batch_alter_table("compliance_policies", schema=None) as batch_op:
        batch_op.create_index("ix_compliance_policies_code", ["code"], unique=True)
        batch_op.create_index("ix_compliance_policies_kind", ["kind"])
        batch_op.create_index("ix_compliance_policies_classification", ["classification"])

    op.create_table(
        "compliance_requirement_policies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("requirement_id", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column(
            "policy_section_notes",
            sa.String(length=500),
            nullable=False,
            server_default=sa.text("''"),
        ),
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
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["compliance_policies.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "requirement_id",
            "policy_id",
            "policy_section_notes",
            name="uq_compliance_req_policy",
        ),
    )
    with op.batch_alter_table("compliance_requirement_policies", schema=None) as batch_op:
        batch_op.create_index("ix_compliance_req_policy_requirement_id", ["requirement_id"])
        batch_op.create_index("ix_compliance_req_policy_policy_id", ["policy_id"])

    op.create_table(
        "compliance_requirement_deadlines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("requirement_id", sa.Integer(), nullable=False),
        sa.Column("serventia_class", _SERVENTIA_CLASS, nullable=False),
        sa.Column("value", sa.Integer(), nullable=True),
        sa.Column("unit", _DEADLINE_UNIT, nullable=False),
        sa.Column("stage_label", sa.String(length=64), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.UniqueConstraint(
            "requirement_id",
            "serventia_class",
            name="uq_compliance_req_deadline_class",
        ),
    )
    with op.batch_alter_table("compliance_requirement_deadlines", schema=None) as batch_op:
        batch_op.create_index("ix_compliance_req_deadline_requirement_id", ["requirement_id"])

    op.create_table(
        "compliance_evidence_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("requirement_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.UniqueConstraint(
            "requirement_id",
            "sort_order",
            name="uq_compliance_evidence_template_order",
        ),
    )
    with op.batch_alter_table("compliance_evidence_templates", schema=None) as batch_op:
        batch_op.create_index("ix_compliance_evidence_template_requirement_id", ["requirement_id"])


def downgrade() -> None:
    with op.batch_alter_table("compliance_evidence_templates", schema=None) as batch_op:
        batch_op.drop_index("ix_compliance_evidence_template_requirement_id")
    op.drop_table("compliance_evidence_templates")

    with op.batch_alter_table("compliance_requirement_deadlines", schema=None) as batch_op:
        batch_op.drop_index("ix_compliance_req_deadline_requirement_id")
    op.drop_table("compliance_requirement_deadlines")

    with op.batch_alter_table("compliance_requirement_policies", schema=None) as batch_op:
        batch_op.drop_index("ix_compliance_req_policy_policy_id")
        batch_op.drop_index("ix_compliance_req_policy_requirement_id")
    op.drop_table("compliance_requirement_policies")

    with op.batch_alter_table("compliance_policies", schema=None) as batch_op:
        batch_op.drop_index("ix_compliance_policies_classification")
        batch_op.drop_index("ix_compliance_policies_kind")
        batch_op.drop_index("ix_compliance_policies_code")
    op.drop_table("compliance_policies")

    with op.batch_alter_table("compliance_requirements", schema=None) as batch_op:
        batch_op.drop_index("ix_compliance_requirements_stage")
        batch_op.drop_index("ix_compliance_requirements_classification")
        batch_op.drop_index("ix_compliance_requirements_source")
        batch_op.drop_index("ix_compliance_requirements_code")
    op.drop_table("compliance_requirements")

    with op.batch_alter_table("compliance_seed_meta", schema=None) as batch_op:
        batch_op.drop_index("ix_compliance_seed_meta_seed_name")
    op.drop_table("compliance_seed_meta")
