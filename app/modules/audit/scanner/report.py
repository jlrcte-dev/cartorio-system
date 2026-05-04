"""Report generators for the read-only file scanner.

All functions in this module write exclusively to the caller-supplied
output directory.  They never read from or write to the scanned tree.
"""

from __future__ import annotations

import csv
import dataclasses
import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.modules.audit.scanner.models import ScanResult

SCANNER_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dt_to_iso(dt: datetime | None) -> str:
    return dt.isoformat() if dt is not None else ""


def _bytes_human(n: int) -> str:
    """Return a human-readable size string (e.g. '1.23 MB')."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.2f} {unit}" if unit != "B" else f"{n} B"
        n //= 1024  # type: ignore[assignment]
    return f"{n} B"


def _sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of an already-written output file."""
    sha = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _json_default(o: object) -> str:
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# JSON inventory
# ---------------------------------------------------------------------------


def write_json(result: ScanResult, output_dir: Path) -> Path:
    """Write *file_inventory.json* and return the path."""
    _ensure_dir(output_dir)
    out = output_dir / "file_inventory.json"

    payload: dict[str, Any] = {
        "metadata": {
            "run_id": result.run_id,
            "run_name": result.run_name,
            "root_path": result.root_path_display,
            "started_at": _dt_to_iso(result.started_at),
            "finished_at": _dt_to_iso(result.finished_at),
            "duration_seconds": round(result.duration_seconds, 3),
            "total_files": result.total_files,
            "total_directories": result.total_directories,
            "total_size_bytes": result.total_size_bytes,
            "errors_count": result.errors_count,
            "excluded_count": result.excluded_count,
        },
        "parameters": dataclasses.asdict(result.parameters),
        "files": [dataclasses.asdict(f) for f in result.files],
        "directories": [dataclasses.asdict(d) for d in result.directories],
        "errors": [dataclasses.asdict(e) for e in result.errors],
    }

    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, default=_json_default, indent=2, ensure_ascii=False)

    return out


# ---------------------------------------------------------------------------
# CSV inventory
# ---------------------------------------------------------------------------

_CSV_HEADERS = [
    "entry_type",
    "name",
    "extension",
    "path_relative",
    "parent_path",
    "depth",
    "size_bytes",
    "modified_at",
    "created_at",
    "direct_files",
    "direct_subdirs",
    "total_size_bytes",
    "error",
]


