"""CLI offline da leitura local do Financeiro (demonstrativo diário de caixa).

Uso (raiz do repositório)::

    python -m app.modules.finance_snapshot.cli analyze \\
        --config <config isolada da fonte financeira> --run-id <run da captura> --periodo AAAA-MM
    python -m app.modules.finance_snapshot.cli export-atlas \\
        --config <config isolada da fonte financeira> --run-id <run do relatório> --periodo AAAA-MM

Tudo é obrigatório: não há config, run ou período padrão. Sem rede e sem credencial.
analyze: 0 relatório local validado e publicado (mesmo com lacunas declaradas) · 2 falha
técnica com etapa e código controlados — relatório anterior preservado, exceto em
``publicacao_inconsistente``, que diz o estado real.
export-atlas (lê só ``latest.json``): 0 exportação válida publicada, inclusive com lacunas
declaradas · 2 falha técnica ou entrada recusada, com o estado real do arquivo · 3 nenhum
relatório · 4 outra exportação financeira em andamento.
O terminal recebe só contagens e códigos; valores ficam nos arquivos privados do data_dir.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from app.core.logging import setup_logging
from app.modules.drive_capture.config import load_config
from app.modules.drive_capture.errors import DriveCaptureError
from app.modules.finance_snapshot.atlas_export import EXPORT_FILE, ExportFailed, export_atlas
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
    exp = sub.add_parser(
        "export-atlas", help="exporta o relatório local validado no contrato do Atlas"
    )
    exp.add_argument(
        "--config", type=Path, required=True, help="config isolada da fonte financeira"
    )
    exp.add_argument(
        "--run-id", required=True, help="run esperado do relatório (nenhum outro é aceito)"
    )
    exp.add_argument("--periodo", required=True, help="período esperado do relatório, AAAA-MM")
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
    if args.command == "export-atlas":
        return _export(config, args.run_id, args.periodo)
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


_FILE_STATE = {
    "preservada": "A exportação anterior foi preservada (conferido em disco).",
    "ausente": "Não havia exportação anterior e nenhum arquivo final foi criado.",
    "substituida": (
        f"A troca atômica concluiu antes da falha: {EXPORT_FILE} JÁ é a nova exportação,"
        " validada; a anterior não existe mais."
    ),
    "indeterminado": (
        f"Não foi possível confirmar o estado de {EXPORT_FILE}; não o use sem conferir."
    ),
}
_EXPORT_MESSAGES = {
    "sem_relatorio": (
        "Nenhum relatório financeiro publicado (finance_snapshot/latest.json); rode analyze com"
        " a mesma config, run e período antes de exportar. Nada foi exportado."
    ),
    "exportacao_em_andamento": (
        "Outra exportação financeira em andamento (trava local presente); nada foi feito."
    ),
    "trava_nao_removida": (
        f"{EXPORT_FILE} foi publicado, mas a trava local não pôde ser removida; a próxima"
        " exportação retornará 4 até que ela seja removida manualmente."
    ),
}


def _export(config, run_id: str, period: str) -> int:  # noqa: ANN001
    try:
        export = export_atlas(config, run_id, period)
    except ExportFailed as failed:
        if failed.code in _EXPORT_MESSAGES:
            print(_EXPORT_MESSAGES[failed.code], file=sys.stderr)
        elif failed.file_state is not None:
            print(
                f"EXPORTAÇÃO FALHOU: código {failed.code}. {_FILE_STATE[failed.file_state]}",
                file=sys.stderr,
            )
        else:
            print(
                f"EXPORTAÇÃO FALHOU: código {failed.code}. Nada foi gravado; a exportação"
                " anterior, se houver, foi preservada.",
                file=sys.stderr,
            )
        return failed.exit_code
    except Exception as exc:  # traceback pode carregar conteúdo
        print(f"ERRO: falha controlada ({type(exc).__name__}).", file=sys.stderr)
        return 2
    cov, ck = export["cobertura"], export["checagens"]
    print(
        f"Exportado {EXPORT_FILE} (contrato {export['formato']} {export['versao']}): run"
        f" {export['origem']['run_id']}, período {export['periodo']}, exportado em"
        f" {export['tempos']['exportado_em']}."
    )
    print(f"Dias {cov['abas_total']} · estados {cov['por_estado']}")
    print(f"Conferência {ck['conferencia']} · continuidade {ck['continuidade']}")
    print("Limitações " + ", ".join(export["limitacoes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
