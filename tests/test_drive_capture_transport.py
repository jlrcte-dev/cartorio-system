"""Transporte somente leitura: só GET, só caminhos de leitura, erros controlados."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from app.modules.drive_capture.auth import SCOPES, build_transport
from app.modules.drive_capture.drive_client import API_BASE, RequestsTransport, check_path
from app.modules.drive_capture.errors import Code, DriveCaptureError, map_http_error
from tests.drive_capture_support import make_config

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "app" / "modules" / "drive_capture"
SECRET_ID = "SHEETsegredo0000000001"


class _Response:
    def __init__(self, status: int, body: bytes) -> None:
        self.status_code = status
        self._body = body
        self.closed = False

    def iter_content(self, chunk: int):  # noqa: ANN201
        for i in range(0, len(self._body), 4):
            yield self._body[i : i + 4]

    def close(self) -> None:
        self.closed = True


class _GetOnlySession:
    """Sessão que só sabe GET; qualquer outro método reprova o teste."""

    def __init__(self, response: _Response | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.requests: list[tuple[str, dict]] = []

    def get(self, url: str, **kwargs: object) -> _Response:
        self.requests.append((url, kwargs))
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response

    def __getattr__(self, name: str) -> object:
        raise AssertionError(f"transporte tentou usar session.{name}")


def test_transport_uses_only_get_on_the_drive_api() -> None:
    session = _GetOnlySession(_Response(200, b'{"id": "x"}'))
    transport = RequestsTransport(session, timeout_seconds=5)

    assert transport.get_json(f"files/{SECRET_ID}", {"fields": "id"}) == {"id": "x"}

    url, kwargs = session.requests[0]
    assert url == f"{API_BASE}files/{SECRET_ID}"
    assert kwargs["timeout"] == 5 and kwargs["stream"] is True
    assert session.response.closed


@pytest.mark.parametrize(
    "path",
    [
        f"files/{SECRET_ID}/permissions",
        f"files/{SECRET_ID}/copy",
        f"files/{SECRET_ID}/comments",
        f"files/{SECRET_ID}/revisions",
        "changes",
        "drives",
        "permissions",
        "../files",
    ],
)
def test_paths_outside_read_allowlist_are_refused(path: str) -> None:
    session = _GetOnlySession(_Response(200, b"{}"))
    with pytest.raises(DriveCaptureError):
        RequestsTransport(session, 5).get_json(path, {})
    assert session.requests == []
    with pytest.raises(DriveCaptureError):
        check_path(path)


def test_body_over_cap_is_refused_not_truncated() -> None:
    transport = RequestsTransport(_GetOnlySession(_Response(200, b"PK\x03\x04" + b"x" * 40)), 5)

    with pytest.raises(DriveCaptureError) as excinfo:
        transport.get_bytes(f"files/{SECRET_ID}/export", {"mimeType": "x"}, max_bytes=20)

    assert excinfo.value.code == Code.SIZE_LIMIT


def _error_body(reason: str) -> bytes:
    return json.dumps(
        {
            "error": {
                "code": 403,
                "message": f"Arquivo {SECRET_ID} de Cliente Fulano não pode ser lido",
                "errors": [{"reason": reason, "message": f"detalhe {SECRET_ID}"}],
            }
        }
    ).encode()


@pytest.mark.parametrize(
    ("status", "reason", "code"),
    [
        (401, "authError", Code.AUTH_FAILED),
        (404, "notFound", Code.NOT_FOUND),
        (403, "insufficientFilePermissions", Code.PERMISSION_DENIED),
        (403, "exportSizeLimitExceeded", Code.EXPORT_SIZE_LIMIT),
        (403, "cannotDownloadFile", Code.DOWNLOAD_RESTRICTED),
        (403, "userRateLimitExceeded", Code.RATE_LIMITED),
        (429, "rateLimitExceeded", Code.RATE_LIMITED),
        (403, "dailyLimitExceeded", Code.QUOTA_EXCEEDED),
        (503, "backendError", Code.SERVER_ERROR),
        (400, "badRequest", Code.UNEXPECTED_RESPONSE),
    ],
)
def test_http_errors_map_to_controlled_codes_without_remote_text(
    status: int, reason: str, code: Code
) -> None:
    assert map_http_error(status, _error_body(reason)) == code
    transport = RequestsTransport(_GetOnlySession(_Response(status, _error_body(reason))), 5)

    with pytest.raises(DriveCaptureError) as excinfo:
        transport.get_json(f"files/{SECRET_ID}", {})

    assert excinfo.value.code == code
    assert SECRET_ID not in str(excinfo.value)
    assert "Fulano" not in str(excinfo.value)


def test_map_http_error_survives_non_json_body() -> None:
    assert map_http_error(403, b"<html>Forbidden</html>") == Code.PERMISSION_DENIED


class RefreshError(Exception):
    """Mesmo nome da exceção do google-auth para credencial revogada."""


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (TimeoutError(f"timeout em {SECRET_ID}"), Code.TIMEOUT),
        (ConnectionError(f"falha em {API_BASE}files/{SECRET_ID}"), Code.NETWORK_ERROR),
        (RefreshError("invalid_grant"), Code.AUTH_FAILED),
        (ValueError("x"), Code.UNEXPECTED_ERROR),
    ],
)
def test_transport_exceptions_are_classified_and_not_chained(error: Exception, code: Code) -> None:
    transport = RequestsTransport(_GetOnlySession(error=error), 5)

    with pytest.raises(DriveCaptureError) as excinfo:
        transport.get_json(f"files/{SECRET_ID}", {})

    assert excinfo.value.code == code
    assert excinfo.value.__suppress_context__ is True
    assert SECRET_ID not in str(excinfo.value)


def test_package_source_has_no_write_calls_or_delegation() -> None:
    source = "\n".join(p.read_text(encoding="utf-8") for p in PACKAGE_DIR.glob("*.py"))

    assert not re.search(r"\.(post|put|patch|delete|request)\(", source)
    assert not re.search(r"\b(POST|PUT|PATCH|DELETE)\b", source)
    assert "with_subject" not in source and "subject=" not in source


def test_only_the_readonly_scope_is_requested() -> None:
    assert SCOPES == ("https://www.googleapis.com/auth/drive.readonly",)


def test_importing_the_package_starts_no_auth_network_or_google_import() -> None:
    code = (
        "import sys\n"
        "import app.modules.drive_capture.cli, app.modules.drive_capture.collector\n"
        "import app.modules.drive_capture.report, app.modules.drive_capture.auth\n"
        "bad = [m for m in sys.modules if m.startswith(('google', 'requests', 'urllib3'))]\n"
        "print(','.join(bad))\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        cwd=PACKAGE_DIR.parents[2],
    )
    assert out.stdout.strip() == ""


# -- credencial ------------------------------------------------------------------------


def _config(tmp_path: Path):  # noqa: ANN202
    return make_config(
        tmp_path, files=[{"alias": "fonte_piloto", "family": "protestos", "file_id": SECRET_ID}]
    )


def test_missing_credential_file_is_explicit(tmp_path: Path) -> None:
    with pytest.raises(DriveCaptureError) as excinfo:
        build_transport(_config(tmp_path))
    assert excinfo.value.code == Code.CREDENTIALS_MISSING


@pytest.mark.parametrize(
    "payload",
    [
        '{"installed": {"client_id": "x", "client_secret": "segredo"}}',
        '{"type": "authorized_user", "refresh_token": "segredo"}',
        "não é json",
    ],
)
def test_non_service_account_credentials_are_refused(tmp_path: Path, payload: str) -> None:
    config = _config(tmp_path)
    config.credentials_file.write_text(payload, encoding="utf-8")

    with pytest.raises(DriveCaptureError) as excinfo:
        build_transport(config)

    assert excinfo.value.code == Code.CREDENTIALS_INVALID
    assert "segredo" not in str(excinfo.value)


def test_missing_drive_extra_is_explicit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config(tmp_path)
    config.credentials_file.write_text(
        json.dumps({"type": "service_account", "client_email": "x@y.iam.gserviceaccount.com"}),
        encoding="utf-8",
    )
    monkeypatch.setitem(sys.modules, "google.oauth2", None)

    with pytest.raises(DriveCaptureError) as excinfo:
        build_transport(config)

    assert excinfo.value.code == Code.DEPENDENCY_MISSING


def test_real_transport_builds_offline_with_readonly_scope(tmp_path: Path) -> None:
    pytest.importorskip("google.oauth2.service_account")
    pytest.importorskip("requests")
    rsa = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.rsa")
    from cryptography.hazmat.primitives import serialization

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    config = _config(tmp_path)
    config.credentials_file.write_text(
        json.dumps(
            {
                "type": "service_account",
                "project_id": "projeto-ficticio",
                "private_key_id": "0" * 40,
                "private_key": pem,
                "client_email": "leitor-cartorio@projeto-ficticio.iam.gserviceaccount.com",
                "client_id": "1",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        ),
        encoding="utf-8",
    )

    transport, identity = build_transport(config)

    assert isinstance(transport, RequestsTransport)
    assert identity == "leitor-cartorio@projeto-ficticio.iam.gserviceaccount.com"
    credentials = transport._session.credentials  # type: ignore[attr-defined]
    assert tuple(credentials.scopes) == SCOPES
    assert not credentials.valid  # nenhum token foi buscado: construir não abre rede
