from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.retention.enums import (
    RetentionDestination,
    RetentionPhaseKind,
    RetentionStatus,
)


class RetentionRuleIn(BaseModel):
    """Entrada para criar/atualizar uma regra de temporalidade (uso interno: seed)."""

    codigo: str = Field(min_length=1, max_length=32)
    assunto: str = Field(min_length=1, max_length=200)
    documento: str = Field(min_length=1, max_length=300)
    fase_corrente_text: str = Field(min_length=1, max_length=64)
    fase_corrente_kind: RetentionPhaseKind
    fase_corrente_years: int | None = None
    fase_corrente_months: int | None = None
    fase_intermediaria_text: str | None = None
    eliminacao: bool = False
    guarda_permanente: bool = False
    requer_microfilmagem: bool = False
    requer_digitalizacao: bool = False
    observacao: str | None = None
    base_legal: str | None = None
    alteracoes: str | None = None
    source_norm: str
    source_version: str
    source_file: str
    source_code: str
    source_notes: str | None = None


class RetentionRuleOut(BaseModel):
    """Representação de leitura de uma regra de temporalidade."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    assunto: str
    documento: str
    fase_corrente_text: str
    fase_corrente_kind: RetentionPhaseKind
    fase_corrente_years: int | None
    fase_corrente_months: int | None
    fase_intermediaria_text: str | None
    eliminacao: bool
    guarda_permanente: bool
    requer_microfilmagem: bool
    requer_digitalizacao: bool
    observacao: str | None
    base_legal: str | None
    alteracoes: str | None
    source_norm: str
    source_version: str
    source_file: str
    source_code: str
    source_notes: str | None
    created_at: datetime
    updated_at: datetime


class DocumentMetadata(BaseModel):
    """Metadados mínimos de um documento para avaliação read-only.

    Nunca contém conteúdo do arquivo. Apenas nome, caminho e timestamps.
    """

    name: str
    path_relative: str = ""
    parent_path: str = ""
    extension: str = ""
    modified_at: datetime | None = None
    legal_hold: bool = False


class RetentionEvaluation(BaseModel):
    """Resultado em memória da avaliação de um documento contra as regras.

    Não é persistido nesta sprint (retention-1A). Apenas estrutura de saída.
    """

    document_name: str
    document_path: str
    matched_rule_codigo: str | None = None
    matched_rule_documento: str | None = None
    status: RetentionStatus
    destination: RetentionDestination
    is_overdue: bool = False
    overdue_by_days: int | None = None
    requires_media_before_disposal: bool = False
    message: str
    advisory: str = (
        "candidato à revisão de temporalidade — exige avaliação humana. "
        "Não executar descarte automático. "
        "Validar com responsável jurídico/administrativo."
    )
