"""add audit findings

Revision ID: c3d9a1b2e4f5
Revises: 455f4efec848
Create Date: 2026-05-04 09:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d9a1b2e4f5"
down_revision: str | None = "455f4efec848"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ENUM_OPTS: dict = {"native_enum": False}


def upgrade() -> None:
    op.create_table(
        "audit_findings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        # --- Obrigatórios ---
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "INFRASTRUCTURE",
                "BACKUP",
                "ACCESS_CONTROL",
                "NETWORK",
                "ENDPOINT_SECURITY",
                "DOCUMENT_MANAGEMENT",
                "OPERATIONAL_FLOW",
                "POLICY_DOCUMENT",
                "COMPLIANCE",
                "VENDOR",
                "FINANCE",
                "SYSTEM",
                "OTHER",
                name="audit_category_enum",
                length=32,
                **_ENUM_OPTS,
            ),
            nullable=False,
        ),
        sa.Column(
            "origin",
            sa.Enum(
                "MANUAL",
                "SCANNER",
                "TECHNICAL_REPORT",
                "CHECKLIST",
                "INTERVIEW",
                "CNJ_MAPPING",
                "BACKUP_LOG",
                "DISK_SCAN",
                "NETWORK_REVIEW",
                "POLICY_REVIEW",
                "OTHER",
                name="audit_origin_enum",
                length=32,
                **_ENUM_OPTS,
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum(
                "CRITICAL",
                "HIGH",
                "MEDIUM",
                "LOW",
                "INFORMATIONAL",
                name="audit_severity_enum",
                length=24,
                **_ENUM_OPTS,
            ),
            nullable=False,
        ),
        sa.Column(
            "probability",
            sa.Enum(
                "HIGH",
                "MEDIUM_HIGH",
                "MEDIUM",
                "LOW",
                "UNKNOWN",
                name="audit_probability_enum",
                length=24,
                **_ENUM_OPTS,
            ),
            nullable=False,
        ),
        sa.Column(
            "impact",
            sa.Enum(
                "CRITICAL",
                "HIGH",
                "MEDIUM",
                "LOW",
                "UNKNOWN",
                name="audit_impact_enum",
                length=24,
                **_ENUM_OPTS,
            ),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Enum(
                "IMMEDIATE",
                "SEVEN_DAYS",
                "THIRTY_DAYS",
                "NINETY_DAYS",
                "BACKLOG",
                name="audit_priority_enum",
                length=24,
                **_ENUM_OPTS,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "OPEN",
                "IN_PROGRESS",
                "WAITING_VALIDATION",
                "RESOLVED",
                "DISMISSED",
                "ARCHIVED",
                name="audit_status_enum",
                length=24,
                **_ENUM_OPTS,
            ),
            nullable=False,
            server_default="OPEN",
        ),
        sa.Column("evidence_summary", sa.Text(), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        # --- Opcionais ---
        sa.Column("finding_code", sa.String(length=32), nullable=True),
        sa.Column("evidence_source", sa.String(length=500), nullable=True),
        sa.Column("evidence_reference", sa.String(length=500), nullable=True),
        sa.Column("evidence_artifact_path", sa.String(length=1000), nullable=True),
        sa.Column("evidence_hash", sa.String(length=64), nullable=True),
        sa.Column("scanner_run_id", sa.String(length=36), nullable=True),
        sa.Column("related_file_path", sa.String(length=1000), nullable=True),
        sa.Column("related_entity_type", sa.String(length=64), nullable=True),
        sa.Column("related_entity_id", sa.String(length=64), nullable=True),
        sa.Column("cnj_requirement", sa.String(length=200), nullable=True),
        sa.Column("cnj_stage", sa.String(length=64), nullable=True),
        sa.Column("compliance_topic", sa.String(length=200), nullable=True),
        sa.Column("responsible_area", sa.String(length=100), nullable=True),
        sa.Column("assigned_to", sa.String(length=100), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_summary", sa.Text(), nullable=True),
        sa.Column("resolution_evidence", sa.Text(), nullable=True),
        sa.Column("dismissed_reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=False, server_default="gestor"),
        sa.Column("updated_by", sa.String(length=64), nullable=False, server_default="gestor"),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(length=64), nullable=True),
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
    )

    with op.batch_alter_table("audit_findings", schema=None) as batch_op:
        batch_op.create_index("ix_audit_findings_status", ["status"])
        batch_op.create_index("ix_audit_findings_severity", ["severity"])
        batch_op.create_index("ix_audit_findings_category", ["category"])
        batch_op.create_index("ix_audit_findings_priority", ["priority"])
        batch_op.create_index("ix_audit_findings_origin", ["origin"])
        batch_op.create_index("ix_audit_findings_scanner_run_id", ["scanner_run_id"])
        batch_op.create_index("ix_audit_findings_due_date", ["due_date"])
        batch_op.create_index("ix_audit_findings_created_at", ["created_at"])


def downgrade() -> None:
    with op.batch_alter_table("audit_findings", schema=None) as batch_op:
        batch_op.drop_index("ix_audit_findings_created_at")
        batch_op.drop_index("ix_audit_findings_due_date")
        batch_op.drop_index("ix_audit_findings_scanner_run_id")
        batch_op.drop_index("ix_audit_findings_origin")
        batch_op.drop_index("ix_audit_findings_priority")
        batch_op.drop_index("ix_audit_findings_category")
        batch_op.drop_index("ix_audit_findings_severity")
        batch_op.drop_index("ix_audit_findings_status")

    op.drop_table("audit_findings")
