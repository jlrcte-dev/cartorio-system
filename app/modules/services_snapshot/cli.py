"""CLI manual do retrato de serviços (fonte piloto).

Uso (raiz do repositório)::

    python -m app.modules.services_snapshot.cli refresh   # coleta + retrato + publicação
    python -m app.modules.services_snapshot.cli show      # último relatório válido; sem rede

refresh: 0 relatório válido publicado (mesmo com cobertura parcial) · 2 falha técnica
(último relatório preservado) · 4 outro refresh em andamento.
show: 0 relatório confirmado pela tentativa que o publicou · 1 relatório válido, mas a
última tentativa falhou ou não está confirmada · 2 relatório/registro local inválido ·
3 nenhum relatório ainda.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from app.core.logging import setup_logging
from app.modules.drive_capture.config import DEFAULT_CONFIG_PATH, load_config
from app.modules.drive_capture.errors import DriveCaptureError
from app.modules.services_snapshot.pipeline import refresh, show
from app.modules.services_snapshot.report import render_markdown

# Mesmo motivo do coletor: em DEBUG, urllib3/google registrariam URLs com o ID do arquivo.
_THIRD_PARTY_LOGGERS = ("urllib3", "requests", "google", "google.auth")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.modules.services_snapshot.cli",
        description="Retrato local de serviços por setor e status (planilha piloto).",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("refresh", "coleta a fonte piloto e publica o retrato, se válido"),
        ("show", "exibe o último retrato válido e a última tentativa (sem rede)"),
    ):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    return parser


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    for name in _THIRD_PARTY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
    args = _parser().parse_args(argv)
    try:
        config = load_config(args.config)
    except DriveCaptureError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        print("Guia: docs/modules/services_snapshot.md", file=sys.stderr)
        return 2
    try:
        if args.command == "show":
            code, text = show(config)
            print(text)
            return code
        code, report, attempt = refresh(config)
    except Exception as exc:  # traceback pode carregar texto privado
        print(f"ERRO: falha controlada ({type(exc).__name__})", file=sys.stderr)
        return 2
    if code == 4:
        print("Outro refresh em andamento (trava local presente); nada foi feito.", file=sys.stderr)
        return code
    if code == 0:
        print(render_markdown(report, attempt))
        if attempt is None:
            print(
                "AVISO: relatório publicado, mas o registro da tentativa não foi gravado;"
                " show indicará atualização não confirmada.",
                file=sys.stderr,
            )
        return 0
    print(
        f"ATUALIZAÇÃO FALHOU: etapa {attempt['etapa']}, código {attempt['codigo']}.",
        file=sys.stderr,
    )
    print("O último relatório válido foi preservado; use show para consultá-lo.", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
