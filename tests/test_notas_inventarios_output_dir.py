"""Testes da proteção de ``--output-dir`` do CLI.

Política: dentro do repositório só são aceitos ``outputs/``, ``tmp/`` e
``.ai_tmp/``. Qualquer outro diretório interno é bloqueado. Fora do repo:
liberado.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.modules.notas.inventarios.domain.errors import InventarioInputError
from app.modules.notas.inventarios.infrastructure.output_dir import (
    ALLOWED_PREFIXES,
    validate_output_dir,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_INPUT = (
    PROJECT_ROOT
    / "app"
    / "modules"
    / "notas"
    / "inventarios"
    / "examples"
    / "inventario_simples.yaml"
)


def _fake_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "pyproject.toml").touch()
    return root


@pytest.mark.parametrize(
    "prefix",
    [
        "_local_data",
        "app",
        "docs",
        "tests",
        ".git",
        "alembic",
        "scripts",
    ],
)
def test_diretorio_conhecido_bloqueia(prefix: str, tmp_path: Path) -> None:
    """Diretórios conhecidos do projeto devem ser bloqueados pelo whitelist."""

    root = _fake_repo(tmp_path)
    target = root / prefix / "saida_teste"
    target.mkdir(parents=True)

    with pytest.raises(InventarioInputError, match=f"'{prefix}/'"):
        validate_output_dir(target, project_root=root)


@pytest.mark.parametrize(
    "name",
    [
        "relatorios_inventario",
        "inventarios_saida",
        "saida",
        "out",
        "exports",
    ],
)
def test_diretorio_arbitrario_no_repo_bloqueia(name: str, tmp_path: Path) -> None:
    """Pasta ad-hoc dentro do repo (não pertencente ao whitelist) deve falhar."""

    root = _fake_repo(tmp_path)
    target = root / name

    with pytest.raises(InventarioInputError, match=f"'{name}/'"):
        validate_output_dir(target, project_root=root)


@pytest.mark.parametrize("prefix", sorted(ALLOWED_PREFIXES))
def test_prefixos_permitidos_liberam(prefix: str, tmp_path: Path) -> None:
    root = _fake_repo(tmp_path)
    target = root / prefix / "inventarios"

    resolved = validate_output_dir(target, project_root=root)
    assert resolved == target.resolve()


def test_subpasta_de_prefixo_permitido_libera(tmp_path: Path) -> None:
    root = _fake_repo(tmp_path)
    target = root / "outputs" / "inventarios" / "2026" / "subpasta"

    resolved = validate_output_dir(target, project_root=root)
    assert resolved == target.resolve()


def test_fora_do_repositorio_liberado(tmp_path: Path) -> None:
    root = _fake_repo(tmp_path)
    externo = tmp_path / "outro_lugar" / "saida"

    resolved = validate_output_dir(externo, project_root=root)
    assert resolved == externo.resolve()


def test_raiz_do_projeto_bloqueia(tmp_path: Path) -> None:
    root = _fake_repo(tmp_path)

    with pytest.raises(InventarioInputError, match="raiz do projeto"):
        validate_output_dir(root, project_root=root)


def test_cli_bloqueia_app_modules_via_subprocess() -> None:
    """CLI invocada com path dentro de ``app/`` deve falhar com mensagem clara."""

    bloqueado = (
        PROJECT_ROOT / "app" / "modules" / "notas" / "inventarios" / "_saida_teste_bloqueada"
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.modules.notas.inventarios.interfaces.cli",
            "--input",
            str(EXAMPLE_INPUT),
            "--output-dir",
            str(bloqueado),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2, proc.stderr
    assert "app/" in proc.stderr
    assert not bloqueado.exists(), "CLI não deveria ter criado o diretório bloqueado."


def test_cli_bloqueia_pasta_arbitraria_via_subprocess() -> None:
    """CLI deve recusar 'relatorios_inventario' (pasta ad-hoc dentro do repo)."""

    bloqueado = PROJECT_ROOT / "relatorios_inventario"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.modules.notas.inventarios.interfaces.cli",
            "--input",
            str(EXAMPLE_INPUT),
            "--output-dir",
            str(bloqueado),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2, proc.stderr
    assert "relatorios_inventario/" in proc.stderr
    assert not bloqueado.exists(), "CLI não deveria ter criado o diretório bloqueado."
