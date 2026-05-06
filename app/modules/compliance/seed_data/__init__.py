"""Pacote com datasets de seed da Matriz INOVA V1.

Os datasets são constantes Python tipadas, armazenadas separadamente do
runtime de seed (`app.modules.compliance.seed`), para permitir versionamento
limpo e cálculo de checksum determinístico.
"""

from app.modules.compliance.seed_data.matriz_v1 import (
    SEED_DEADLINES,
    SEED_EVIDENCE_TEMPLATES,
    SEED_META,
    SEED_POLICIES,
    SEED_REQUIREMENT_POLICIES,
    SEED_REQUIREMENTS,
)

__all__ = [
    "SEED_DEADLINES",
    "SEED_EVIDENCE_TEMPLATES",
    "SEED_META",
    "SEED_POLICIES",
    "SEED_REQUIREMENT_POLICIES",
    "SEED_REQUIREMENTS",
]
