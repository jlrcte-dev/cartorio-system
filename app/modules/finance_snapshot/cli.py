"""CLI offline da leitura local do Financeiro (demonstrativo diário de caixa).

Uso (raiz do repositório)::

    python -m app.modules.finance_snapshot.cli analyze \\
        --config <config isolada da fonte financeira> --run-id <run da captura> --periodo AAAA-MM

Tudo é obrigatório: não há config, run ou período padrão. Sem rede e sem credencial.
Saída: 0 relatório local validado e publicado (mesmo com lacunas declaradas) · 2 falha
técnica com etapa e código controlados — relatório anterior preservado, exceto em
``publicacao_inconsistente``, que diz o estado real. O terminal recebe só contagens e
códigos; valores ficam no relatório privado do data_dir.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from app.core.logging import setup_logging
from app.modules.drive_capture.config import load_config
from app.modules.drive_capture.errors import DriveCaptureError
from app.modules.finance_snapshot.pipeline import (
    LATEST,
    LATEST_MD,
    SNAPSHOT_DIR,
    AnalyzeFailed,
    analyze,
)
from app.modules.finance_snapshot.report import render_summary

_RUN = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{6}$")
_PERIOD = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.modules.finance_snapshot.cli",
        description="Leitura local offline do demonstrativo financeiro capturado.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser(
        "analyze", help="lê a geração do run informado e publica o relatório local"
    )
    cmd.add_argument(
        "--config", type=Path, required=True, help="config isolada da fonte financeira"
    )
    cmd.add_argument(
        "--run-id", required=True, help="run da captura a ler (nenhuma outra é buscada)"
    )
    cmd.add_argument("--periodo", required=True, help="período aprovado, AAAA-MM")
    return parser


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = _parser().parse_args(argv)
    period = _PERIOD.match(args.periodo)
    if not _RUN.match(args.run_id) or not period:
        print(
            "ERRO: --run-id ou --periodo fora do formato (AAAAMMDDTHHMMSSZ-xxxxxx, AAAA-MM).",
            file=sys.stderr,
        )
        return 2
    try:
        config = load_config(args.config)
    except DriveCaptureError as exc:
        print(f"ERRO: configuração recusada ({exc.code}).", file=sys.stderr)
        return 2
    try:
        report = analyze(config, args.run_id, (int(period.group(1)), int(period.group(2))))
    except AnalyzeFailed as failed:
        if failed.code == "publicacao_inconsistente":
            state = (
                "latest.json não foi alterado, mas latest.md NÃO pôde ser restaurado e "
                "corresponde à tentativa recusada; rode analyze de novo antes de usá-lo."
            )
        else:
            state = "O relatório anterior, se houver, foi preservado."
        print(
            f"LEITURA FALHOU: etapa {failed.stage}, código {failed.code}. {state}", file=sys.stderr
        )
        return 2
    except Exception as exc:  # traceback pode carregar conteúdo de célula
        print(f"ERRO: falha controlada ({type(exc).__name__}).", file=sys.stderr)
        return 2
    print(render_summary(report))
    print(f"Relatório privado: {SNAPSHOT_DIR}/{LATEST} e {LATEST_MD} no diretório de dados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
