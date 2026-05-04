from __future__ import annotations

import datetime as _dt
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.audit.findings import service
from app.modules.audit.findings.enums import (
    AuditCategory,
    AuditOrigin,
    AuditPriority,
    AuditSeverity,
    AuditStatus,
)
from app.modules.audit.findings.schemas import (
    AuditFindingCreate,
    AuditFindingRead,
    AuditFindingStatusUpdate,
    AuditFindingUpdate,
)

router = APIRouter(prefix="/audit/findings", tags=["audit"])

DbSession = Annotated[Session, Depends(get_db)]

LimitQuery = Annotated[int, Query(ge=1, le=200)]
OffsetQuery = Annotated[int, Query(ge=0)]
StatusQuery = Annotated[AuditStatus | None, Query(alias="status")]
_ARCHIVE_DESC = "Justificativa obrigatória para arquivamento"
NotesQuery = Annotated[str, Query(min_length=1, description=_ARCHIVE_DESC)]
UpdatedByQuery = Annotated[str, Query(min_length=1, max_length=64)]


class _ArchiveBody:
    """Corpo mínimo para arquivamento."""

    def __init__(self, notes: str, updated_by: str = "gestor") -> None:
        self.notes = notes
        self.updated_by = updated_by


@router.post(
    "",
    response_model=AuditFindingRead,
    status_code=status.HTTP_201_CREATED,
)
def create_finding(
    payload: AuditFindingCreate,
    db: DbSession,
) -> AuditFindingRead:
    finding = service.create_finding(db, payload)
    return AuditFindingRead.model_validate(finding)


@router.get("", response_model=list[AuditFindingRead])
def list_findings(
    db: DbSession,
    finding_status: StatusQuery = None,
    severity: AuditSeverity | None = None,
    category: AuditCategory | None = None,
    priority: AuditPriority | None = None,
    origin: AuditOrigin | None = None,
    scanner_run_id: str | None = None,
    due_before: _dt.date | None = None,
    due_after: _dt.date | None = None,
    created_after: _dt.datetime | None = None,
    created_before: _dt.datetime | None = None,
    q: str | None = Query(default=None, max_length=200),
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> list[AuditFindingRead]:
    findings = service.list_findings(
        db,
        status=finding_status,
        severity=severity,
        category=category,
        priority=priority,
        origin=origin,
        scanner_run_id=scanner_run_id,
        due_before=due_before,
        due_after=due_after,
        created_after=created_after,
        created_before=created_before,
        q=q,
        limit=limit,
        offset=offset,
    )
    return [AuditFindingRead.model_validate(f) for f in findings]


@router.get("/{finding_id}", response_model=AuditFindingRead)
def get_finding(finding_id: int, db: DbSession) -> AuditFindingRead:
    finding = service.get_finding(db, finding_id)
    return AuditFindingRead.model_validate(finding)


@router.patch("/{finding_id}", response_model=AuditFindingRead)
def update_finding(
    finding_id: int,
    payload: AuditFindingUpdate,
    db: DbSession,
) -> AuditFindingRead:
    finding = service.update_finding(db, finding_id, payload)
    return AuditFindingRead.model_validate(finding)


@router.post("/{finding_id}/status", response_model=AuditFindingRead)
def change_status(
    finding_id: int,
    payload: AuditFindingStatusUpdate,
    db: DbSession,
) -> AuditFindingRead:
    finding = service.change_status(db, finding_id, payload)
    return AuditFindingRead.model_validate(finding)


@router.post("/{finding_id}/archive", response_model=AuditFindingRead)
def archive_finding(
    finding_id: int,
    db: DbSession,
    notes: NotesQuery,
    updated_by: UpdatedByQuery = "gestor",
) -> AuditFindingRead:
    finding = service.archive_finding(db, finding_id, notes=notes, updated_by=updated_by)
    return AuditFindingRead.model_validate(finding)
