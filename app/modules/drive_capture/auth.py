"""Monta o transporte real: service account própria do cartório, escopo único de leitura.

Método único nesta etapa (ADR-011): chave JSON de service account compartilhada como
Leitor nas fontes. Sem delegação de domínio (nenhum ``subject``), sem OAuth de usuário,
sem reaproveitar token de outro sistema. O conteúdo do arquivo de credencial nunca é
impresso nem registrado.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.modules.drive_capture.config import CaptureConfig
from app.modules.drive_capture.drive_client import RequestsTransport
from app.modules.drive_capture.errors import Code, DriveCaptureError

# drive.readonly é o menor escopo que permite exportar/baixar conteúdo. drive.file NÃO é
# somente leitura e drive.metadata.readonly não entrega conteúdo.
DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
SCOPES: tuple[str, ...] = (DRIVE_READONLY_SCOPE,)


def _read_service_account_info(path: Path) -> dict:
    if not path.is_file():
        raise DriveCaptureError(Code.CREDENTIALS_MISSING)
    try:
        info = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise DriveCaptureError(Code.CREDENTIALS_INVALID) from None
    if (
        not isinstance(info, dict)
        or info.get("type") != "service_account"
        or not isinstance(info.get("client_email"), str)
    ):
        raise DriveCaptureError(Code.CREDENTIALS_INVALID)
    return info


def build_transport(config: CaptureConfig) -> tuple[RequestsTransport, str]:
    """Devolve o transporte autenticado e o e-mail da identidade da credencial local."""
    info = _read_service_account_info(config.credentials_file)
    try:
        from google.auth.transport.requests import AuthorizedSession
        from google.oauth2 import service_account
    except ImportError:
        raise DriveCaptureError(Code.DEPENDENCY_MISSING) from None
    try:
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=list(SCOPES)
        )
    except (ValueError, KeyError, TypeError):
        raise DriveCaptureError(Code.CREDENTIALS_INVALID) from None
    if tuple(credentials.scopes or ()) != SCOPES:
        raise DriveCaptureError(Code.CREDENTIALS_INVALID, "escopo diferente de drive.readonly")
    session = AuthorizedSession(credentials)
    return (
        RequestsTransport(session, config.limits.request_timeout_seconds),
        credentials.service_account_email,
    )
