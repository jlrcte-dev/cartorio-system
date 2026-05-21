"""Proteção do ``--output-dir`` do CLI.

Política: caminhos dentro do repositório só são aceitos quando estão sob
``outputs/``, ``tmp/`` ou ``.ai_tmp/`` — todos gitignorados. Qualquer outro
diretório interno (código, documentação, testes, dados locais sensíveis ou
pastas arbitrárias criadas ad-hoc) é bloqueado. Caminhos fora do repositório
permanecem liberados — a responsabilidade fora dos limites do repo é do
usuário.
"""

from __future__ import annotations

from pathlib import Path

from app.modules.notas.inventarios.domain.errors import InventarioInputError

ALLOWED_PREFIXES: frozenset[str] = frozenset({"outputs", "tmp", ".ai_tmp"})


def _find_project_root(start: Path) -> Path | None:
    """Sobe a árvore procurando ``pyproject.toml``.

    Retorna ``None`` se não encontrar — situação atípica, mas tratada para não
    quebrar testes executados em ambientes incomuns.
    """

    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    return None


def validate_output_dir(path: Path, project_root: Path | None = None) -> Path:
    """Resolve ``path`` em absoluto e garante destino permitido.

    Levanta :class:`InventarioInputError` com mensagem orientativa quando o
    destino cai dentro do repositório fora dos prefixos permitidos. Retorna o
    ``Path`` absoluto resolvido em caso de sucesso.
    """

    resolved = path.expanduser().resolve()
    root = project_root or _find_project_root(Path(__file__).resolve().parent)

    if root is None:
        # Sem raiz identificável — não há como aplicar a regra; libera.
        return resolved

    try:
        relative = resolved.relative_to(root)
    except ValueError:
        # Fora do repositório — liberado.
        return resolved

    if not relative.parts:
        raise InventarioInputError(
            f"--output-dir '{path}' aponta para a raiz do projeto. "
            "Use 'outputs/', 'tmp/', '.ai_tmp/' ou caminho fora do repositório."
        )

    first = relative.parts[0]
    if first not in ALLOWED_PREFIXES:
        raise InventarioInputError(
            f"--output-dir '{path}' aponta para '{first}/' dentro do repositório, "
            "diretório não permitido. Use 'outputs/', 'tmp/' ou '.ai_tmp/', ou um "
            "caminho fora do repositório."
        )

    return resolved


__all__ = ["ALLOWED_PREFIXES", "validate_output_dir"]
