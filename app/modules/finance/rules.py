"""Regras de domínio do Finance Core.

Centraliza as validações cruzadas entre campos de FinancialEntry para que tanto
os schemas Pydantic (criação) quanto o service (atualização parcial) usem a
mesma fonte de verdade.
"""

from __future__ import annotations

import datetime as _dt

from app.modules.finance.enums import (
    ALLOWED_STATUS_BY_TYPE,
    REQUIRED_DIRECTION_BY_TYPE,
    EntryDirection,
    EntryStatus,
    EntryType,
)

STATUS_REQUIRES_PAYMENT_DATE: frozenset[EntryStatus] = frozenset(
    {EntryStatus.PAID, EntryStatus.RECEIVED}
)
STATUS_FORBIDS_PAYMENT_DATE: frozenset[EntryStatus] = frozenset(
    {EntryStatus.PENDING, EntryStatus.TO_REVIEW, EntryStatus.CANCELLED}
)


def resolve_direction(entry_type: EntryType, direction: EntryDirection | None) -> EntryDirection:
    """Resolve a direction final.

    - Para tipos rígidos (RECEITA/DESPESA/REPASSE): força o valor obrigatório
      e rejeita conflito explícito.
    - Para AJUSTE: exige direction (não há default seguro).
    """
    required = REQUIRED_DIRECTION_BY_TYPE[entry_type]
    if required is not None:
        if direction is not None and direction != required:
            raise ValueError(
                f"entry_type {entry_type.value} requer direction {required.value}, "
                f"recebido {direction.value}"
            )
        return required
    if direction is None:
        raise ValueError("entry_type AJUSTE exige direction (INFLOW ou OUTFLOW)")
    return direction


def validate_status_for_type(entry_type: EntryType, status: EntryStatus) -> None:
    allowed = ALLOWED_STATUS_BY_TYPE[entry_type]
    if status not in allowed:
        allowed_names = ", ".join(sorted(s.value for s in allowed))
        raise ValueError(
            f"Status {status.value} não é válido para entry_type {entry_type.value}. "
            f"Permitidos: {allowed_names}"
        )


def validate_payment_date_for_status(status: EntryStatus, payment_date: _dt.date | None) -> None:
    """Garante coerência entre status e payment_date.

    - PAID/RECEIVED: payment_date obrigatório.
    - PENDING/TO_REVIEW/CANCELLED: payment_date deve ser nulo.
    """
    if status in STATUS_REQUIRES_PAYMENT_DATE and payment_date is None:
        raise ValueError(f"status {status.value} exige payment_date preenchido")
    if status in STATUS_FORBIDS_PAYMENT_DATE and payment_date is not None:
        raise ValueError(f"status {status.value} não admite payment_date (deve ser nulo)")
