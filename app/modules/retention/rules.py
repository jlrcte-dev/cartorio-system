"""Heurísticas puras de classificação documento → regra normativa.

SAFETY CONTRACT
---------------
- Nenhuma função aqui lê conteúdo de arquivo.
- Nenhuma função executa, autoriza ou recomenda descarte.
- Apenas casa metadados (nome, caminho) com termos previstos nas regras.
"""

from __future__ import annotations

import re
import unicodedata

from app.modules.retention.models import RetentionRule

_NON_WORD = re.compile(r"[^a-z0-9]+")


def _normalize(text: str) -> str:
    """Lowercase, remove acentos, normaliza separadores em espaços."""

    if not text:
        return ""
    nfd = unicodedata.normalize("NFD", text)
    no_accents = "".join(ch for ch in nfd if not unicodedata.combining(ch))
    return _NON_WORD.sub(" ", no_accents.lower()).strip()


# Palavras muito curtas ou genéricas que sozinhas não devem disparar match.
_STOPWORDS: frozenset[str] = frozenset(
    {
        "de",
        "da",
        "do",
        "das",
        "dos",
        "e",
        "em",
        "para",
        "no",
        "na",
        "ao",
        "a",
        "o",
        "os",
        "as",
        "por",
        "que",
        "ou",
        "registro",
        "livro",
        "documento",
        "documentos",
    }
)


def _significant_terms(text: str) -> list[str]:
    return [w for w in _normalize(text).split() if len(w) >= 4 and w not in _STOPWORDS]


def _stem(word: str) -> str:
    """Remoção ingênua de plural português ('s' final em palavras longas)."""

    if len(word) > 4 and word.endswith("s"):
        return word[:-1]
    return word


def match_rule(
    document_name: str,
    document_path: str,
    rules: list[RetentionRule],
) -> RetentionRule | None:
    """Retorna a regra mais provável para o documento, ou None.

    Estratégia conservadora: requer pelo menos 2 termos significativos do
    `documento` da regra batendo (por raiz, ignorando plural simples)
    no nome+caminho. Empate → primeira ordem por código.
    """

    haystack = _normalize(f"{document_name} {document_path}")
    if not haystack:
        return None

    best: RetentionRule | None = None
    best_score = 0
    for rule in rules:
        terms = _significant_terms(rule.documento)
        if not terms:
            continue
        score = sum(1 for t in terms if _stem(t) in haystack)
        if score >= 2 and score > best_score:
            best = rule
            best_score = score
    return best


# Diretórios suspeitos para guarda permanente (TEMP-003).
_SUSPICIOUS_DIRS_FOR_PERMANENT: tuple[str, ...] = (
    "/temp/",
    "/tmp/",
    "/_tmp/",
    "/lixo/",
    "/descarte/",
    "/_old/",
    "/old/",
    "/backup_temp/",
    "/rascunho/",
    "/scratch/",
)


def is_in_suspicious_location_for_permanent(document_path: str) -> bool:
    """Indica se o caminho do documento está em local impróprio para guarda permanente."""

    if not document_path:
        return False
    p = document_path.replace("\\", "/").lower()
    if not p.startswith("/"):
        p = "/" + p
    return any(needle in p for needle in _SUSPICIOUS_DIRS_FOR_PERMANENT)
