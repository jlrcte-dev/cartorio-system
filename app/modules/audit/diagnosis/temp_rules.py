"""TEMP-* — findings de temporalidade documental.

Sprint retention-1A: implementação inicial das regras como funções puras.
Sprint retention-1B: integração no pipeline principal de DocumentDiagnosis
    (via ``DocumentAnalyzer(retention_rules=...)``). A integração permanece
    opcional: quando o chamador não injeta regras, nenhum finding TEMP-* é
    emitido.

SAFETY CONTRACT
---------------
- Nenhuma função aqui lê conteúdo de arquivo.
- Nenhuma função executa, autoriza ou recomenda descarte.
- Apenas inspeciona metadados (nome, caminho, timestamps).
- Saídas usam linguagem conservadora obrigatória:
    * "candidato à revisão de temporalidade"
    * "exige avaliação humana"
    * "não executar descarte automático"
    * "validar com responsável jurídico/administrativo"

Esta sprint implementa apenas TEMP-001, TEMP-002 e TEMP-003.
TEMP-004, TEMP-005 e TEMP-008 ficam como backlog documentado.

Funções puras: recebem inventário (lista de dicts) + lista de RetentionRule e
retornam DiagnosisCandidate.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.modules.audit.diagnosis.models import DiagnosisCandidate
from app.modules.audit.findings.enums import (
    AuditCategory,
    AuditImpact,
    AuditPriority,
    AuditProbability,
    AuditSeverity,
)
from app.modules.retention import rules as retention_heuristics
from app.modules.retention.enums import RetentionPhaseKind
from app.modules.retention.models import RetentionRule

FileDict = dict[str, Any]

_MAX_PER_RULE = 30

_ADVISORY_SUFFIX = (
    "Candidato à revisão de temporalidade — exige avaliação humana. "
    "Não executar descarte automático. "
    "Validar com responsável jurídico/administrativo."
)

# Diretórios cujo nome sugere conteúdo documental (heurística inicial conservadora).
_DOCUMENT_DIR_HINTS: tuple[str, ...] = (
    "/protocolo/",
    "/registro/",
    "/registros/",
    "/escritura/",
    "/escrituras/",
    "/atas/",
    "/notas/",
    "/livros/",
    "/livro/",
    "/casamento/",
    "/casamentos/",
    "/nascimento/",
    "/obito/",
    "/óbito/",
    "/imovel/",
    "/imoveis/",
    "/protesto/",
    "/cartorio/",
    "/cartório/",
    "/serventia/",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _path_lower(f: FileDict) -> str:
    return (f.get("path_relative") or "").lower().replace("\\", "/")


def _name_lower(f: FileDict) -> str:
    return (f.get("name") or "").lower()


def _parse_dt(value: object) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    try:
        dt = datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _phase_duration(rule: RetentionRule) -> timedelta | None:
    if rule.fase_corrente_kind != RetentionPhaseKind.DURATION:
        return None
    years = rule.fase_corrente_years or 0
    months = rule.fase_corrente_months or 0
    if years == 0 and months == 0:
        return None
    return timedelta(days=years * 365 + months * 30)


def _looks_like_document_dir(path_lower: str) -> bool:
    if not path_lower:
        return False
    p = path_lower if path_lower.startswith("/") else "/" + path_lower
    return any(hint in p for hint in _DOCUMENT_DIR_HINTS)


def _match_rule_for_file(f: FileDict, rules: list[RetentionRule]) -> RetentionRule | None:
    return retention_heuristics.match_rule(
        document_name=f.get("name") or "",
        document_path=f.get("path_relative") or "",
        rules=rules,
    )


# ---------------------------------------------------------------------------
# TEMP-001 — documento sem classificação de temporalidade
# ---------------------------------------------------------------------------


def rule_temp_001_unclassified(
    files: list[FileDict],
    rules: list[RetentionRule],
    scanner_run_id: str,
) -> list[DiagnosisCandidate]:
    """TEMP-001: arquivo em diretório aparentemente documental, mas sem regra associada."""

    candidates: list[DiagnosisCandidate] = []
    for f in files:
        p = _path_lower(f)
        if not _looks_like_document_dir(p):
            continue
        matched = _match_rule_for_file(f, rules)
        if matched is not None:
            continue
        candidates.append(
            DiagnosisCandidate(
                title="Documento sem classificação de temporalidade",
                description=(
                    "Arquivo em diretório aparentemente documental, mas sem "
                    "correspondência com nenhuma regra de temporalidade conhecida. "
                    f"{_ADVISORY_SUFFIX}"
                ),
                category=AuditCategory.DOCUMENT_MANAGEMENT,
                severity=AuditSeverity.LOW,
                probability=AuditProbability.LOW,
                impact=AuditImpact.LOW,
                priority=AuditPriority.BACKLOG,
                evidence_summary=(f"Documento sem classificação: {f.get('path_relative', '?')}"),
                evidence_reference=f.get("path_relative", ""),
                scanner_run_id=scanner_run_id,
                related_file_path=f.get("path_relative", ""),
                related_parent_path=f.get("parent_path", ""),
                related_extension=f.get("extension", ""),
                related_size_bytes=f.get("size_bytes"),
                related_modified_at=str(f.get("modified_at") or ""),
                recommended_action=(
                    "Revisar manualmente. Classificar conforme tabela de "
                    "temporalidade do Provimento CNJ 50/2015 ou marcar como "
                    "fora de escopo. Não executar descarte automático."
                ),
                rule_id="TEMP-001",
                rule_name="unclassified_document",
                confidence=0.40,
                notes="Heurística por diretório documental. Sem leitura de conteúdo.",
            )
        )
        if len(candidates) >= _MAX_PER_RULE:
            break
    return candidates


# ---------------------------------------------------------------------------
# TEMP-002 — documento com prazo potencialmente vencido
# ---------------------------------------------------------------------------


def rule_temp_002_expired(
    files: list[FileDict],
    rules: list[RetentionRule],
    scanner_run_id: str,
    *,
    now: datetime | None = None,
) -> list[DiagnosisCandidate]:
    """TEMP-002: arquivo cuja regra associada tem fase corrente DURATION e prazo expirado."""

    current_time = now or datetime.now(UTC)
    candidates: list[DiagnosisCandidate] = []
    for f in files:
        matched = _match_rule_for_file(f, rules)
        if matched is None or matched.guarda_permanente:
            continue
        duration = _phase_duration(matched)
        if duration is None:
            continue
        modified_at = _parse_dt(f.get("modified_at"))
        if modified_at is None:
            continue
        expires_at = modified_at + duration
        if current_time < expires_at:
            continue
        overdue_days = (current_time - expires_at).days
        candidates.append(
            DiagnosisCandidate(
                title="Documento com prazo potencialmente vencido",
                description=(
                    f"Arquivo associado à regra {matched.codigo} "
                    f"({matched.fase_corrente_text}) com prazo aparentemente vencido "
                    f"há cerca de {overdue_days} dias. {_ADVISORY_SUFFIX}"
                ),
                category=AuditCategory.DOCUMENT_MANAGEMENT,
                severity=AuditSeverity.MEDIUM,
                probability=AuditProbability.MEDIUM,
                impact=AuditImpact.MEDIUM,
                priority=AuditPriority.NINETY_DAYS,
                evidence_summary=(
                    f"Prazo potencialmente vencido em {overdue_days} dias: "
                    f"{f.get('path_relative', '?')} "
                    f"(regra {matched.codigo})"
                ),
                evidence_reference=f.get("path_relative", ""),
                scanner_run_id=scanner_run_id,
                related_file_path=f.get("path_relative", ""),
                related_parent_path=f.get("parent_path", ""),
                related_extension=f.get("extension", ""),
                related_size_bytes=f.get("size_bytes"),
                related_modified_at=str(f.get("modified_at") or ""),
                recommended_action=(
                    "Validar com responsável jurídico/administrativo se o prazo "
                    "está realmente vencido. Confirmar requisitos de "
                    "desfiguração (art. 2º) e comunicação semestral ao juízo "
                    "competente (art. 3º) antes de qualquer ação. "
                    "Não executar descarte automático."
                ),
                rule_id="TEMP-002",
                rule_name="potentially_expired_document",
                confidence=0.55,
                notes=(
                    f"Regra associada: {matched.codigo} — {matched.documento}. "
                    f"Fase corrente: {matched.fase_corrente_text}."
                ),
            )
        )
        if len(candidates) >= _MAX_PER_RULE:
            break
    return candidates


# ---------------------------------------------------------------------------
# TEMP-003 — guarda permanente em local inadequado
# ---------------------------------------------------------------------------


def rule_temp_003_permanent_in_suspicious_location(
    files: list[FileDict],
    rules: list[RetentionRule],
    scanner_run_id: str,
) -> list[DiagnosisCandidate]:
    """TEMP-003: arquivo casado com regra de guarda permanente, mas em diretório suspeito."""

    candidates: list[DiagnosisCandidate] = []
    for f in files:
        matched = _match_rule_for_file(f, rules)
        if matched is None or not matched.guarda_permanente:
            continue
        path = f.get("path_relative") or ""
        if not retention_heuristics.is_in_suspicious_location_for_permanent(path):
            continue
        candidates.append(
            DiagnosisCandidate(
                title="Documento de guarda permanente em local inadequado",
                description=(
                    f"Arquivo associado à regra {matched.codigo} "
                    f"({matched.documento}) é de guarda permanente, mas está "
                    f"localizado em diretório que sugere temporariedade ou "
                    f"descarte. {_ADVISORY_SUFFIX}"
                ),
                category=AuditCategory.DOCUMENT_MANAGEMENT,
                severity=AuditSeverity.HIGH,
                probability=AuditProbability.MEDIUM_HIGH,
                impact=AuditImpact.HIGH,
                priority=AuditPriority.THIRTY_DAYS,
                evidence_summary=(
                    f"Guarda permanente em local suspeito: {path} (regra {matched.codigo})"
                ),
                evidence_reference=path,
                scanner_run_id=scanner_run_id,
                related_file_path=path,
                related_parent_path=f.get("parent_path", ""),
                related_extension=f.get("extension", ""),
                related_size_bytes=f.get("size_bytes"),
                related_modified_at=str(f.get("modified_at") or ""),
                recommended_action=(
                    "Mover para repositório oficial de guarda permanente após "
                    "validação humana. Não executar descarte automático. "
                    "Validar com responsável jurídico/administrativo."
                ),
                rule_id="TEMP-003",
                rule_name="permanent_in_suspicious_location",
                confidence=0.60,
                notes=(
                    f"Regra: {matched.codigo} — {matched.documento}. "
                    "Heurística por padrão de diretório."
                ),
            )
        )
        if len(candidates) >= _MAX_PER_RULE:
            break
    return candidates


# ---------------------------------------------------------------------------
# Backlog documentado — não implementadas nesta sprint
# ---------------------------------------------------------------------------

BACKLOG_TEMP_RULES: tuple[str, ...] = (
    "TEMP-004 — documento eliminável sem evidência de autorização (depende de "
    "convenção de pasta de autorização ainda não definida).",
    "TEMP-005 — documento cuja eliminação depende de microfilmagem/digitalização "
    "(requer detecção de mídia auxiliar em pasta companion).",
    "TEMP-008 — documento antigo ou sigiloso sem restrição adequada (requer "
    "modelo de classificação de sigilo ainda não disponível).",
)
