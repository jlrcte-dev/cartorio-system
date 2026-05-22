"""Testes de regressão por golden files do CLI de inventários.

Cada exemplo canônico (`inventario_simples.yaml`,
`inventario_sem_meeiro.yaml`) gera três saídas — validação JSON, resumo
Markdown e minuta Markdown — cujo conteúdo congelado vive em
``tests/golden/notas_inventarios/``.

Política:

- comparação é por conteúdo, com normalização ``CRLF`` → ``LF`` para evitar
  falha falsa Windows ↔ Linux;
- os goldens **não** são atualizados automaticamente — mudanças intencionais
  exigem regerar e revisar o diff antes de versionar;
- nenhum golden pode conter PII real; só placeholders e dados fictícios.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = PROJECT_ROOT / "app" / "modules" / "notas" / "inventarios" / "examples"
GOLDEN_DIR = PROJECT_ROOT / "tests" / "golden" / "notas_inventarios"


def _normalize(text: str) -> str:
    return text.replace("\r\n", "\n")


def _run_cli(input_path: Path, output_dir: Path, *, render_minuta: bool) -> None:
    args = [
        sys.executable,
        "-m",
        "app.modules.notas.inventarios.interfaces.cli",
        "--input",
        str(input_path),
        "--output-dir",
        str(output_dir),
    ]
    if render_minuta:
        args.append("--render-minuta")
    proc = subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (
        f"CLI falhou com {proc.returncode}: stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )


def _assert_iguais(gerado: Path, golden: Path) -> None:
    assert gerado.exists(), f"arquivo gerado ausente: {gerado}"
    assert golden.exists(), f"golden ausente: {golden}"
    gerado_text = _normalize(gerado.read_text(encoding="utf-8"))
    golden_text = _normalize(golden.read_text(encoding="utf-8"))
    if gerado_text == golden_text:
        return
    # Apresenta uma diferença mínima para facilitar revisão manual.
    gerado_lines = gerado_text.splitlines()
    golden_lines = golden_text.splitlines()
    for i, (a, b) in enumerate(zip(gerado_lines, golden_lines, strict=False)):
        if a != b:
            raise AssertionError(
                f"divergência na linha {i + 1}\n"
                f"  gerado : {a!r}\n"
                f"  golden : {b!r}\n"
                f"(arquivos: gerado={gerado}, golden={golden})"
            )
    raise AssertionError(
        "conteúdo diverge no comprimento "
        f"(gerado={len(gerado_lines)} linhas, golden={len(golden_lines)} linhas)"
    )


@pytest.mark.parametrize(
    ("exemplo", "prefixo_golden"),
    [
        ("inventario_simples.yaml", "inventario_simples"),
        ("inventario_sem_meeiro.yaml", "inventario_sem_meeiro"),
    ],
)
def test_golden_outputs_dos_exemplos_canonicos(
    exemplo: str, prefixo_golden: str, tmp_path: Path
) -> None:
    """Cada exemplo gera 3 arquivos e cada um precisa bater com o golden."""

    out_dir = tmp_path / "out"
    _run_cli(EXAMPLES_DIR / exemplo, out_dir, render_minuta=True)

    pares = [
        ("inventario_validacao.json", f"{prefixo_golden}_validacao.json"),
        ("inventario_resumo.md", f"{prefixo_golden}_resumo.md"),
        ("inventario_minuta.md", f"{prefixo_golden}_minuta.md"),
    ]
    for nome_gerado, nome_golden in pares:
        _assert_iguais(out_dir / nome_gerado, GOLDEN_DIR / nome_golden)


def test_golden_files_estao_versionados_em_lf() -> None:
    """Goldens vivem em LF — evita ruído de diff entre Windows e Linux."""

    for golden in GOLDEN_DIR.glob("*"):
        if not golden.is_file():
            continue
        raw = golden.read_bytes()
        crlf = raw.count(b"\r\n")
        assert crlf == 0, (
            f"golden {golden.name} contém {crlf} ocorrência(s) de CRLF — "
            "normalize para LF antes de versionar"
        )


def test_golden_files_nao_contem_pii_obvia() -> None:
    """Reforço anti-PII nos goldens, com os mesmos padrões do renderer."""

    import re

    padroes: list[tuple[str, re.Pattern[str]]] = [
        ("CPF", re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")),
        ("CNPJ", re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")),
        ("CEP", re.compile(r"\b\d{5}-\d{3}\b")),
        ("Data dd/mm/aaaa", re.compile(r"\b\d{2}/\d{2}/\d{4}\b")),
        ("E-mail", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
        ("Telefone (DDD) 9xxxx-xxxx", re.compile(r"\(\d{2}\)\s*\d{4,5}-\d{4}")),
    ]
    for golden in GOLDEN_DIR.glob("*"):
        if not golden.is_file():
            continue
        texto = golden.read_text(encoding="utf-8")
        for nome, padrao in padroes:
            match = padrao.search(texto)
            assert match is None, f"PII suspeita ({nome}) em {golden.name}: {match.group()!r}"
