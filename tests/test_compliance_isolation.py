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


def test_router_does_not_expose_delete() -> None:
    from app.modules.compliance.router import router

    for route in router.routes:
        methods = getattr(route, "methods", None) or set()
        assert "DELETE" not in methods, (
            f"Rota {getattr(route, 'path', '<?>')} expõe DELETE — proibido nesta sprint"
        )


def test_router_evidence_endpoints_exist() -> None:
    from app.modules.compliance.router import router

    paths_methods: dict[str, set[str]] = {}
    for route in router.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", None) or set()
        paths_methods.setdefault(path, set()).update(methods)

    assert "/compliance/evidences" in paths_methods, "Endpoint /evidences não registrado"
    assert "POST" in paths_methods["/compliance/evidences"], "POST /evidences ausente"
    assert "GET" in paths_methods["/compliance/evidences"], "GET /evidences ausente"
    assert "/compliance/evidences/{evidence_id}" in paths_methods, (
        "Endpoint /evidences/{id} não registrado"
    )
    assert "GET" in paths_methods["/compliance/evidences/{evidence_id}"], (
        "GET /evidences/{id} ausente"
    )
    assert "PATCH" in paths_methods["/compliance/evidences/{evidence_id}"], (
        "PATCH /evidences/{id} ausente"
    )
