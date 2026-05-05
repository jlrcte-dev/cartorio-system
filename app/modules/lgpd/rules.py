"""Regras de domínio do módulo LGPD.

Centraliza normalização de campos vindos da plataforma INOVA (CSV) e
validações de transição de status.
"""

from __future__ import annotations

import datetime as _dt
import re
import unicodedata

from app.modules.lgpd.enums import (
    ALLOWED_STATUS_TRANSITIONS,
    LgpdActionCategory,
    LgpdActionPriority,
    LgpdActionStatus,
    LgpdActionType,
)

ACTION_CODE_PATTERN = re.compile(r"^AC-\d{2,3}$")


def _strip_accents(value: str) -> str:
    nfkd = unicodedata.normalize("NFKD", value)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_key(value: str | None) -> str:
    """Normaliza uma string para comparação: sem acento, minúsculas, sem espaços."""
    if value is None:
        return ""
    return _strip_accents(value).strip().lower()


# Alias privado mantido para compatibilidade interna.
_normalize_key = normalize_key


# --- Normalização vinda do CSV da INOVA ------------------------------------

_STATUS_MAP: dict[str, LgpdActionStatus] = {
    "finalizada": LgpdActionStatus.COMPLETED,
    "concluida": LgpdActionStatus.COMPLETED,
    "concluído": LgpdActionStatus.COMPLETED,
    "concluido": LgpdActionStatus.COMPLETED,
    "completed": LgpdActionStatus.COMPLETED,
    "pendente": LgpdActionStatus.PENDING,
    "pending": LgpdActionStatus.PENDING,
    "em andamento": LgpdActionStatus.IN_PROGRESS,
    "em progresso": LgpdActionStatus.IN_PROGRESS,
    "in progress": LgpdActionStatus.IN_PROGRESS,
}

_CATEGORY_MAP: dict[str, LgpdActionCategory] = {
    "governanca": LgpdActionCategory.GOVERNANCA,
    "governança": LgpdActionCategory.GOVERNANCA,
    "preparacao": LgpdActionCategory.PREPARACAO,
    "preparação": LgpdActionCategory.PREPARACAO,
    "implantacao": LgpdActionCategory.IMPLANTACAO,
    "implantação": LgpdActionCategory.IMPLANTACAO,
}

_TYPE_MAP: dict[str, LgpdActionType] = {
    "obrigatorio": LgpdActionType.OBRIGATORIO,
    "obrigatório": LgpdActionType.OBRIGATORIO,
    "recomendacao": LgpdActionType.RECOMENDACAO,
    "recomendação": LgpdActionType.RECOMENDACAO,
}

_PRIORITY_MAP: dict[str, LgpdActionPriority] = {
    "alta": LgpdActionPriority.ALTA,
    "media": LgpdActionPriority.MEDIA,
    "média": LgpdActionPriority.MEDIA,
    "baixa": LgpdActionPriority.BAIXA,
}


def normalize_status(raw: str | None) -> LgpdActionStatus:
    return _STATUS_MAP.get(_normalize_key(raw), LgpdActionStatus.PENDING)


def normalize_category(raw: str | None) -> LgpdActionCategory:
    return _CATEGORY_MAP.get(_normalize_key(raw), LgpdActionCategory.OTHER)


def normalize_action_type(raw: str | None) -> LgpdActionType:
    return _TYPE_MAP.get(_normalize_key(raw), LgpdActionType.OTHER)


def normalize_priority(raw: str | None) -> LgpdActionPriority:
    return _PRIORITY_MAP.get(_normalize_key(raw), LgpdActionPriority.OTHER)


# --- Datas ------------------------------------------------------------------


def parse_csv_date(raw: str | None) -> _dt.date | None:
    """Aceita ISO (yyyy-mm-dd ou yyyy-mm-ddTHH:MM:SSZ) e brasileiro (dd/mm/yyyy).

    Retorna None para valores vazios. Levanta ValueError em formato inválido.
    """
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    # ISO completo com T (ex.: 2023-03-01T08:00:00Z)
    if "T" in text:
        text = text.split("T", 1)[0]
    try:
        return _dt.date.fromisoformat(text)
    except ValueError:
        pass
    if "/" in text:
        try:
            return _dt.datetime.strptime(text, "%d/%m/%Y").date()
        except ValueError as exc:
            raise ValueError(f"Data inválida: {raw!r}") from exc
    raise ValueError(f"Data inválida: {raw!r}")


# --- Texto ------------------------------------------------------------------

_HTML_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def strip_html(raw: str | None) -> str | None:
    """Remove tags HTML simples vindas do export SharePoint da INOVA.

    Mantém o texto legível (substitui <br> por espaço antes de remover tags).
    Retorna None se entrada for None ou vazia após limpeza.
    """
    if raw is None:
        return None
    text = raw.replace("<br>", " ").replace("<br/>", " ").replace("<br />", " ")
    text = _HTML_TAG.sub("", text)
    # decodificação básica de entidades comuns vindas do CSV INOVA
    text = (
        text.replace("&quot;", '"')
        .replace("&#58;", ":")
        .replace("&#xA;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&nbsp;", " ")
    )
    text = _WS.sub(" ", text).strip()
    return text or None


# --- Status transitions -----------------------------------------------------


def validate_status_transition(current: LgpdActionStatus, new: LgpdActionStatus) -> None:
    allowed = ALLOWED_STATUS_TRANSITIONS[current]
    if new not in allowed:
        allowed_names = ", ".join(sorted(s.value for s in allowed))
        raise ValueError(
            f"Transição de status inválida: {current.value} → {new.value}. "
            f"Permitidas a partir de {current.value}: {allowed_names}"
        )


def validate_action_code(code: str) -> str:
    code = code.strip().upper()
    if not ACTION_CODE_PATTERN.match(code):
        raise ValueError(f"action_code inválido: {code!r}. Formato esperado: AC-XX (ex.: AC-01)")
    return code
