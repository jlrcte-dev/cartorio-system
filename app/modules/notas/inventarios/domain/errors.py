"""Hierarquia de erros do módulo de inventários."""

from __future__ import annotations


class InventarioError(Exception):
    """Erro genérico do módulo de inventários."""


class InventarioInputError(InventarioError):
    """Falha ao carregar/desserializar a entrada (YAML/JSON malformado, tipo errado)."""


class InventarioValidationError(InventarioError):
    """Inconsistência semântica no inventário (percentuais, valores, referências).

    Carrega uma lista de mensagens para que o chamador possa reportar todos os
    problemas encontrados de uma só vez.
    """

    def __init__(self, errors: list[str]) -> None:
        self.errors = list(errors)
        super().__init__("; ".join(self.errors) if self.errors else "inventário inválido")
