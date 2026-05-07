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


def test_router_requirement_links_endpoints_exist() -> None:
    from app.modules.compliance.router import router

    paths_methods: dict[str, set[str]] = {}
    for route in router.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", None) or set()
        paths_methods.setdefault(path, set()).update(methods)

    assert "/compliance/requirement-links" in paths_methods, (
        "Endpoint /requirement-links não registrado"
    )
    assert "POST" in paths_methods["/compliance/requirement-links"], (
        "POST /requirement-links ausente"
    )
    assert "GET" in paths_methods["/compliance/requirement-links"], (
        "GET /requirement-links ausente"
    )
    assert "/compliance/requirement-links/{link_id}" in paths_methods, (
        "Endpoint /requirement-links/{id} não registrado"
    )
    assert "GET" in paths_methods["/compliance/requirement-links/{link_id}"], (
        "GET /requirement-links/{id} ausente"
    )
    assert "PATCH" in paths_methods["/compliance/requirement-links/{link_id}"], (
        "PATCH /requirement-links/{id} ausente"
    )
    assert "DELETE" not in paths_methods.get("/compliance/requirement-links/{link_id}", set()), (
        "DELETE /requirement-links/{id} não deve existir"
    )


def test_router_requirement_status_endpoints_exist() -> None:
    from app.modules.compliance.router import router

    paths_methods: dict[str, set[str]] = {}
    for route in router.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", None) or set()
        paths_methods.setdefault(path, set()).update(methods)

    assert "/compliance/requirement-statuses" in paths_methods, (
        "GET /requirement-statuses ausente"
    )
    assert "GET" in paths_methods["/compliance/requirement-statuses"]

    assert "/compliance/requirements/{code}/status" in paths_methods, (
        "GET /requirements/{code}/status ausente"
    )
    assert "GET" in paths_methods["/compliance/requirements/{code}/status"]

    assert "/compliance/requirement-statuses/recompute" in paths_methods, (
        "POST /requirement-statuses/recompute ausente"
    )
    assert "POST" in paths_methods["/compliance/requirement-statuses/recompute"]

    assert "/compliance/requirements/{code}/status/recompute" in paths_methods, (
        "POST /requirements/{code}/status/recompute ausente"
    )
    assert "POST" in paths_methods["/compliance/requirements/{code}/status/recompute"]


def test_router_requirement_status_does_not_expose_delete_or_patch() -> None:
    """Não deve haver DELETE em status nem PATCH humano nesta sprint."""

    from app.modules.compliance.router import router

    status_paths = (
        "/compliance/requirement-statuses",
        "/compliance/requirements/{code}/status",
        "/compliance/requirement-statuses/recompute",
        "/compliance/requirements/{code}/status/recompute",
    )
    for route in router.routes:
        path = getattr(route, "path", "")
        if path in status_paths:
            methods = getattr(route, "methods", None) or set()
            assert "DELETE" not in methods, f"DELETE proibido em {path}"
            assert "PATCH" not in methods, f"PATCH humano proibido em {path}"


def test_compliance_models_no_cross_module_fk() -> None:
    """Garantir que nenhuma FK aponta para audit/retention/lgpd/finance."""

    from app.modules.compliance.models import (
        ComplianceRequirementStatus,
        ComplianceRequirementStatusHistory,
    )

    forbidden_prefixes = (
        "audit_",
        "retention_",
        "lgpd_",
        "finance_",
        "temp_",
    )

    for model in (ComplianceRequirementStatus, ComplianceRequirementStatusHistory):
        for fk in model.__table__.foreign_keys:
            target_table = fk.column.table.name
            for prefix in forbidden_prefixes:
                assert not target_table.startswith(prefix), (
                    f"{model.__name__}: FK cruzada para {target_table} não permitida"
                )
