from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.retention.models import RetentionRule
from app.modules.retention.schemas import RetentionRuleIn


def list_all(session: Session) -> list[RetentionRule]:
    return list(session.scalars(select(RetentionRule).order_by(RetentionRule.codigo)).all())


def get_by_codigo_documento(session: Session, codigo: str, documento: str) -> RetentionRule | None:
    stmt = select(RetentionRule).where(
        RetentionRule.codigo == codigo,
        RetentionRule.documento == documento,
    )
    return session.scalars(stmt).first()


def get_by_codigo(session: Session, codigo: str) -> list[RetentionRule]:
    stmt = select(RetentionRule).where(RetentionRule.codigo == codigo)
    return list(session.scalars(stmt).all())


def upsert(session: Session, payload: RetentionRuleIn) -> RetentionRule:
    """Idempotente. Chave: (codigo, documento)."""

    existing = get_by_codigo_documento(session, payload.codigo, payload.documento)
    if existing is None:
        rule = RetentionRule(**payload.model_dump())
        session.add(rule)
        session.flush()
        return rule

    for field, value in payload.model_dump().items():
        setattr(existing, field, value)
    session.flush()
    return existing


def count(session: Session) -> int:
    from sqlalchemy import func

    return int(session.scalar(select(func.count()).select_from(RetentionRule)) or 0)
