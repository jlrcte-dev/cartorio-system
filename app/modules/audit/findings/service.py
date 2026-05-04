from __future__ import annotations

import datetime as _dt
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import CartorioException
from app.modules.audit.findings.enums import (
    AuditCategory,
    AuditOrigin,
    AuditPriority,
    AuditSeverity,
    AuditStatus,
)
from app.modules.audit.findings.models import AuditFinding
from app.modules.audit.findings.rules import (
    validate_critical_priority,
    validate_status_transition_fields,
)
from app.modules.audit.findings.schemas import (
    AuditFindingCreate,
    AuditFindingStatusUpdate,
    AuditFindingUpdate,
)

_UTC = _dt.UTC


def create_finding(db: Session, payload: AuditFindingCreate) -> AuditFinding:
    data = payload.model_dump()
    data["updated_by"] = data["created_by"]
    finding = AuditFinding(**data)
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding


def get_finding(db: Session, finding_id: int) -> AuditFinding:
    finding = db.get(AuditFinding, finding_id)
    if finding is None:
        raise CartorioException(
            message=f"Achado de auditoria {finding_id} não encontrado.",
            status_code=404,
        )
    return finding


def list_findings(
    db: Session,
    *,
    status: AuditStatus | None = None,
    severity: AuditSeverity | None = None,
    category: AuditCategory | None = None,
    priority: AuditPriority | None = None,
    origin: AuditOrigin | None = None,
    scanner_run_id: str | None = None,
    due_before: _dt.date | None = None,
    due_after: _dt.date | None = None,
    created_after: _dt.datetime | None = None,
    created_before: _dt.datetime | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[AuditFinding]:
    stmt = select(AuditFinding)
    if status is not None:
        stmt = stmt.where(AuditFinding.status == status)
    if severity is not None:
        stmt = stmt.where(AuditFinding.severity == severity)
    if category is not None:
        stmt = stmt.where(AuditFinding.category == category)
    if priority is not None:
        stmt = stmt.where(AuditFinding.priority == priority)
    if origin is not None:
        stmt = stmt.where(AuditFinding.origin == origin)
    if scanner_run_id is not None:
        stmt = stmt.where(AuditFinding.scanner_run_id == scanner_run_id)
    if due_before is not None:
        stmt = stmt.where(AuditFinding.due_date <= due_before)
    if due_after is not None:
        stmt = stmt.where(AuditFinding.due_date >= due_after)
    if created_after is not None:
        stmt = stmt.where(AuditFinding.created_at >= created_after)
    if created_before is not None:
        stmt = stmt.where(AuditFinding.created_at <= created_before)
    if q is not None and q.strip():
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            AuditFinding.title.ilike(pattern) | AuditFinding.description.ilike(pattern)
        )
    stmt = stmt.order_by(AuditFinding.created_at.desc(), AuditFinding.id.desc())
    stmt = stmt.limit(limit).offset(offset)
    return db.scalars(stmt).all()


def update_finding(
    db: Session,
    finding_id: int,
    payload: AuditFindingUpdate,
) -> AuditFinding:
    finding = get_finding(db, finding_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return finding

    # Re-validate CRITICAL rule against merged severity + priority
    new_severity = data.get("severity", finding.severity)
    new_priority = data.get("priority", finding.priority)
    new_notes = data.get("notes", finding.notes)

    try:
        validate_critical_priority(new_severity, new_priority, new_notes)
    except ValueError as exc:
        raise CartorioException(message=str(exc), status_code=422) from exc

    if "updated_by" not in data:
        data["updated_by"] = "gestor"

    for key, value in data.items():
        setattr(finding, key, value)

    db.commit()
    db.refresh(finding)
    return finding


def change_status(
    db: Session,
    finding_id: int,
    payload: AuditFindingStatusUpdate,
) -> AuditFinding:
    finding = get_finding(db, finding_id)

    # Validate status-specific fields (schemas already ran model_validator,
    # but we re-validate here in case service is called directly)
    try:
        validate_status_transition_fields(
            status=payload.status,
            resolution_summary=payload.resolution_summary,
            resolution_evidence=payload.resolution_evidence,
            dismissed_reason=payload.dismissed_reason,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise CartorioException(message=str(exc), status_code=422) from exc

    finding.status = payload.status

    # Auto-fill resolved_at when transitioning to RESOLVED.
    # When leaving RESOLVED, resolution_summary and evidence are preserved (audit trail).
    if payload.status == AuditStatus.RESOLVED:
        finding.resolved_at = payload.resolved_at or _dt.datetime.now(_UTC)

    if payload.resolution_summary is not None:
        finding.resolution_summary = payload.resolution_summary
    if payload.resolution_evidence is not None:
        finding.resolution_evidence = payload.resolution_evidence
    if payload.dismissed_reason is not None:
        finding.dismissed_reason = payload.dismissed_reason
    if payload.notes is not None:
        finding.notes = payload.notes

    finding.updated_by = payload.updated_by

    db.commit()
    db.refresh(finding)
    return finding


def archive_finding(
    db: Session,
    finding_id: int,
    notes: str,
    updated_by: str = "gestor",
) -> AuditFinding:
    """Arquiva um achado. Exige notes — não é exclusão silenciosa."""
    payload = AuditFindingStatusUpdate(
        status=AuditStatus.ARCHIVED,
        notes=notes,
        updated_by=updated_by,
    )
    return change_status(db, finding_id, payload)
