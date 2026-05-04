from __future__ import annotations

from enum import StrEnum


class AuditCategory(StrEnum):
    INFRASTRUCTURE = "INFRASTRUCTURE"
    BACKUP = "BACKUP"
    ACCESS_CONTROL = "ACCESS_CONTROL"
    NETWORK = "NETWORK"
    ENDPOINT_SECURITY = "ENDPOINT_SECURITY"
    DOCUMENT_MANAGEMENT = "DOCUMENT_MANAGEMENT"
    OPERATIONAL_FLOW = "OPERATIONAL_FLOW"
    POLICY_DOCUMENT = "POLICY_DOCUMENT"
    COMPLIANCE = "COMPLIANCE"
    VENDOR = "VENDOR"
    FINANCE = "FINANCE"
    SYSTEM = "SYSTEM"
    OTHER = "OTHER"


class AuditOrigin(StrEnum):
    MANUAL = "MANUAL"
    SCANNER = "SCANNER"
    TECHNICAL_REPORT = "TECHNICAL_REPORT"
    CHECKLIST = "CHECKLIST"
    INTERVIEW = "INTERVIEW"
    CNJ_MAPPING = "CNJ_MAPPING"
    BACKUP_LOG = "BACKUP_LOG"
    DISK_SCAN = "DISK_SCAN"
    NETWORK_REVIEW = "NETWORK_REVIEW"
    POLICY_REVIEW = "POLICY_REVIEW"
    OTHER = "OTHER"


class AuditSeverity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class AuditProbability(StrEnum):
    HIGH = "HIGH"
    MEDIUM_HIGH = "MEDIUM_HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class AuditImpact(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class AuditPriority(StrEnum):
    IMMEDIATE = "IMMEDIATE"
    SEVEN_DAYS = "SEVEN_DAYS"
    THIRTY_DAYS = "THIRTY_DAYS"
    NINETY_DAYS = "NINETY_DAYS"
    BACKLOG = "BACKLOG"


class AuditStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_VALIDATION = "WAITING_VALIDATION"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"
    ARCHIVED = "ARCHIVED"


# Prioridades obrigatórias para severidade CRITICAL (salvo justificativa em notes)
CRITICAL_REQUIRED_PRIORITIES: frozenset[AuditPriority] = frozenset(
    {AuditPriority.IMMEDIATE, AuditPriority.SEVEN_DAYS}
)

# Status que exigem campos de resolução
STATUS_REQUIRES_RESOLUTION: frozenset[AuditStatus] = frozenset({AuditStatus.RESOLVED})
STATUS_REQUIRES_DISMISSAL: frozenset[AuditStatus] = frozenset({AuditStatus.DISMISSED})
STATUS_REQUIRES_NOTES: frozenset[AuditStatus] = frozenset({AuditStatus.ARCHIVED})
