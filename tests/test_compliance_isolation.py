"""Garante a fronteira do módulo compliance.

Compliance NÃO pode importar audit, lgpd ou retention. O router não pode
expor métodos de escrita.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PROHIBITED_MODULES = (
    "app.modules.audit",
    "app.modules.lgpd",
    "app.modules.retention",
)

COMPLIANCE_DIR = Path("app/modules/compliance")
ASSERT_FILES = sorted(COMPLIANCE_DIR.rglob("*.py"))


@pytest.mark.parametrize("path", ASSERT_FILES, ids=lambda p: p.as_posix())
def test_compliance_does_not_import_other_modules(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for forbidden in PROHIBITED_MODULES:
                    assert not alias.name.startswith(forbidden), (
                        f"{path}: import {alias.name} viola fronteira"
                    )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for forbidden in PROHIBITED_MODULES:
                assert not module.startswith(forbidden), f"{path}: from {module} viola fronteira"


def test_router_only_exposes_get_methods() -> None:
    from app.modules.compliance.router import router

    write_methods = {"POST", "PUT", "PATCH", "DELETE"}
    for route in router.routes:
        methods = getattr(route, "methods", None) or set()
        offending = methods & write_methods
        assert not offending, (
            f"Rota {getattr(route, 'path', '<?>')} expõe métodos de escrita: {offending}"
        )
