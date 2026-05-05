from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.lgpd import service
from app.modules.lgpd.enums import (
    LgpdActionCategory,
    LgpdActionPriority,
    LgpdActionStatus,
    LgpdActionType,
)
from app.modules.lgpd.schemas import (
    LgpdActionImportReport,
    LgpdActionRead,
    LgpdActionStatusHistoryRead,
    LgpdActionSummary,
    LgpdActionUpdate,
)

router = APIRouter(prefix="/lgpd", tags=["lgpd"])

DbSession = Annotated[Session, Depends(get_db)]
LimitQuery = Annotated[int, Query(ge=1, le=500)]
OffsetQuery = Annotated[int, Query(ge=0)]
StatusQuery = Annotated[LgpdActionStatus | None, Query(alias="status")]


@router.post(
    "/actions/import",
    response_model=LgpdActionImportReport,
)
async def import_actions(
    db: DbSession,
    file: Annotated[UploadFile, File(description="CSV do Plano de Ação LGPD (INOVA)")],
    created_by: Annotated[str, Query(min_length=1, max_length=64)] = "gestor",
) -> LgpdActionImportReport:
    raw = await file.read()
    return service.import_actions_from_csv(db, raw, created_by=created_by)


@router.get("/actions", response_model=list[LgpdActionRead])
def list_actions(
    db: DbSession,
    action_status: StatusQuery = None,
    category: LgpdActionCategory | None = None,
    priority: LgpdActionPriority | None = None,
    action_type: LgpdActionType | None = None,
    responsible_party: str | None = None,
    department: str | None = None,
    limit: LimitQuery = 200,
    offset: OffsetQuery = 0,
) -> list[LgpdActionRead]:
    actions = service.list_actions(
        db,
        status=action_status,
        category=category,
        priority=priority,
        action_type=action_type,
        responsible_party=responsible_party,
        department=department,
        limit=limit,
        offset=offset,
    )
    return [LgpdActionRead.model_validate(a) for a in actions]


@router.get("/actions/summary", response_model=LgpdActionSummary)
def actions_summary(db: DbSession) -> LgpdActionSummary:
    return service.compute_summary(db)


@router.get("/actions/export.csv")
def export_actions(db: DbSession) -> Response:
    csv_text = service.export_actions_csv(db)
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="lgpd_actions.csv"'},
    )


@router.get(
    "/actions/{action_code}/history",
    response_model=list[LgpdActionStatusHistoryRead],
)
def action_history(action_code: str, db: DbSession) -> list[LgpdActionStatusHistoryRead]:
    history = service.list_status_history(db, action_code)
    return [LgpdActionStatusHistoryRead.model_validate(h) for h in history]


@router.get("/actions/{action_code}", response_model=LgpdActionRead)
def get_action(action_code: str, db: DbSession) -> LgpdActionRead:
    action = service.get_action_by_code(db, action_code)
    return LgpdActionRead.model_validate(action)


@router.patch("/actions/{action_code}", response_model=LgpdActionRead)
def update_action(
    action_code: str,
    payload: LgpdActionUpdate,
    db: DbSession,
) -> LgpdActionRead:
    action = service.update_action(db, action_code, payload)
    return LgpdActionRead.model_validate(action)
