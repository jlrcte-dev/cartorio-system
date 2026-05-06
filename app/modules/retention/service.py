"""Serviço de avaliação de temporalidade — read-only, sem persistência.

SAFETY CONTRACT
---------------
- Não lê conteúdo de arquivos.
- Não move, exclui, renomeia ou altera arquivos.
- Não persiste avaliações (Sprint retention-1A).
- Toda avaliação é apenas indicativa e exige validação humana.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.modules.retention import repository
from app.modules.retention import rules as rule_heuristics
from app.modules.retention.enums import (
    RetentionDestination,
    RetentionPhaseKind,
    RetentionStatus,
)
from app.modules.retention.models import RetentionRule
from app.modules.retention.schemas import DocumentMetadata, RetentionEvaluation

_ADVISORY = (
    "candidato à revisão de temporalidade — exige avaliação humana. "
    "Não executar descarte automático. "
    "Validar com responsável jurídico/administrativo."
)


def _now() -> datetime:
    return datetime.now(UTC)


def _rule_destination(rule: RetentionRule) -> RetentionDestination:
    if rule.guarda_permanente:
        return RetentionDestination.PERMANENT
    if rule.eliminacao and (rule.requer_microfilmagem or rule.requer_digitalizacao):
        return RetentionDestination.DISPOSAL_REQUIRES_MEDIA
    if rule.eliminacao:
        return RetentionDestination.DISPOSAL_AFTER_TERM
    return RetentionDestination.UNDETERMINED


def _phase_duration(rule: RetentionRule) -> timedelta | None:
    if rule.fase_corrente_kind != RetentionPhaseKind.DURATION:
        return None
    years = rule.fase_corrente_years or 0
    months = rule.fase_corrente_months or 0
    if years == 0 and months == 0:
        return None
    return timedelta(days=years * 365 + months * 30)


def evaluate_document(
    metadata: DocumentMetadata,
    rules: list[RetentionRule],
    *,
    now: datetime | None = None,
) -> RetentionEvaluation:
    """Avalia um documento contra a lista de regras (em memória).

    Não persiste o resultado. Não recomenda descarte.
    """

    current_time = now or _now()

    if metadata.legal_hold:
        return RetentionEvaluation(
            document_name=metadata.name,
            document_path=metadata.path_relative,
            status=RetentionStatus.BLOCKED_BY_LEGAL_HOLD,
            destination=RetentionDestination.UNDETERMINED,
            message=(
                "Documento sob legal hold — qualquer avaliação de prazo fica suspensa. "
                "Exige avaliação humana."
            ),
            advisory=_ADVISORY,
        )

    matched = rule_heuristics.match_rule(metadata.name, metadata.path_relative, rules)

    if matched is None:
        return RetentionEvaluation(
            document_name=metadata.name,
            document_path=metadata.path_relative,
            status=RetentionStatus.NEEDS_CLASSIFICATION,
            destination=RetentionDestination.UNDETERMINED,
            message=(
                "Documento sem classificação de temporalidade — "
                "candidato à revisão de temporalidade. "
                "Não executar descarte automático."
            ),
            advisory=_ADVISORY,
        )

    destination = _rule_destination(matched)
    requires_media = matched.requer_microfilmagem or matched.requer_digitalizacao

    if matched.guarda_permanente:
        return RetentionEvaluation(
            document_name=metadata.name,
            document_path=metadata.path_relative,
            matched_rule_codigo=matched.codigo,
            matched_rule_documento=matched.documento,
            status=RetentionStatus.PERMANENT,
            destination=destination,
            requires_media_before_disposal=requires_media,
            message=(
                f"Documento de guarda permanente conforme regra {matched.codigo}. "
                "Não executar descarte automático."
            ),
            advisory=_ADVISORY,
        )

    duration = _phase_duration(matched)
    if duration is None or metadata.modified_at is None:
        return RetentionEvaluation(
            document_name=metadata.name,
            document_path=metadata.path_relative,
            matched_rule_codigo=matched.codigo,
            matched_rule_documento=matched.documento,
            status=RetentionStatus.ACTIVE,
            destination=destination,
            requires_media_before_disposal=requires_media,
            message=(
                f"Documento associado à regra {matched.codigo}; "
                "prazo de fase corrente não pôde ser calculado a partir dos metadados. "
                "Exige avaliação humana."
            ),
            advisory=_ADVISORY,
        )

    expires_at = metadata.modified_at + duration
    is_overdue = current_time >= expires_at
    if is_overdue:
        overdue_by = (current_time - expires_at).days
        return RetentionEvaluation(
            document_name=metadata.name,
            document_path=metadata.path_relative,
            matched_rule_codigo=matched.codigo,
            matched_rule_documento=matched.documento,
            status=RetentionStatus.EXPIRED_REVIEW_REQUIRED,
            destination=destination,
            is_overdue=True,
            overdue_by_days=overdue_by,
            requires_media_before_disposal=requires_media,
            message=(
                f"Documento com prazo potencialmente vencido conforme regra "
                f"{matched.codigo} ({matched.fase_corrente_text}). "
                "Candidato à revisão de temporalidade — exige avaliação humana. "
                "Não executar descarte automático."
            ),
            advisory=_ADVISORY,
        )

    return RetentionEvaluation(
        document_name=metadata.name,
        document_path=metadata.path_relative,
        matched_rule_codigo=matched.codigo,
        matched_rule_documento=matched.documento,
        status=RetentionStatus.ACTIVE,
        destination=destination,
        requires_media_before_disposal=requires_media,
        message=(
            f"Documento dentro do prazo de fase corrente da regra {matched.codigo} "
            f"({matched.fase_corrente_text})."
        ),
        advisory=_ADVISORY,
    )


def load_rules(session: Session) -> list[RetentionRule]:
    return repository.list_all(session)
