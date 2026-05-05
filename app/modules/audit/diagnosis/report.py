"""Report generators for DocumentDiagnosis.

All functions write exclusively to the caller-supplied output directory.
They never open any file listed in the diagnosis candidates.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.audit.diagnosis.models import (
    DIAGNOSIS_VERSION,
    DiagnosisCandidate,
    DiagnosisResult,
)

_CSV_HEADERS = [
    "candidate_id",
    "rule_id",
    "rule_name",
    "category",
    "severity",
    "priority",
    "title",
    "status",
    "confidence",
    "related_file_path",
    "related_parent_path",
    "related_extension",
    "related_size_bytes",
    "related_modified_at",
    "recommended_action",
    "notes",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _sha256_file(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _json_default(o: object) -> str:
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


def _sev_order(sev: str) -> int:
    return {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFORMATIONAL": 4}.get(sev, 9)


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------


def write_json(result: DiagnosisResult, output_dir: Path) -> Path:
    """Write *document_diagnosis.json* and return the path."""
    _ensure_dir(output_dir)
    out = output_dir / "document_diagnosis.json"
    payload: dict[str, Any] = result.model_dump(mode="json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, default=_json_default, indent=2, ensure_ascii=False)
    return out


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------


def write_csv(result: DiagnosisResult, output_dir: Path) -> Path:
    """Write *document_diagnosis.csv* (UTF-8 with BOM for Excel) and return the path."""
    _ensure_dir(output_dir)
    out = output_dir / "document_diagnosis.csv"
    with open(out, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(_CSV_HEADERS)
        for c in result.candidates:
            writer.writerow(
                [
                    c.candidate_id,
                    c.rule_id,
                    c.rule_name,
                    c.category,
                    c.severity,
                    c.priority,
                    c.title,
                    c.status,
                    c.confidence,
                    c.related_file_path,
                    c.related_parent_path,
                    c.related_extension,
                    c.related_size_bytes if c.related_size_bytes is not None else "",
                    c.related_modified_at,
                    c.recommended_action,
                    c.notes,
                ]
            )
    return out


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------


def write_markdown(result: DiagnosisResult, output_dir: Path) -> Path:
    """Write *document_diagnosis.md* and return the path."""
    _ensure_dir(output_dir)
    out = output_dir / "document_diagnosis.md"
    lines: list[str] = []

    def h(level: int, text: str) -> None:
        lines.append(f"{'#' * level} {text}\n")

    def p(text: str = "") -> None:
        lines.append(text + "\n")

    def tr(*cols: str) -> None:
        lines.append("| " + " | ".join(cols) + " |\n")

    def tsep(*widths: int) -> None:
        lines.append("| " + " | ".join("-" * w for w in widths) + " |\n")

    # --- Header ---
    h(1, f"Diagnóstico Documental — {result.run_name}")
    p()
    p("> **AVISO IMPORTANTE — Análise baseada exclusivamente em metadados.**  ")
    p(
        "> Nenhum arquivo original foi aberto, lido ou modificado. "
        "Os candidatos identificados são sugestões para revisão humana — "
        "não representam achados definitivos, irregularidades confirmadas "
        "ou afirmações sobre o conteúdo dos arquivos."
    )
    p()

    # --- Summary ---
    h(2, "Resumo")
    p()
    p(f"- **Diagnosis ID:** `{result.diagnosis_id}`")
    p(f"- **Run name:** {result.run_name}")
    p(f"- **Scanner Run ID:** `{result.scanner_run_id}`")
    p(f"- **Gerado em:** {result.generated_at}")
    p(f"- **Arquivos analisados:** {result.total_files_analyzed:,}")
    p(f"- **Candidatos identificados:** {result.total_candidates}")
    p()

    # Severity distribution
    sev_counts: dict[str, int] = defaultdict(int)
    for c in result.candidates:
        sev_counts[str(c.severity)] += 1

    if sev_counts:
        h(3, "Distribuição por severidade")
        p()
        tr("Severidade", "Candidatos")
        tsep(14, 12)
        for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"):
            if sev in sev_counts:
                tr(sev, str(sev_counts[sev]))
        p()

    if not result.candidates:
        p("_Nenhum candidato identificado com os parâmetros atuais._")
        p()
    else:
        # --- Candidates grouped by rule ---
        h(2, "Candidatos por regra")
        p()
        by_rule: dict[str, list[DiagnosisCandidate]] = defaultdict(list)
        for c in result.candidates:
            by_rule[c.rule_id].append(c)

        for rule_id, rule_candidates in sorted(by_rule.items()):
            first = rule_candidates[0]
            h(3, f"{rule_id} — {first.rule_name.replace('_', ' ').title()}")
            p()
            p(f"**Severidade:** {first.severity} | **Prioridade:** {first.priority}")
            p()
            for c in rule_candidates:
                p(f"**{c.title}**")
                p()
                p(f"_{c.description}_")
                p()
                p(f"- **Evidência:** {c.evidence_summary}")
                if c.related_file_path:
                    p(f"- **Arquivo:** `{c.related_file_path}`")
                if c.related_parent_path and not c.related_file_path:
                    p(f"- **Pasta:** `{c.related_parent_path}`")
                p(f"- **Ação recomendada:** {c.recommended_action}")
                p(f"- **Confiança:** {c.confidence:.0%}")
                if c.notes:
                    p()
                    p("<details><summary>Detalhes</summary>")
                    p()
                    p(f"```\n{c.notes}\n```")
                    p()
                    p("</details>")
                p()
            p("---")
            p()

    # --- Safety footer ---
    h(2, "Aviso de segurança operacional")
    p()
    p("Esta análise foi executada em **modo estritamente baseado em metadados**.")
    p()
    p("- Nenhum arquivo original foi aberto para leitura de conteúdo.")
    p("- Nenhum arquivo foi modificado, movido, renomeado ou excluído.")
    p("- Nenhum dado pessoal ou financeiro foi lido dos arquivos analisados.")
    p("- Os candidatos identificados requerem **validação manual** antes de qualquer ação.")
    p("- Não criar `AuditFinding` sem revisão humana dos candidatos.")
    p()
    p(f"_Gerado pelo Cartório System — DocumentDiagnosis v{DIAGNOSIS_VERSION}_")

    with open(out, "w", encoding="utf-8") as fh:
        fh.writelines(lines)
    return out


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def write_manifest(
    result: DiagnosisResult,
    output_dir: Path,
    output_files: dict[str, Path],
) -> Path:
    """Write *diagnosis_manifest.json* with SHA-256 hashes of generated artefacts."""
    _ensure_dir(output_dir)
    out = output_dir / "diagnosis_manifest.json"

    file_hashes: dict[str, str] = {}
    file_sizes: dict[str, int] = {}
    for label, path in output_files.items():
        if path.exists():
            file_hashes[label] = _sha256_file(path)
            file_sizes[label] = path.stat().st_size

    manifest: dict[str, Any] = {
        "diagnosis_id": result.diagnosis_id,
        "run_name": result.run_name,
        "generated_at": result.generated_at,
        "scanner_run_id": result.scanner_run_id,
        "diagnosis_version": DIAGNOSIS_VERSION,
        "read_only": True,
        "content_read": False,
        "original_files_accessed": False,
        "counts": {
            "total_files_analyzed": result.total_files_analyzed,
            "total_candidates": result.total_candidates,
        },
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


def write_all(result: DiagnosisResult, output_dir: str | Path) -> dict[str, Path]:
    """Write all four artefacts and return a ``{label: path}`` mapping."""
    out = Path(output_dir)
    _ensure_dir(out)

    json_path = write_json(result, out)
    csv_path = write_csv(result, out)
    md_path = write_markdown(result, out)

    output_files = {
        "document_diagnosis_json": json_path,
        "document_diagnosis_csv": csv_path,
        "document_diagnosis_md": md_path,
    }

    manifest_path = write_manifest(result, out, output_files)
    output_files["diagnosis_manifest_json"] = manifest_path

    return output_files
