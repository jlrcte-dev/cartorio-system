"""CLI manual e opt-in do coletor somente leitura do Drive do cartório.

Uso (a partir da raiz do repositório)::

    python -m app.modules.drive_capture.cli check
    python -m app.modules.drive_capture.cli collect

``check`` confere identidade, escopo, fronteira e acesso a metadados — não baixa nada.
``collect`` captura as fontes elegíveis e gera o relatório sanitizado. Toda saída do
terminal usa só aliases locais e códigos controlados.

Saída: 0 = completa · 1 = parcial · 2 = falhou ou configuração inválida.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from app.core.logging import setup_logging
from app.modules.drive_capture.collector import Collector, RunResult
from app.modules.drive_capture.config import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_REPORT_JSON,
    CaptureConfig,
    load_config,
)
from app.modules.drive_capture.drive_client import DriveClient
from app.modules.drive_capture.errors import MESSAGES, Code, DriveCaptureError
from app.modules.drive_capture.report import build_report, render_markdown, write_json_report
from app.modules.drive_capture.store import CaptureStore, atomic_write_bytes

EXIT = {"complete": 0, "partial": 1, "failed": 2}


# Em DEBUG, urllib3 registra a linha da requisição (com o ID do arquivo) e google.auth
# registra chamadas de token. O nível do Atlas/cartório vem do .env; aqui ele não manda.
_THIRD_PARTY_LOGGERS = ("urllib3", "requests", "google", "google.auth")


def _quiet_third_party_loggers() -> None:
    for name in _THIRD_PARTY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.modules.drive_capture.cli",
        description="Coletor somente leitura das fontes autorizadas do Drive do cartório.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("check", "valida identidade, escopo, fronteira e acesso a metadados (sem download)"),
        ("collect", "captura as fontes elegíveis e gera o relatório sanitizado"),
    ):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument(
            "--config",
            type=Path,
            default=DEFAULT_CONFIG_PATH,
            help="config local não versionada (padrão: _local_data/drive_capture/config.yaml)",
        )
    sub.choices["collect"].add_argument(
        "--report-json",
        type=Path,
        default=DEFAULT_REPORT_JSON,
        help="JSON técnico sanitizado (padrão: exports/atlas/cartorio_drive_capture_report.json)",
    )
    return parser


def _make_collector(config: CaptureConfig) -> tuple[Collector, str]:
    # Import tardio: só aqui a dependência do Google é carregada e a credencial é lida.
    from app.modules.drive_capture.auth import build_transport

    transport, identity = build_transport(config)
    client = DriveClient(
        transport,
        shared_drive_id=config.shared_drive_id,
        max_retries=config.limits.max_retries,
    )
    return Collector(config, client, CaptureStore(config.data_dir)), identity


def _print_sources(result: RunResult) -> None:
    for s in result.sources:
        detail = s.code or s.method or ""
        print(f"  {s.alias:<28} {s.family:<26} {s.result:<9} {detail}")


def _print_folders(result: RunResult) -> None:
    for f in result.folders:
        print(
            f"  pasta {f.alias:<22} listagem={f.listing:<8} código={f.code or '-'} "
            f"vistos={f.children_seen} elegíveis={f.eligible} subpastas={f.ignored_subfolders} "
            f"atalhos={f.ignored_shortcuts} outro_tipo={f.ignored_mime} "
            f"fora_do_padrão={f.not_matching_pattern} saíram={f.departed}"
        )


def _check(config: CaptureConfig) -> int:
    collector, identity = _make_collector(config)
    print("Credencial: service account carregada · escopo drive.readonly (único)")
    result = collector.preflight(identity)
    if result.global_code:
        print(f"FALHA: {result.global_code} — {MESSAGES[Code(result.global_code)]}")
        return 2
    print("Identidade autenticada confere com expected_identity.")
    _print_folders(result)
    _print_sources(result)
    failed = sum(1 for s in result.sources if s.result != "eligible")
    partial = failed or any(f.listing != "complete" for f in result.folders)
    print(f"Fontes elegíveis: {len(result.sources) - failed} de {len(result.sources)}")
    return 1 if partial else 0


def _collect(config: CaptureConfig, report_json: Path) -> int:
    collector, identity = _make_collector(config)
    result = collector.run(identity)
    report = build_report(result, config)
    write_json_report(report, report_json)
    md_path = config.data_dir / "reports" / "latest.md"
    atomic_write_bytes(md_path, render_markdown(report).encode("utf-8"))
    _print_folders(result)
    _print_sources(result)
    totals = report["totals"]
    print(
        f"Resultado: {result.status} · capturadas {totals['captured']} · "
        f"falhas {totals['failed']} · não tentadas {totals['skipped']}"
    )
    if result.global_code:
        print(f"FALHA GLOBAL: {result.global_code} — {MESSAGES[Code(result.global_code)]}")
    print("Relatório JSON: (gravado no caminho de --report-json)")
    print("Relatório Markdown: reports/latest.md no diretório de dados")
    return EXIT[result.status]


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    _quiet_third_party_loggers()
    args = _build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        if args.command == "check":
            return _check(config)
        return _collect(config, args.report_json)
    except DriveCaptureError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        if exc.code == Code.CONFIG_INVALID:
            print("Modelo: docs/modules/drive_capture.config.example.yaml", file=sys.stderr)
        print("Guia de configuração: docs/modules/drive_capture.md", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
