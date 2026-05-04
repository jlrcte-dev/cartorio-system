"""Regras de domínio do AuditFinding.

Centraliza validações cruzadas para que schemas Pydantic (criação/atualização)
e service (mudança de status) usem a mesma fonte de verdade.
"""

from __future__ import annotations

from app.modules.audit.findings.enums import (
    CRITICAL_REQUIRED_PRIORITIES,
    AuditPriority,
    AuditSeverity,
    AuditStatus,
)


def validate_critical_priority(
    severity: AuditSeverity,
    priority: AuditPriority,
    notes: str | None,
) -> None:
    """Achado CRITICAL exige priority IMMEDIATE ou SEVEN_DAYS.

    Permite desvio quando notes fornece justificativa explícita.
    """
    is_critical = severity == AuditSeverity.CRITICAL
    if is_critical and priority not in CRITICAL_REQUIRED_PRIORITIES and not notes:
        raise ValueError(
            "Achado CRITICAL exige priority IMMEDIATE ou SEVEN_DAYS. "
            "Para usar outra prioridade, informe justificativa em notes."
        )


def validate_resolved_fields(
    resolution_summary: str | None,
    resolution_evidence: str | None,
    notes: str | None,
) -> None:
    """status RESOLVED exige resolution_summary e ao menos uma evidência de encerramento."""
    if not resolution_summary:
        raise ValueError("status RESOLVED exige resolution_summary")
    if not resolution_evidence and not notes:
        raise ValueError(
            "status RESOLVED exige resolution_evidence ou notes como evidência de resolução"
        )


def validate_dismissed_fields(
    dismissed_reason: str | None,
    resolution_summary: str | None,
) -> None:
    """status DISMISSED exige dismissed_reason ou resolution_summary."""
    if not dismissed_reason and not resolution_summary:
        raise ValueError("status DISMISSED exige dismissed_reason ou resolution_summary")


def validate_archived_fields(notes: str | None) -> None:
    """status ARCHIVED exige notes justificando o arquivamento."""
    if not notes:
        raise ValueError(
            "status ARCHIVED exige notes justificando o arquivamento. "
            "Não use ARCHIVED como exclusão silenciosa."
        )


def validate_status_transition_fields(
    *,
    status: AuditStatus,
    resolution_summary: str | None,
    resolution_evidence: str | None,
    dismissed_reason: str | None,
    notes: str | None,
) -> None:
    """Verifica os campos obrigatórios para a transição de status informada."""
    if status == AuditStatus.RESOLVED:
        validate_resolved_fields(resolution_summary, resolution_evidence, notes)
    elif status == AuditStatus.DISMISSED:
        validate_dismissed_fields(dismissed_reason, resolution_summary)
    elif status == AuditStatus.ARCHIVED:
        validate_archived_fields(notes)
