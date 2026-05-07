from __future__ import annotations

from enum import StrEnum


class RequirementSource(StrEnum):
    """Origem normativa do requisito mapeado.

    Usar `PROV_213` para artigos do Provimento CNJ 213/2026, mesmo quando a
    obrigação seja de natureza LGPD. A natureza da obrigação fica em
    `RequirementClassification`.
    """

    PROV_213 = "PROV_213"
    LGPD = "LGPD"
    ANEXO_III = "ANEXO_III"
    ANEXO_IV = "ANEXO_IV"
    MATRIZ_INOVA = "MATRIZ_INOVA"


class RequirementClassification(StrEnum):
    OBRIGATORIO_LGPD = "OBRIGATORIO_LGPD"
    OBRIGATORIO_PROVIMENTO = "OBRIGATORIO_PROVIMENTO"
    COMPLEMENTAR_BOA_PRATICA = "COMPLEMENTAR_BOA_PRATICA"
    COMPLEMENTAR_GOVERNANCA = "COMPLEMENTAR_GOVERNANCA"


class RequirementStage(StrEnum):
    ETAPA_1 = "ETAPA_1"
    ETAPA_2 = "ETAPA_2"
    ETAPA_3 = "ETAPA_3"
    ETAPA_3_4 = "ETAPA_3_4"
    ETAPA_4 = "ETAPA_4"
    ETAPA_5 = "ETAPA_5"
    ETAPAS_1_2 = "ETAPAS_1_2"
    ETAPAS_1_5 = "ETAPAS_1_5"
    TODAS = "TODAS"
    NAO_APLICAVEL = "NAO_APLICAVEL"


class PolicyDocumentKind(StrEnum):
    POLITICA = "POLITICA"
    PROCEDIMENTO = "PROCEDIMENTO"
    PLANO = "PLANO"
    INVENTARIO = "INVENTARIO"
    DOCUMENTO = "DOCUMENTO"
    DOCUMENTO_TECNICO = "DOCUMENTO_TECNICO"
    MODELO_ATA = "MODELO_ATA"
    CARTAZ = "CARTAZ"
    FAQ = "FAQ"
    GUIA = "GUIA"
    OUTRO = "OUTRO"


class ServentiaClass(StrEnum):
    C1 = "C1"
    C2 = "C2"
    C3 = "C3"


class DeadlineUnit(StrEnum):
    DIAS = "DIAS"
    MESES = "MESES"
    AO_FINAL_ETAPA = "AO_FINAL_ETAPA"


class ComplianceEvidenceType(StrEnum):
    DOCUMENT = "DOCUMENT"
    POLICY = "POLICY"
    REPORT = "REPORT"
    SCREENSHOT = "SCREENSHOT"
    LOG = "LOG"
    DECLARATION = "DECLARATION"
    CONTRACT = "CONTRACT"
    CERTIFICATE = "CERTIFICATE"
    MEETING_MINUTES = "MEETING_MINUTES"
    CONFIGURATION = "CONFIGURATION"
    EXTERNAL_REFERENCE = "EXTERNAL_REFERENCE"
    OTHER = "OTHER"


class ComplianceEvidenceStatus(StrEnum):
    COLLECTED = "COLLECTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    NEEDS_UPDATE = "NEEDS_UPDATE"


class ComplianceEvidenceSourceModule(StrEnum):
    MANUAL = "MANUAL"
    EXTERNAL = "EXTERNAL"
    AUDIT = "AUDIT"
    RETENTION = "RETENTION"
    LGPD = "LGPD"
    SYSTEM = "SYSTEM"


class ComplianceLinkSourceModule(StrEnum):
    AUDIT = "AUDIT"
    RETENTION = "RETENTION"
    LGPD = "LGPD"
    MANUAL = "MANUAL"
    EXTERNAL = "EXTERNAL"


class ComplianceLinkSourceType(StrEnum):
    FINDING = "FINDING"
    DIAGNOSIS = "DIAGNOSIS"
    SIGNAL = "SIGNAL"
    ACTION = "ACTION"
    POLICY = "POLICY"
    DOCUMENT = "DOCUMENT"
    MANUAL_NOTE = "MANUAL_NOTE"


class ComplianceLinkRiskLevel(StrEnum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ComplianceRequirementStatusValue(StrEnum):
    """Status indicativo interno de acompanhamento por requisito.

    Não representa declaração automática de conformidade. A conclusão sempre
    depende de revisão humana e validação documental — nenhum dos valores
    abaixo afirma cumprimento ou aprovação.

    UNDER_REVIEW está reservado para futura sprint de revisão humana; o
    recompute desta sprint não emite UNDER_REVIEW.
    """

    EVIDENCE_PENDING = "EVIDENCE_PENDING"
    EVIDENCE_AVAILABLE = "EVIDENCE_AVAILABLE"
    HAS_OPEN_FINDINGS = "HAS_OPEN_FINDINGS"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"
    UNDER_REVIEW = "UNDER_REVIEW"
