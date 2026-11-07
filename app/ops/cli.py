"""Ponto de entrada único do verificador operacional.

Uso (raiz da release)::

    python -m app.ops.cli check [--output ARQUIVO] [--compact]
    python -m app.ops.cli alert --report ARQUIVO --spool DIRETORIO
    python -m app.ops.cli render-units --templates DIR --params ARQUIVO --out DIR

``check`` é somente leitura e lê a configuração só do ambiente (``CARTORIO_OPS_*`` e
``DATABASE_URL``). O JSON vai para stdout — e, com ``--output``, também para um arquivo
publicado atomicamente. Códigos de saída: 0 todas as checagens obrigatórias
comprovadas · 1 falha detectada · 2 diagnóstico inconclusivo (inclui uso inválido e
erro interno do próprio verificador). Falha vence inconclusivo.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from datetime import timedelta
from pathlib import Path

from app.ops.alert import build_alert, failure_problem, load_report, monitor_facts, write_alert
from app.ops.config import load_config
from app.ops.report import (
    EXIT_CODES,
    Clock,
    Status,
    internal_error_report,
    utc_now,
    write_json_atomic,
)
from app.ops.systemd import ShowRunner, run_systemctl_show
from app.ops.units import UnitParamsError, load_params, render_units
from app.ops.verifier import run_checks

EXIT_INCONCLUSIVE = EXIT_CODES[Status.INCONCLUSIVE]
_INVOCATION_ID = re.compile(r"^[0-9a-f]{32}$")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.ops.cli",
        description="Verificador operacional somente leitura do Cartório System.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="executa as checagens e emite o JSON versionado")
    check.add_argument("--output", type=Path, help="também publica o JSON neste arquivo")
    check.add_argument("--compact", action="store_true", help="JSON numa linha só")

    alert = sub.add_parser("alert", help="emite alerta a partir do último relatório")
    alert.add_argument("--report", type=Path, required=True, help="JSON gerado por check")
    alert.add_argument("--spool", type=Path, required=True, help="destino local dos alertas")
    alert.add_argument(
        "--max-report-age-minutes",
        type=float,
        default=15.0,
        help="relatório mais velho que isto é tratado como ausente (padrão 15)",
    )
    alert.add_argument(
        "--expect-failure",
        action="store_true",
        help="acionado por OnFailure=: nunca responde 'sem alerta'",
    )

    render = sub.add_parser("render-units", help="gera .service/.timer a partir dos modelos")
    render.add_argument("--templates", type=Path, required=True, help="ex.: deploy/ops")
    render.add_argument("--params", type=Path, required=True, help="ex.: deploy/ops/lab.params")
    render.add_argument("--out", type=Path, required=True, help="diretório de saída")
    return parser


def _check(
    args: argparse.Namespace, environ: Mapping[str, str], clock: Clock, runner: ShowRunner
) -> int:
    raw = environ.get("INVOCATION_ID", "")
    invocation = raw if _INVOCATION_ID.match(raw) else None
    try:
        report = run_checks(
            load_config(environ), clock=clock, runner=runner, invocation_id=invocation
        )
    except Exception as exc:  # o verificador nunca termina sem dizer por quê
        report = internal_error_report(clock(), exc, invocation)
    print(json.dumps(report, ensure_ascii=False, indent=None if args.compact else 2))
    code = int(report["exit_code"])
    if args.output is not None:
        try:
            write_json_atomic(args.output, report)
        except OSError as exc:
            print(f"ERRO: relatório não publicado ({type(exc).__name__}).", file=sys.stderr)
            # Sem relatório persistido o alerta não tem evidência: nunca sair como saudável.
            if code == 0:
                code = EXIT_INCONCLUSIVE
    return code


def _alert(args: argparse.Namespace, environ: Mapping[str, str], clock: Clock) -> int:
    now = clock()
    max_age = timedelta(minutes=args.max_report_age_minutes)
    report, problem = load_report(args.report, now, max_age)
    monitor = monitor_facts(environ) if args.expect_failure else {}
    if problem is None and report is not None:
        if args.expect_failure:
            # Acionado por falha: o relatório em disco precisa descrever ESSA falha.
            problem = failure_problem(report, monitor)
        elif report.get("overall") == Status.OK.value:
            print("sem alerta: o último relatório está saudável")
            return 0
    alert = build_alert(report, problem, now, monitor=monitor)
    try:
        target = write_alert(args.spool, alert, now)
    except OSError as exc:
        print(f"ERRO: alerta não gravado ({type(exc).__name__}).", file=sys.stderr)
        return EXIT_INCONCLUSIVE
    summary = {"alert_file": target.name, "level": alert["level"], "summary": alert["summary"]}
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def _render(args: argparse.Namespace) -> int:
    try:
        params = load_params(args.params.read_text(encoding="utf-8"))
        rendered = render_units(args.templates, params)
    except UnitParamsError as exc:
        for problem in exc.problems:
            print(f"ERRO: {problem}", file=sys.stderr)
        return EXIT_INCONCLUSIVE
    except OSError as exc:
        print(f"ERRO: modelos ou parâmetros ilegíveis ({type(exc).__name__}).", file=sys.stderr)
        return EXIT_INCONCLUSIVE
    args.out.mkdir(parents=True, exist_ok=True)
    for name, text in rendered.items():
        (args.out / name).write_text(text, encoding="utf-8", newline="\n")
        print(name)
    return 0


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    clock: Clock = utc_now,
    runner: ShowRunner = run_systemctl_show,
) -> int:
    args = _parser().parse_args(argv)
    env = os.environ if environ is None else environ
    if args.command == "check":
        return _check(args, env, clock, runner)
    if args.command == "alert":
        return _alert(args, env, clock)
    return _render(args)


if __name__ == "__main__":
    raise SystemExit(main())