def write_csv(result: ScanResult, output_dir: Path) -> Path:
    """Write *file_inventory.csv* (UTF-8 with BOM for Excel) and return the path."""
    _ensure_dir(output_dir)
    out = output_dir / "file_inventory.csv"

    with open(out, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(_CSV_HEADERS)

        for d in result.directories:
            writer.writerow(
                [
                    d.entry_type,
                    d.name,
                    "",
                    d.path_relative,
                    d.parent_path,
                    d.depth,
                    "",
                    "",
                    "",
                    d.direct_files,
                    d.direct_subdirs,
                    d.total_size_bytes,
                    d.error or "",
                ]
            )

        for f in result.files:
            writer.writerow(
                [
                    f.entry_type,
                    f.name,
                    f.extension,
                    f.path_relative,
                    f.parent_path,
                    f.depth,
                    f.size_bytes,
                    _dt_to_iso(f.modified_at),
                    _dt_to_iso(f.created_at),
                    "",
                    "",
                    "",
                    f.error or "",
                ]
            )

    return out


# ---------------------------------------------------------------------------
# Markdown summary
# ---------------------------------------------------------------------------

_TOP_N = 10


def write_markdown(result: ScanResult, output_dir: Path) -> Path:
    """Write *scan_summary.md* and return the path."""
    _ensure_dir(output_dir)
    out = output_dir / "scan_summary.md"

    lines: list[str] = []

    def h(level: int, text: str) -> None:
        lines.append(f"{'#' * level} {text}\n")

    def p(text: str = "") -> None:
        lines.append(text + "\n")

    def table_row(*cols: str) -> None:
        lines.append("| " + " | ".join(cols) + " |\n")

    def table_sep(*widths: int) -> None:
        lines.append("| " + " | ".join("-" * w for w in widths) + " |\n")

    h(1, f"Relatório de Varredura — {result.run_name}")
    p()
    p("> **Este relatório foi gerado em modo estritamente somente leitura (read-only).**")
    p("> Nenhum arquivo foi modificado, movido, renomeado ou excluído durante a execução.")
    p()

    h(2, "Resumo executivo")
    p()
    p(f"- **Run ID:** `{result.run_id}`")
    p(f"- **Run name:** {result.run_name}")
    p(f"- **Início:** {_dt_to_iso(result.started_at)}")
    p(f"- **Fim:** {_dt_to_iso(result.finished_at)}")
    p(f"- **Duração:** {result.duration_seconds:.2f}s")
    p(f"- **Total de arquivos:** {result.total_files:,}")
    p(f"- **Total de pastas:** {result.total_directories:,}")
    p(
        f"- **Tamanho total:** {_bytes_human(result.total_size_bytes)}"
        f" ({result.total_size_bytes:,} bytes)"
    )
    p(f"- **Itens excluídos:** {result.excluded_count:,}")
    p(f"- **Erros de acesso:** {result.errors_count:,}")
    p()

    # Extension distribution
    h(2, "Distribuição por extensão")
    p()
    ext_counts: dict[str, int] = {}
    ext_sizes: dict[str, int] = {}
    for f in result.files:
        key = f.extension if f.extension else "(sem extensão)"
        ext_counts[key] = ext_counts.get(key, 0) + 1
        ext_sizes[key] = ext_sizes.get(key, 0) + f.size_bytes
    top_exts = sorted(ext_counts.items(), key=lambda x: x[1], reverse=True)[:_TOP_N]
    if top_exts:
        table_row("Extensão", "Quantidade", "Tamanho total")
        table_sep(12, 12, 16)
        for ext, count in top_exts:
            table_row(ext, str(count), _bytes_human(ext_sizes.get(ext, 0)))
    else:
        p("_Nenhum arquivo encontrado._")
    p()

    # Top 10 largest files
    h(2, f"Top {_TOP_N} maiores arquivos")
    p()
    top_files = sorted(result.files, key=lambda f: f.size_bytes, reverse=True)[:_TOP_N]
    if top_files:
        table_row("Arquivo", "Tamanho", "Modificado em")
        table_sep(50, 12, 24)
        for f in top_files:
            table_row(
                f"`{f.path_relative}`",
                _bytes_human(f.size_bytes),
                _dt_to_iso(f.modified_at),
            )
    else:
        p("_Nenhum arquivo encontrado._")
    p()

    # Top 10 largest directories
    h(2, f"Top {_TOP_N} pastas com mais arquivos diretos")
    p()
    top_dirs = sorted(result.directories, key=lambda d: d.direct_files, reverse=True)[:_TOP_N]
    if top_dirs:
        table_row("Pasta", "Arquivos diretos", "Tamanho direto")
        table_sep(50, 18, 16)
        for d in top_dirs:
            table_row(
                f"`{d.path_relative}`",
                str(d.direct_files),
                _bytes_human(d.total_size_bytes),
            )
    else:
        p("_Nenhuma pasta encontrada._")
    p()

    # Oldest files by modification date
    h(2, f"Top {_TOP_N} arquivos mais antigos (por data de modificação)")
    p()
    files_with_mtime = [f for f in result.files if f.modified_at is not None]
    oldest = sorted(files_with_mtime, key=lambda f: f.modified_at)[:_TOP_N]  # type: ignore[arg-type, return-value]
    if oldest:
        table_row("Arquivo", "Tamanho", "Modificado em")
        table_sep(50, 12, 24)
        for f in oldest:
            table_row(
                f"`{f.path_relative}`",
                _bytes_human(f.size_bytes),
                _dt_to_iso(f.modified_at),
            )
    else:
        p("_Nenhum arquivo com data de modificação disponível._")
    p()

    # Recently modified files
    h(2, f"Top {_TOP_N} arquivos modificados mais recentemente")
    p()
    recent = sorted(
        files_with_mtime,
        key=lambda f: f.modified_at,  # type: ignore[arg-type, return-value]
        reverse=True,
    )[:_TOP_N]
    if recent:
        table_row("Arquivo", "Tamanho", "Modificado em")
        table_sep(50, 12, 24)
        for f in recent:
            table_row(
                f"`{f.path_relative}`",
                _bytes_human(f.size_bytes),
                _dt_to_iso(f.modified_at),
            )
    else:
        p("_Nenhum arquivo com data de modificação disponível._")
    p()

    # Errors
    h(2, "Erros de acesso")
    p()
    if result.errors:
        table_row("Caminho", "Tipo", "Mensagem")
        table_sep(40, 20, 50)
        for e in result.errors:
            table_row(f"`{e.path_relative}`", e.error_type, e.message[:60])
    else:
        p("_Nenhum erro de acesso registrado._")
    p()

    # Security observations
    h(2, "Observações de segurança")
    p()
    suspicious_exts = {".exe", ".bat", ".cmd", ".ps1", ".vbs", ".scr", ".msi", ".reg"}
    susp_files = [f for f in result.files if f.extension in suspicious_exts]
    if susp_files:
        p(
            f"⚠️ **{len(susp_files)} arquivo(s) com extensão executável ou sensível** "
            f"encontrado(s) na estrutura varrida."
        )
        for f in susp_files[:10]:
            p(f"  - `{f.path_relative}`")
        if len(susp_files) > 10:
            p(f"  - ... e mais {len(susp_files) - 10} arquivo(s).")
    else:
        p("✅ Nenhum arquivo com extensão executável ou potencialmente suspeita identificado.")
    p()
    p(
        "_Esta seção é baseada somente em metadados (nome e extensão)._"
        " _O conteúdo dos arquivos não foi lido._"
    )
    p()

    h(2, "Aviso de execução read-only")
    p()
    p("Esta varredura foi executada em **modo estritamente somente leitura**.")
    p()
    p("- Nenhum arquivo foi aberto para leitura de conteúdo.")
    p("- Nenhum arquivo foi modificado, movido, renomeado ou excluído.")
    p("- Nenhuma permissão foi alterada.")
    p("- Nenhum dado foi gravado na árvore de diretórios analisada.")
    p("- Os resultados foram gravados exclusivamente no diretório de saída configurado.")
    p()
    p(f"_Gerado pelo Cartório System — Scanner v{SCANNER_VERSION}_")

    with open(out, "w", encoding="utf-8") as fh:
        fh.writelines(lines)

    return out


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def write_manifest(
    result: ScanResult,
    output_dir: Path,
    output_files: dict[str, Path],
) -> Path:
    """Write *scan_manifest.json* with hashes of the generated artefacts."""
    _ensure_dir(output_dir)
    out = output_dir / "scan_manifest.json"

    file_hashes: dict[str, str] = {}
    file_sizes: dict[str, int] = {}
    for label, path in output_files.items():
        if path.exists():
            file_hashes[label] = _sha256_file(path)
            file_sizes[label] = path.stat().st_size

    manifest: dict[str, Any] = {
        "manifest_id": str(uuid.uuid4()),
        "generated_at": datetime.now(UTC).isoformat(),
        "scanner_version": SCANNER_VERSION,
        "read_only": True,
        "run": {
            "run_id": result.run_id,
            "run_name": result.run_name,
            "root_path": result.root_path_display,
            "started_at": _dt_to_iso(result.started_at),
            "finished_at": _dt_to_iso(result.finished_at),
            "duration_seconds": round(result.duration_seconds, 3),
        },
        "counts": {
            "total_files": result.total_files,
            "total_directories": result.total_directories,
            "total_size_bytes": result.total_size_bytes,
            "errors_count": result.errors_count,
            "excluded_count": result.excluded_count,
        },
        "parameters": dataclasses.asdict(result.parameters),
        "output_files": {
            label: {
                "filename": path.name,
                "size_bytes": file_sizes.get(label, 0),
                "sha256": file_hashes.get(label, ""),
            }
            for label, path in output_files.items()
        },
    }

    with open(out, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)

    return out


# ---------------------------------------------------------------------------
# Convenience: write all outputs at once
# ---------------------------------------------------------------------------


def write_all(result: ScanResult, output_dir: str | Path) -> dict[str, Path]:
    """Write all four artefacts and return a ``{label: path}`` mapping."""
    out = Path(output_dir)
    _ensure_dir(out)

    json_path = write_json(result, out)
    csv_path = write_csv(result, out)
    md_path = write_markdown(result, out)

    output_files = {
        "file_inventory_json": json_path,
        "file_inventory_csv": csv_path,
        "scan_summary_md": md_path,
    }

    manifest_path = write_manifest(result, out, output_files)
    output_files["scan_manifest_json"] = manifest_path

    return output_files
