from __future__ import annotations

from enum import StrEnum


class LgpdActionStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class LgpdActionCategory(StrEnum):
    GOVERNANCA = "GOVERNANCA"
    PREPARACAO = "PREPARACAO"
    IMPLANTACAO = "IMPLANTACAO"
    OTHER = "OTHER"


class LgpdActionType(StrEnum):
    OBRIGATORIO = "OBRIGATORIO"
    RECOMENDACAO = "RECOMENDACAO"
    OTHER = "OTHER"


class LgpdActionPriority(StrEnum):
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAIXA = "BAIXA"
    OTHER = "OTHER"


# Transições de status permitidas. Uma ação só pode mover-se para um status
# permitido ou repetir o atual. Permitimos voltar de IN_PROGRESS para PENDING
# para corrigir erros operacionais (não é uma transição comum, mas é segura).
ALLOWED_STATUS_TRANSITIONS: dict[LgpdActionStatus, frozenset[LgpdActionStatus]] = {
    LgpdActionStatus.PENDING: frozenset(
        {LgpdActionStatus.PENDING, LgpdActionStatus.IN_PROGRESS, LgpdActionStatus.COMPLETED}
    ),
    LgpdActionStatus.IN_PROGRESS: frozenset(
        {LgpdActionStatus.IN_PROGRESS, LgpdActionStatus.PENDING, LgpdActionStatus.COMPLETED}
    ),
    LgpdActionStatus.COMPLETED: frozenset(
        {LgpdActionStatus.COMPLETED, LgpdActionStatus.IN_PROGRESS}
    ),
}
