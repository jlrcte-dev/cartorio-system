"""Relatório sanitizado de cobertura: JSON técnico versionado + Markdown para revisão.

Contém só aliases locais, famílias, datas, contagens e códigos controlados. Nunca:
IDs ou URLs do Drive, títulos, nomes de pessoas, conteúdo, valores, hashes de conteúdo,
caminhos locais ou mensagens remotas. Este é o único artefato desta etapa reservado em
``exports/atlas/``; nenhum consumidor do Atlas o lê ainda.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.modules.drive_capture.collector import FolderOutcome, RunResult, SourceOutcome
from app.modules.drive_capture.config import FAMILIES, CaptureConfig
from app.modules.drive_capture.errors import MESSAGES, Code
from app.modules.drive_capture.store import atomic_write_json, iso, utc_now

CONTRACT = "cartorio_system.drive_capture.report"
CONTRACT_VERSION = "1.0"

NOTICE = (
    "Sinais técnicos de leitura. Versão/modifiedTime do Drive e hash da exportação não "
    "provam que um serviço avançou nem que houve erro; última modificação não prova o "
    "período coberto; ausência de atualização não prova ausência de trabalho; 404/403 "
    "significam indisponível para a identidade, não exclusão."
)

_SOURCE_FIELDS = (
    "alias",
    "family",
    "origin",
    "folder_alias",
    "result",
    "code",
    "attempt_at",
    "last_success_at",
    "drive_modified_time",
    "drive_version",
    "bytes",
    "method",
    "consistency_retry",
    "signals",
)


def _source_dict(outcome: SourceOutcome) -> dict[str, Any]:
    raw = asdict(outcome)
    return {name: raw[name] for name in _SOURCE_FIELDS}


def _family_status(
    family: str, config: CaptureConfig, sources: list[SourceOutcome], folders: list[FolderOutcome]
) -> dict[str, Any]:
    configured = any(f.family == family for f in config.files) or any(
        f.family == family for f in config.folders
    )
    fam_sources = [s for s in sources if s.family == family]
    fam_folders = [f for f in folders if f.family == family]
    captured = sum(1 for s in fam_sources if s.result == "captured")
    not_captured = len(fam_sources) - captured
    folders_ok = all(f.listing == "complete" for f in fam_folders)
    if not configured:
        status = "not_configured"
    elif not fam_sources and fam_folders and folders_ok:
        status = "empty_listing"
    elif captured and not not_captured and folders_ok:
        status = "complete"
    elif captured:
        status = "partial"
    else:
        status = "failed"
    return {
        "family": family,
        "status": status,
        "sources": len(fam_sources),
        "captured": captured,
        "not_captured": not_captured,
        "folders": len(fam_folders),
        "folders_listing_complete": sum(1 for f in fam_folders if f.listing == "complete"),
    }


def build_report(result: RunResult, config: CaptureConfig) -> dict[str, Any]:
    sources = result.sources
    return {
        "contract": CONTRACT,
        "contract_version": CONTRACT_VERSION,
        "generated_at": iso(utc_now()),
        "notice": NOTICE,
        "run": {
            "run_id": result.run_id,
            "mode": "manual",
            "started_at": iso(result.started_at),
            "finished_at": iso(result.finished_at) if result.finished_at else None,
            "status": result.status,
            "identity_verified": result.identity_verified,
            "global_code": result.global_code,
        },
        "totals": {
            "sources": len(sources),
            "captured": sum(1 for s in sources if s.result == "captured"),
            "failed": sum(1 for s in sources if s.result == "failed"),
            "skipped": sum(1 for s in sources if s.result == "skipped"),
            "bytes_captured": sum(s.bytes or 0 for s in sources if s.result == "captured"),
            "folders": len(result.folders),
            "folders_listing_complete": sum(1 for f in result.folders if f.listing == "complete"),
        },
        "families": [
            _family_status(family, config, sources, result.folders) for family in FAMILIES
        ],
        "folders": [asdict(f) for f in result.folders],
        "sources": [_source_dict(s) for s in sources],
    }


def write_json_report(report: dict[str, Any], path: Path) -> None:
    atomic_write_json(path, report)


def _code_text(code: str | None) -> str:
    if not code:
        return "—"
    try:
        return f"`{code}` — {MESSAGES[Code(code)]}"
    except ValueError:
        return f"`{code}`"


def _signals_text(signals: dict[str, bool | None]) -> str:
    if not signals or all(v is None for v in signals.values()):
        return "primeira captura"
    labels = {
        "version_changed": "versão",
        "modified_time_changed": "modifiedTime",
        "content_hash_changed": "hash",
    }
    changed = [labels[k] for k, v in signals.items() if v]
    return "mudou: " + ", ".join(changed) if changed else "sem sinal de alteração"


def render_markdown(report: dict[str, Any]) -> str:
    run = report["run"]
    totals = report["totals"]
    lines = [
        "# Coleta do Drive do cartório — relatório sanitizado",
        "",
        f"Contrato `{report['contract']}` v{report['contract_version']} · "
        f"gerado em {report['generated_at']} (UTC)",
        "",
        f"> {report['notice']}",
        "",
        "## Execução",
        "",
        f"- run: `{run['run_id']}` (modo {run['mode']})",
        f"- início/fim (UTC): {run['started_at']} → {run['finished_at']}",
        f"- resultado global: **{run['status']}**",
        f"- identidade conferida: {'sim' if run['identity_verified'] else 'não'}",
        f"- falha global: {_code_text(run['global_code'])}",
        f"- fontes: {totals['sources']} · capturadas {totals['captured']} · "
        f"falhas {totals['failed']} · não tentadas {totals['skipped']} · "
        f"{totals['bytes_captured']} bytes",
        "",
        "## Cobertura por família",
        "",
        "| Família | Situação | Fontes | Capturadas | Não capturadas | "
        "Pastas (listagem completa) |",
        "|---|---|---|---|---|---|",
    ]
    for fam in report["families"]:
        lines.append(
            f"| {fam['family']} | {fam['status']} | {fam['sources']} | {fam['captured']} | "
            f"{fam['not_captured']} | {fam['folders']} ({fam['folders_listing_complete']}) |"
        )
    if report["folders"]:
        lines += [
            "",
            "## Pastas autorizadas",
            "",
            "| Pasta | Família | Listagem | Código | Vistos | Elegíveis | Subpastas | "
            "Atalhos | Outro tipo | Fora do padrão | Já cobertos | Saíram |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for f in report["folders"]:
            lines.append(
                f"| {f['alias']} | {f['family']} | {f['listing']} | {f['code'] or '—'} | "
                f"{f['children_seen']} | {f['eligible']} | {f['ignored_subfolders']} | "
                f"{f['ignored_shortcuts']} | {f['ignored_mime']} | "
                f"{f['not_matching_pattern']} | {f['already_covered']} | {f['departed']} |"
            )
    lines += [
        "",
        "## Fontes",
        "",
        "| Fonte | Família | Resultado | Código | Tentativa | Último sucesso | "
        "modifiedTime (Drive) | Versão | Bytes | Método | Sinal |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in report["sources"]:
        signal = _signals_text(s["signals"]) if s["result"] == "captured" else "—"
        retry = " (1 nova tentativa de consistência)" if s["consistency_retry"] else ""
        lines.append(
            f"| {s['alias']} | {s['family']} | {s['result']}{retry} | {s['code'] or '—'} | "
            f"{s['attempt_at']} | {s['last_success_at'] or '—'} | "
            f"{s['drive_modified_time'] or '—'} | {s['drive_version'] or '—'} | "
            f"{s['bytes'] if s['bytes'] is not None else '—'} | {s['method'] or '—'} | {signal} |"
        )
    codes = sorted({s["code"] for s in report["sources"] if s["code"]})
    if codes:
        lines += ["", "## Códigos desta execução", ""]
        lines += [f"- {_code_text(c)}" for c in codes]
    lines.append("")
    return "\n".join(lines)
