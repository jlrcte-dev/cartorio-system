"""Códigos de falha controlados do coletor.

Respostas HTTP e mensagens remotas podem conter IDs, títulos ou e-mails. Nada vindo do
servidor é propagado: o erro carrega só um código desta lista e um texto fixo.
"""

from __future__ import annotations

import json
from enum import StrEnum


class Code(StrEnum):
    CONFIG_INVALID = "config_invalid"
    CREDENTIALS_MISSING = "credentials_missing"
    CREDENTIALS_INVALID = "credentials_invalid"
    DEPENDENCY_MISSING = "dependency_missing"
    IDENTITY_MISMATCH = "identity_mismatch"
    RUN_LOCKED = "run_locked"
    AUTH_FAILED = "auth_failed"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    DOWNLOAD_RESTRICTED = "download_restricted"
    EXPORT_SIZE_LIMIT = "export_size_limit"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXCEEDED = "quota_exceeded"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    UNEXPECTED_RESPONSE = "unexpected_response"
    UNSUPPORTED_MIME = "unsupported_mime"
    SHORTCUT_NOT_FOLLOWED = "shortcut_not_followed"
    IS_FOLDER = "is_folder"
    NOT_A_FOLDER = "not_a_folder"
    TRASHED = "trashed"
    OUT_OF_BOUNDARY = "out_of_boundary"
    SIZE_LIMIT = "size_limit_exceeded"
    SOURCE_CHANGED = "source_changed_during_capture"
    INTEGRITY_MISMATCH = "integrity_mismatch"
    RUN_BUDGET_EXHAUSTED = "run_budget_exhausted"
    SOURCE_CAP = "source_cap_reached"
    STORE_ERROR = "store_error"
    UNEXPECTED_ERROR = "unexpected_error"


RETRYABLE: frozenset[Code] = frozenset(
    {Code.RATE_LIMITED, Code.SERVER_ERROR, Code.NETWORK_ERROR, Code.TIMEOUT}
)

MESSAGES: dict[Code, str] = {
    Code.CONFIG_INVALID: "configuração inválida",
    Code.CREDENTIALS_MISSING: "arquivo de credencial não encontrado no caminho configurado",
    Code.CREDENTIALS_INVALID: "arquivo de credencial ilegível ou não é de service account",
    Code.DEPENDENCY_MISSING: "dependência ausente: instale o extra com pip install -e .[drive]",
    Code.IDENTITY_MISMATCH: "identidade autenticada difere de expected_identity",
    Code.RUN_LOCKED: "outra coleta em andamento (run.lock presente no diretório de dados)",
    Code.AUTH_FAILED: "autenticação recusada ou credencial revogada",
    Code.NOT_FOUND: "fonte indisponível para esta identidade (404) — não implica exclusão",
    Code.PERMISSION_DENIED: "acesso negado à fonte (403)",
    Code.DOWNLOAD_RESTRICTED: "download/exportação bloqueado para leitores nesta fonte",
    Code.EXPORT_SIZE_LIMIT: "exportação acima do limite do Drive (10 MB)",
    Code.RATE_LIMITED: "limite de taxa da API atingido",
    Code.QUOTA_EXCEEDED: "quota da API esgotada",
    Code.SERVER_ERROR: "erro do servidor do Drive (5xx)",
    Code.NETWORK_ERROR: "falha de rede",
    Code.TIMEOUT: "tempo de resposta esgotado",
    Code.UNEXPECTED_RESPONSE: "resposta inesperada da API",
    Code.UNSUPPORTED_MIME: "tipo de arquivo não aceito no piloto",
    Code.SHORTCUT_NOT_FOLLOWED: "atalho não é seguido — atalhos não ampliam a fronteira",
    Code.IS_FOLDER: "ID configurado como arquivo é uma pasta",
    Code.NOT_A_FOLDER: "ID configurado como pasta não é uma pasta",
    Code.TRASHED: "fonte está na lixeira",
    Code.OUT_OF_BOUNDARY: (
        "fonte ausente da pasta autorizada (movida, removida ou sem acesso — não distinguido);"
        " leituras suspensas"
    ),
    Code.SIZE_LIMIT: "fonte acima do teto de bytes por arquivo",
    Code.SOURCE_CHANGED: "origem mudou durante a captura — geração não promovida",
    Code.INTEGRITY_MISMATCH: "bytes recebidos não conferem com o checksum do Drive",
    Code.RUN_BUDGET_EXHAUSTED: "teto de bytes ou de tempo da execução atingido",
    Code.SOURCE_CAP: "teto de fontes por execução atingido",
    Code.STORE_ERROR: "falha ao gravar a captura localmente",
    Code.UNEXPECTED_ERROR: "erro inesperado no coletor",
}


class DriveCaptureError(Exception):
    def __init__(self, code: Code, detail: str = "") -> None:
        self.code = code
        # detail é sempre texto do próprio coletor (ex.: nome de campo da config), nunca remoto.
        self.detail = detail
        super().__init__(f"{code}: {MESSAGES[code]}" + (f" ({detail})" if detail else ""))


_RATE_REASONS = {"userRateLimitExceeded", "rateLimitExceeded"}
_QUOTA_REASONS = {"dailyLimitExceeded", "quotaExceeded", "dailyLimitExceededUnreg"}
_DOWNLOAD_REASONS = {"cannotDownloadFile", "cannotDownloadAbusiveFile", "fileNotDownloadable"}


def _error_reason(body: bytes) -> str | None:
    try:
        payload = json.loads(body.decode("utf-8", errors="replace"))
        errors = payload["error"]["errors"]
        reason = errors[0]["reason"]
    except (ValueError, KeyError, IndexError, TypeError):
        return None
    return reason if isinstance(reason, str) else None


def map_http_error(status: int, body: bytes) -> Code:
    """Traduz status + ``reason`` do corpo de erro do Drive em código controlado."""
    reason = _error_reason(body)
    if status == 401:
        return Code.AUTH_FAILED
    if status == 404:
        return Code.NOT_FOUND
    if status == 429 or reason in _RATE_REASONS:
        return Code.RATE_LIMITED
    if reason in _QUOTA_REASONS:
        return Code.QUOTA_EXCEEDED
    if reason == "exportSizeLimitExceeded":
        return Code.EXPORT_SIZE_LIMIT
    if reason in _DOWNLOAD_REASONS:
        return Code.DOWNLOAD_RESTRICTED
    if status == 403:
        return Code.PERMISSION_DENIED
    if 500 <= status < 600:
        return Code.SERVER_ERROR
    return Code.UNEXPECTED_RESPONSE


def classify_exception(exc: BaseException) -> Code:
    """Classifica exceções do transporte sem importar ``requests``/``google-auth``.

    ``requests.Timeout`` e ``requests.ConnectionError`` herdam de ``OSError``; o
    ``RefreshError`` do google-auth indica credencial revogada ou chave inválida.
    """
    names = {cls.__name__ for cls in type(exc).__mro__}
    if names & {"RefreshError", "DefaultCredentialsError"}:
        return Code.AUTH_FAILED
    if names & {"Timeout", "TimeoutError", "ReadTimeout", "ConnectTimeout"}:
        return Code.TIMEOUT
    if isinstance(exc, OSError):
        return Code.NETWORK_ERROR
    return Code.UNEXPECTED_ERROR
