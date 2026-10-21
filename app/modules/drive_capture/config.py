"""Configuração local (não versionada) do coletor: identidade, fronteira e tetos.

A fronteira é só o que está aqui: IDs explícitos de arquivo e pastas autorizadas cujos
filhos DIRETOS entram por regra de tipo e, opcionalmente, padrão de nome. Nada é
descoberto por busca global.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.modules.drive_capture.errors import Code, DriveCaptureError

CONFIG_VERSION = 1

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = REPO_ROOT / "_local_data" / "drive_capture" / "config.yaml"
DEFAULT_REPORT_JSON = REPO_ROOT / "exports" / "atlas" / "cartorio_drive_capture_report.json"

FAMILIES: tuple[str, ...] = (
    "gerenciamento_financeiro",
    "protestos",
    "documentos_em_andamento",
    "relatorios_colaboradores",
)

GOOGLE_SHEET = "application/vnd.google-apps.spreadsheet"
GOOGLE_DOC = "application/vnd.google-apps.document"
GOOGLE_FOLDER = "application/vnd.google-apps.folder"
GOOGLE_SHORTCUT = "application/vnd.google-apps.shortcut"

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
ODS = "application/vnd.oasis.opendocument.spreadsheet"
CSV = "text/csv"
PDF = "application/pdf"

# Tipo nativo → (MIME de exportação, extensão, método). CSV de uma aba não representa a
# planilha inteira, por isso Sheets sai sempre como XLSX.
GOOGLE_EXPORTS: dict[str, tuple[str, str, str]] = {
    GOOGLE_SHEET: (XLSX, "xlsx", "export_xlsx"),
    GOOGLE_DOC: (DOCX, "docx", "export_docx"),
}

STORED_EXTENSIONS: dict[str, str] = {XLSX: "xlsx", ODS: "ods", CSV: "csv", DOCX: "docx", PDF: "pdf"}

ALIAS_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
DRIVE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,128}$")

MiB = 1024 * 1024

# Tetos rígidos do perfil piloto: a config pode reduzir, nunca ultrapassar.
HARD_CAPS: dict[str, int] = {
    "max_sources": 25,
    "max_file_bytes": 50 * MiB,
    "max_run_bytes": 200 * MiB,
    "max_listing_pages": 20,
    "page_size": 1000,
    "request_timeout_seconds": 300,
    "max_retries": 3,
    "max_run_seconds": 3600,
}


@dataclass(frozen=True)
class Limits:
    max_sources: int = 10
    max_file_bytes: int = 10 * MiB
    max_run_bytes: int = 50 * MiB
    max_listing_pages: int = 5
    page_size: int = 100
    request_timeout_seconds: int = 60
    max_retries: int = 2
    max_run_seconds: int = 600


@dataclass(frozen=True)
class FileSource:
    alias: str
    family: str
    file_id: str


@dataclass(frozen=True)
class FolderSource:
    alias: str
    family: str
    folder_id: str
    mime_types: tuple[str, ...]
    name_pattern: str | None = None


@dataclass(frozen=True)
class CaptureConfig:
    credentials_file: Path
    data_dir: Path
    expected_identity: str
    shared_drive_id: str | None = None
    accepted_stored_mime_types: frozenset[str] = frozenset()
    limits: Limits = field(default_factory=Limits)
    files: tuple[FileSource, ...] = ()
    folders: tuple[FolderSource, ...] = ()

    def is_capturable_mime(self, mime: str) -> bool:
        return mime in GOOGLE_EXPORTS or mime in self.accepted_stored_mime_types


def _fail(detail: str) -> DriveCaptureError:
    return DriveCaptureError(Code.CONFIG_INVALID, detail)


def _resolve(base: Path, raw: object, field_name: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise _fail(f"{field_name} ausente")
    path = Path(raw).expanduser()
    return (path if path.is_absolute() else base / path).resolve()


def _ensure_outside_versioned_tree(path: Path, field_name: str) -> None:
    """Dentro do repositório, só ``_local_data/`` (ignorado pelo Git) é aceito."""
    if path.is_relative_to(REPO_ROOT) and not path.is_relative_to(REPO_ROOT / "_local_data"):
        raise _fail(f"{field_name} dentro do repositório fora de _local_data/")


def _family(raw: object, where: str) -> str:
    if raw not in FAMILIES:
        raise _fail(f"{where}.family deve ser uma de {', '.join(FAMILIES)}")
    return str(raw)


def _alias(raw: object, where: str) -> str:
    if not isinstance(raw, str) or not ALIAS_RE.match(raw):
        raise _fail(f"{where}.alias deve casar {ALIAS_RE.pattern}")
    return raw


def _drive_id(raw: object, where: str) -> str:
    if not isinstance(raw, str) or not DRIVE_ID_RE.match(raw):
        raise _fail(f"{where} não é um ID do Drive válido (cole o ID, não a URL)")
    return raw


def _limits(raw: object) -> Limits:
    if raw is None:
        return Limits()
    if not isinstance(raw, dict):
        raise _fail("limits deve ser um mapa")
    unknown = set(raw) - set(HARD_CAPS)
    if unknown:
        raise _fail(f"limits com chave desconhecida: {', '.join(sorted(unknown))}")
    values: dict[str, int] = {}
    for key, value in raw.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise _fail(f"limits.{key} deve ser inteiro não negativo")
        if value > HARD_CAPS[key]:
            raise _fail(f"limits.{key} acima do teto do piloto ({HARD_CAPS[key]})")
        values[key] = value
    limits = Limits(**values)
    if limits.max_sources < 1 or limits.page_size < 1 or limits.max_listing_pages < 1:
        raise _fail("max_sources, page_size e max_listing_pages devem ser >= 1")
    return limits


def parse_config(data: object, base_dir: Path) -> CaptureConfig:
    if not isinstance(data, dict):
        raise _fail("raiz deve ser um mapa")
    if data.get("version") != CONFIG_VERSION:
        raise _fail(f"version deve ser {CONFIG_VERSION}")

    credentials_file = _resolve(base_dir, data.get("credentials_file"), "credentials_file")
    _ensure_outside_versioned_tree(credentials_file, "credentials_file")
    data_dir = _resolve(base_dir, data.get("data_dir") or ".", "data_dir")
    _ensure_outside_versioned_tree(data_dir, "data_dir")

    expected_identity = data.get("expected_identity")
    if not isinstance(expected_identity, str) or "@" not in expected_identity:
        raise _fail("expected_identity obrigatório: e-mail da service account do cartório")
    shared_drive_id = data.get("shared_drive_id")
    if shared_drive_id is not None:
        shared_drive_id = _drive_id(shared_drive_id, "shared_drive_id")

    accepted = data.get("accepted_stored_mime_types") or []
    if not isinstance(accepted, list) or not set(accepted) <= set(STORED_EXTENSIONS):
        raise _fail("accepted_stored_mime_types só admite: " + ", ".join(sorted(STORED_EXTENSIONS)))

    aliases: set[str] = set()
    ids: set[str] = set()

    def _claim(alias: str, drive_id: str, where: str) -> None:
        if alias in aliases:
            raise _fail(f"{where}.alias repetido")
        if drive_id in ids:
            raise _fail(f"{where}: ID repetido — cada fonte é identificada pelo ID do Drive")
        aliases.add(alias)
        ids.add(drive_id)

    files: list[FileSource] = []
    for i, item in enumerate(data.get("files") or []):
        where = f"files[{i}]"
        if not isinstance(item, dict):
            raise _fail(f"{where} deve ser um mapa")
        source = FileSource(
            alias=_alias(item.get("alias"), where),
            family=_family(item.get("family"), where),
            file_id=_drive_id(item.get("file_id"), f"{where}.file_id"),
        )
        _claim(source.alias, source.file_id, where)
        files.append(source)

    allowed_child_mimes = set(GOOGLE_EXPORTS) | set(accepted)
    folders: list[FolderSource] = []
    for i, item in enumerate(data.get("folders") or []):
        where = f"folders[{i}]"
        if not isinstance(item, dict):
            raise _fail(f"{where} deve ser um mapa")
        include = item.get("include")
        if not isinstance(include, dict):
            raise _fail(f"{where}.include obrigatório — pasta sem regra de inclusão não entra")
        mime_types = include.get("mime_types")
        if not isinstance(mime_types, list) or not mime_types:
            raise _fail(f"{where}.include.mime_types obrigatório")
        if not set(mime_types) <= allowed_child_mimes:
            raise _fail(f"{where}.include.mime_types fora dos tipos capturáveis")
        name_pattern = include.get("name_pattern")
        if name_pattern is not None and (not isinstance(name_pattern, str) or not name_pattern):
            raise _fail(f"{where}.include.name_pattern deve ser texto não vazio")
        if item.get("recursive"):
            raise _fail(f"{where}.recursive não é suportado — declare a subpasta explicitamente")
        folder = FolderSource(
            alias=_alias(item.get("alias"), where),
            family=_family(item.get("family"), where),
            folder_id=_drive_id(item.get("folder_id"), f"{where}.folder_id"),
            mime_types=tuple(mime_types),
            name_pattern=name_pattern,
        )
        _claim(folder.alias, folder.folder_id, where)
        folders.append(folder)

    if not files and not folders:
        raise _fail("nenhuma fonte declarada em files ou folders")

    return CaptureConfig(
        credentials_file=credentials_file,
        data_dir=data_dir,
        expected_identity=expected_identity,
        shared_drive_id=shared_drive_id,
        accepted_stored_mime_types=frozenset(accepted),
        limits=_limits(data.get("limits")),
        files=tuple(files),
        folders=tuple(folders),
    )


def load_config(path: Path) -> CaptureConfig:
    if not path.is_file():
        raise _fail("arquivo de configuração não encontrado")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        raise _fail("arquivo de configuração ilegível ou YAML inválido") from None
    return parse_config(data, path.resolve().parent)
