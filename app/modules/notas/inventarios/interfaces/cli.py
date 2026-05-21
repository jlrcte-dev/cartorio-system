"""CLI do módulo de inventários.

Uso
---
    python -m app.modules.notas.inventarios.interfaces.cli \\
        --input app/modules/notas/inventarios/examples/inventario_simples.yaml \\
        --output-dir outputs/inventarios

Produz dois arquivos em ``--output-dir``:

- ``inventario_validacao.json`` — resultado da validação + resumo dos cálculos.
- ``inventario_resumo.md`` — resumo legível (apenas placeholders, nunca PII).

Códigos de saída:
- 0: validação OK.
- 1: validação falhou — `inventario_validacao.json` contém a lista de erros.
- 2: entrada inválida (arquivo ausente, YAML/JSON malformado, schema inválido).
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.modules.notas.inventarios.application.calculator import (
    DECIMAL_TOLERANCIA,
    InventarioCalculator,
)
from app.modules.notas.inventarios.application.renderer import render_resumo_markdown
from app.modules.notas.inventarios.application.validator import (
    InventarioValidator,
    ValidationResult,
)
from app.modules.notas.inventarios.domain.errors import InventarioInputError
from app.modules.notas.inventarios.domain.models import Inventario, ResumoInventario
from app.modules.notas.inventarios.infrastructure.loaders import load_inventario
from app.modules.notas.inventarios.infrastructure.output_dir import validate_output_dir

EXIT_OK = 0
EXIT_VALIDATION_FAILED = 1
EXIT_INPUT_ERROR = 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.modules.notas.inventarios.interfaces.cli",
        description=(
            "Valida e calcula um inventário extrajudicial a partir de YAML/JSON. "
            "Não recebe e não armazena dados pessoais reais."
        ),
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Caminho do arquivo YAML/JSON com a entrada do inventário.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Diretório onde os arquivos de saída serão gravados.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        output_dir = validate_output_dir(args.output_dir)
    except InventarioInputError as exc:
        print(f"[erro de entrada] {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR

    try:
        inv = load_inventario(args.input)
    except InventarioInputError as exc:
        print(f"[erro de entrada] {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR

    validator = InventarioValidator()
    result = validator.validate(inv)

    calculator = InventarioCalculator()
    resumo = calculator.compute(inv)

    output_dir.mkdir(parents=True, exist_ok=True)

    validacao_path = output_dir / "inventario_validacao.json"
    resumo_md_path = output_dir / "inventario_resumo.md"

    validacao_path.write_text(
        json.dumps(
            _build_validacao_payload(inv, result, resumo),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    resumo_md_path.write_text(render_resumo_markdown(inv, resumo), encoding="utf-8")

    if not result.ok:
        print(
            f"[validacao FALHOU] {len(result.errors)} erro(s). Detalhes em {validacao_path}",
            file=sys.stderr,
        )
        return EXIT_VALIDATION_FAILED

    if resumo.divergencia_centavos > Decimal("0"):
        print(
            f"[atencao] divergencia de centavos: {_decimal_str(resumo.divergencia_centavos)} "
            f"(dentro da tolerancia de {_decimal_str(DECIMAL_TOLERANCIA)} por linha, "
            "mas sem ajuste automatico — ver inventario_validacao.json)",
            file=sys.stderr,
        )

    print(f"[validacao OK] arquivos gerados em {output_dir}")
    return EXIT_OK


def _build_validacao_payload(
    inv: Inventario,
    result: ValidationResult,
    resumo: ResumoInventario,
) -> dict[str, Any]:
    alerta_centavos = None
    if resumo.divergencia_centavos > Decimal("0"):
        alerta_centavos = {
            "divergencia": _decimal_str(resumo.divergencia_centavos),
            "mensagem": (
                "soma distribuida difere do patrimonio total dentro da tolerancia "
                "de arredondamento. Sprint atual NAO ajusta centavos automaticamente; "
                "decisao (alerta, ajuste controlado ou distribuicao manual por valor) "
                "fica para sprint futura."
            ),
        }

    return {
        "tipo_ato": inv.tipo_ato,
        "validacao": {
            "ok": result.ok,
            "erros": list(result.errors),
        },
        "alerta_centavos": alerta_centavos,
        "resumo": {
            "patrimonio_total": _decimal_str(resumo.patrimonio_total),
            "valor_meacao": _decimal_str(resumo.valor_meacao),
            "monte_partilhavel": _decimal_str(resumo.monte_partilhavel),
            "divergencia_centavos": _decimal_str(resumo.divergencia_centavos),
            "quinhao_por_herdeiro": {
                k: _decimal_str(v) for k, v in resumo.quinhao_por_herdeiro.items()
            },
            "total_por_beneficiario": {
                k: _decimal_str(v) for k, v in resumo.total_por_beneficiario.items()
            },
            "bens": [
                {
                    "id": r.bem_id,
                    "tipo": r.tipo.value,
                    "valor": _decimal_str(r.valor),
                    "quinhoes": [
                        {
                            "beneficiario": q.beneficiario,
                            "percentual": _decimal_str(q.percentual),
                            "valor": _decimal_str(q.valor),
                        }
                        for q in r.quinhoes
                    ],
                }
                for r in resumo.bens
            ],
        },
    }


def _decimal_str(value: Decimal) -> str:
    return f"{value:.2f}"


if __name__ == "__main__":
    raise SystemExit(main())
