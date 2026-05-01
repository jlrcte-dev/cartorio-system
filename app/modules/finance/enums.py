from __future__ import annotations

from enum import StrEnum


class EntryType(StrEnum):
    RECEITA = "RECEITA"
    DESPESA = "DESPESA"
    REPASSE = "REPASSE"
    AJUSTE = "AJUSTE"


class EntryStatus(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"
    TO_REVIEW = "TO_REVIEW"


class ServiceArea(StrEnum):
    RI = "RI"
    RC = "RC"
    NOTAS = "NOTAS"
    PROTESTO = "PROTESTO"
    RTD = "RTD"
    GERAL = "GERAL"


class EntrySource(StrEnum):
    MANUAL = "MANUAL"
    IMPORT_XLSX = "IMPORT_XLSX"
    ENGEGRAPH_EXPORT = "ENGEGRAPH_EXPORT"
    BANK_STATEMENT = "BANK_STATEMENT"
    ACCOUNTING = "ACCOUNTING"
    OTHER = "OTHER"


class EntryDirection(StrEnum):
    INFLOW = "INFLOW"
    OUTFLOW = "OUTFLOW"


# Status permitidos por tipo
ALLOWED_STATUS_BY_TYPE: dict[EntryType, frozenset[EntryStatus]] = {
    EntryType.RECEITA: frozenset(
        {EntryStatus.PENDING, EntryStatus.RECEIVED, EntryStatus.CANCELLED, EntryStatus.TO_REVIEW}
    ),
    EntryType.DESPESA: frozenset(
        {EntryStatus.PENDING, EntryStatus.PAID, EntryStatus.CANCELLED, EntryStatus.TO_REVIEW}
    ),
    EntryType.REPASSE: frozenset(
        {EntryStatus.PENDING, EntryStatus.PAID, EntryStatus.CANCELLED, EntryStatus.TO_REVIEW}
    ),
    EntryType.AJUSTE: frozenset(
        {
            EntryStatus.PENDING,
            EntryStatus.PAID,
            EntryStatus.RECEIVED,
            EntryStatus.CANCELLED,
            EntryStatus.TO_REVIEW,
        }
    ),
}


# Direction obrigatório por tipo (None = livre, válido apenas para AJUSTE)
REQUIRED_DIRECTION_BY_TYPE: dict[EntryType, EntryDirection | None] = {
    EntryType.RECEITA: EntryDirection.INFLOW,
    EntryType.DESPESA: EntryDirection.OUTFLOW,
    EntryType.REPASSE: EntryDirection.OUTFLOW,
    EntryType.AJUSTE: None,
}


# Status considerados "liquidados" (efetivamente pagos/recebidos) por tipo
SETTLED_STATUS_BY_TYPE: dict[EntryType, frozenset[EntryStatus]] = {
    EntryType.RECEITA: frozenset({EntryStatus.RECEIVED}),
    EntryType.DESPESA: frozenset({EntryStatus.PAID}),
    EntryType.REPASSE: frozenset({EntryStatus.PAID}),
    EntryType.AJUSTE: frozenset({EntryStatus.PAID, EntryStatus.RECEIVED}),
}
