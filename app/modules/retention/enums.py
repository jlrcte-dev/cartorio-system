from __future__ import annotations

from enum import StrEnum


class RetentionPhaseKind(StrEnum):
    """Tipo de prazo na fase corrente da regra de temporalidade."""

    PERMANENT = "PERMANENT"
    DURATION = "DURATION"
    NONE = "NONE"


class RetentionDestination(StrEnum):
    """Destinação prevista pela regra normativa."""

    PERMANENT = "PERMANENT"
    DISPOSAL_AFTER_TERM = "DISPOSAL_AFTER_TERM"
    DISPOSAL_REQUIRES_MEDIA = "DISPOSAL_REQUIRES_MEDIA"
    UNDETERMINED = "UNDETERMINED"


class RetentionStatus(StrEnum):
    """Status de avaliação de um documento contra a tabela de temporalidade.

    Nenhum status autoriza descarte automático. EXPIRED_REVIEW_REQUIRED apenas
    indica candidato à revisão humana.
    """

    UNKNOWN = "UNKNOWN"
    NEEDS_CLASSIFICATION = "NEEDS_CLASSIFICATION"
    ACTIVE = "ACTIVE"
    EXPIRED_REVIEW_REQUIRED = "EXPIRED_REVIEW_REQUIRED"
    PERMANENT = "PERMANENT"
    BLOCKED_BY_LEGAL_HOLD = "BLOCKED_BY_LEGAL_HOLD"


class NormSource(StrEnum):
    """Identificadores de fontes normativas suportadas."""

    PROVIMENTO_CNJ_50_2015 = "PROVIMENTO_CNJ_50_2015"


# Linguagem obrigatória para findings TEMP-* e mensagens de avaliação.
CONSERVATIVE_PHRASES = (
    "candidato à revisão de temporalidade",
    "exige avaliação humana",
    "não executar descarte automático",
    "validar com responsável jurídico/administrativo",
)
