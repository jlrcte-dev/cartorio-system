"""Tests for DocumentDiagnosis — Sprint 3.

All tests use tmp_path fixtures and synthetic inventory JSON.
No real server paths are touched. No database is accessed.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.modules.audit.diagnosis.analyzer import DocumentAnalyzer, InventoryLoadError
from app.modules.audit.diagnosis.models import DiagnosisResult
from app.modules.audit.diagnosis.report import write_all

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MB = 1024 * 1024


def _file_entry(
    name: str,
    path_relative: str | None = None,
    parent_path: str = ".",
    size_bytes: int = 1024,
    extension: str | None = None,
    modified_at: str = "2024-01-01T00:00:00+00:00",
) -> dict:
    if extension is None:
        extension = ("." + name.rsplit(".", 1)[1].lower()) if "." in name else ""
    if path_relative is None:
        path_relative = name
    return {
        "name": name,
        "extension": extension,
        "path_relative": path_relative,
        "parent_path": parent_path,
        "entry_type": "file",
        "depth": 1,
        "size_bytes": size_bytes,
        "modified_at": modified_at,
        "created_at": modified_at,
        "error": None,
    }


def _write_inventory(
    tmp: Path,
    files: list[dict],
    run_id: str = "test-run-abc123",
    run_name: str = "test-run",
) -> Path:
    tmp.mkdir(parents=True, exist_ok=True)
    data = {
        "metadata": {
            "run_id": run_id,
            "run_name": run_name,
            "root_path": "[root]",
            "started_at": "2026-05-04T10:00:00+00:00",
            "finished_at": "2026-05-04T10:01:00+00:00",
            "duration_seconds": 60.0,
            "total_files": len(files),
            "total_directories": 0,
            "total_size_bytes": sum(f.get("size_bytes", 0) for f in files),
            "errors_count": 0,
            "excluded_count": 0,
        },
        "parameters": {
            "max_depth": None,
            "follow_symlinks": False,
            "include_hidden": True,
            "fail_fast": False,
            "exclude_patterns": [],
        },
        "files": files,
        "directories": [],
        "errors": [],
    }
    path = tmp / "file_inventory.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _old_date(years: int = 7) -> str:
    dt = datetime.now(UTC) - timedelta(days=years * 365)
    return dt.isoformat()


# ---------------------------------------------------------------------------
# 1. Carrega inventory válido
# ---------------------------------------------------------------------------


def test_load_valid_inventory(tmp_path):
    inv = _write_inventory(tmp_path / "inv", [_file_entry("relatorio.pdf")])
    result = DocumentAnalyzer(inventory_path=inv).run()
    assert isinstance(result, DiagnosisResult)
    assert result.total_files_analyzed == 1


# ---------------------------------------------------------------------------
# 2. Rejeita inventory inválido
# ---------------------------------------------------------------------------


def test_rejects_missing_inventory(tmp_path):
    with pytest.raises(InventoryLoadError, match="not found"):
        DocumentAnalyzer(inventory_path=tmp_path / "nope.json").run()


def test_rejects_invalid_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    with pytest.raises(InventoryLoadError, match="Invalid JSON"):
        DocumentAnalyzer(inventory_path=bad).run()


def test_rejects_inventory_without_files_key(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"metadata": {}}), encoding="utf-8")
    with pytest.raises(InventoryLoadError, match="'files'"):
        DocumentAnalyzer(inventory_path=bad).run()


# ---------------------------------------------------------------------------
# 3. scanner_run_id vem do inventory
# ---------------------------------------------------------------------------


def test_scanner_run_id_from_inventory(tmp_path):
    inv = _write_inventory(tmp_path / "inv", [], run_id="inv-run-id-999")
    result = DocumentAnalyzer(inventory_path=inv).run()
    assert result.scanner_run_id == "inv-run-id-999"


# ---------------------------------------------------------------------------
# 4. scanner_run_id vem do manifest quando fornecido
# ---------------------------------------------------------------------------


def test_scanner_run_id_from_manifest(tmp_path):
    inv = _write_inventory(tmp_path / "inv", [], run_id="inv-run-id")
    manifest_data = {"run": {"run_id": "manifest-run-id-777"}, "read_only": True}
    manifest_path = tmp_path / "inv" / "scan_manifest.json"
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")

    result = DocumentAnalyzer(inventory_path=inv, manifest_path=manifest_path).run()
    assert result.scanner_run_id == "manifest-run-id-777"


# ---------------------------------------------------------------------------
# 5. Detecta possível credencial por nome (DIAG-001)
# ---------------------------------------------------------------------------


def test_rule_credential_by_name(tmp_path):
    files = [
        _file_entry("senha_sistema.txt", path_relative="Dados/senha_sistema.txt"),
        _file_entry("relatorio_anual.pdf"),
    ]
    inv = _write_inventory(tmp_path / "inv", files)
    result = DocumentAnalyzer(inventory_path=inv).run()

    creds = [c for c in result.candidates if c.rule_id == "DIAG-001"]
    assert len(creds) == 1
    assert "senha" in creds[0].notes.lower()
    assert creds[0].related_file_path == "Dados/senha_sistema.txt"


def test_rule_credential_detects_various_keywords(tmp_path):
    files = [
        _file_entry("login_dados.xlsx"),
        _file_entry("token_acesso.txt"),
        _file_entry("normal_doc.pdf"),
    ]
    inv = _write_inventory(tmp_path / "inv", files)
    result = DocumentAnalyzer(inventory_path=inv).run()
    rule_ids = {c.rule_id for c in result.candidates}
    assert "DIAG-001" in rule_ids


# ---------------------------------------------------------------------------
# 6. Detecta executável / script por extensão (DIAG-002)
# ---------------------------------------------------------------------------


def test_rule_executable_by_extension(tmp_path):
    files = [
        _file_entry("instalar.exe", extension=".exe"),
        _file_entry("setup.msi", extension=".msi"),
        _file_entry("doc.pdf"),
    ]
    inv = _write_inventory(tmp_path / "inv", files)
    result = DocumentAnalyzer(inventory_path=inv).run()

    execs = [c for c in result.candidates if c.rule_id == "DIAG-002"]
    assert len(execs) == 2
    assert all(c.related_extension in (".exe", ".msi") for c in execs)


def test_rule_executable_detects_script_extensions(tmp_path):
    files = [_file_entry(f"script{ext}", extension=ext) for ext in [".bat", ".ps1", ".vbs"]]
    inv = _write_inventory(tmp_path / "inv", files)
    result = DocumentAnalyzer(inventory_path=inv).run()
    execs = [c for c in result.candidates if c.rule_id == "DIAG-002"]
    assert len(execs) == 3


# ---------------------------------------------------------------------------
# 7. Detecta arquivo em pasta Temp (DIAG-003)
# ---------------------------------------------------------------------------


def test_rule_temp_folder(tmp_path):
    files = [
        _file_entry("boleto.pdf", path_relative="Dados/Temp/boleto.pdf", parent_path="Dados/Temp"),
        _file_entry("normal.docx", path_relative="Docs/normal.docx", parent_path="Docs"),
    ]
    inv = _write_inventory(tmp_path / "inv", files)
    result = DocumentAnalyzer(inventory_path=inv).run()

    temp_cands = [c for c in result.candidates if c.rule_id == "DIAG-003"]
    assert len(temp_cands) == 1
    assert "Temp" in temp_cands[0].related_parent_path


def test_rule_temp_folder_portuguese_variant(tmp_path):
    files = [
        _file_entry(
            "contrato.pdf",
            path_relative="Servidor/Temporários/contrato.pdf",
            parent_path="Servidor/Temporários",
        )
    ]
    inv = _write_inventory(tmp_path / "inv", files)
    result = DocumentAnalyzer(inventory_path=inv).run()
    temp_cands = [c for c in result.candidates if c.rule_id == "DIAG-003"]
    assert len(temp_cands) == 1


# ---------------------------------------------------------------------------
# 8. Detecta arquivo grande (DIAG-004)
# ---------------------------------------------------------------------------


def test_rule_large_pdf(tmp_path):
    files = [
        _file_entry("enorme.pdf", size_bytes=15 * _MB, extension=".pdf"),
        _file_entry("pequeno.pdf", size_bytes=500 * 1024, extension=".pdf"),
    ]
    inv = _write_inventory(tmp_path / "inv", files)
    # large_pdf_mb=10 — enorme.pdf should trigger
    result = DocumentAnalyzer(inventory_path=inv, large_pdf_mb=10).run()
    pdf_cands = [c for c in result.candidates if c.rule_id == "DIAG-004a"]
    assert len(pdf_cands) == 1
    assert "15" in pdf_cands[0].evidence_summary or "enorme" in pdf_cands[0].notes


def test_rule_large_other_file_filtered_by_default(tmp_path):
    """large_other (DIAG-004c) has BACKLOG priority and is excluded by default."""
    files = [_file_entry("backup.zip", size_bytes=100 * _MB, extension=".zip")]
    inv = _write_inventory(tmp_path / "inv", files)
    result = DocumentAnalyzer(inventory_path=inv, large_file_mb=50).run()
    other_cands = [c for c in result.candidates if c.rule_id == "DIAG-004c"]
    assert len(other_cands) == 0  # filtered out when include_low_priority=False


def test_rule_large_other_file_included_with_flag(tmp_path):
    files = [_file_entry("backup.zip", size_bytes=100 * _MB, extension=".zip")]
    inv = _write_inventory(tmp_path / "inv", files)
    result = DocumentAnalyzer(inventory_path=inv, large_file_mb=50, include_low_priority=True).run()
    other_cands = [c for c in result.candidates if c.rule_id == "DIAG-004c"]
    assert len(other_cands) == 1


# ---------------------------------------------------------------------------
# 9. Detecta nome genérico (DIAG-005)
# ---------------------------------------------------------------------------


def test_rule_generic_name(tmp_path):
    files = [
        _file_entry("documento.pdf"),
        _file_entry("scan.pdf"),
        _file_entry("relatorio_anual_2025.pdf"),
    ]
    inv = _write_inventory(tmp_path / "inv", files)
    result = DocumentAnalyzer(inventory_path=inv, include_low_priority=True).run()
    generic = [c for c in result.candidates if c.rule_id == "DIAG-005"]
    assert len(generic) == 1
    assert "2" in generic[0].evidence_summary  # 2 generic files


def test_rule_generic_name_hyphen_prefix(tmp_path):
    files = [_file_entry("-backup_temp.docx")]
    inv = _write_inventory(tmp_path / "inv", files)
    result = DocumentAnalyzer(inventory_path=inv, include_low_priority=True).run()
    generic = [c for c in result.candidates if c.rule_id == "DIAG-005"]
    assert len(generic) == 1


# ---------------------------------------------------------------------------
# 10. Acervo financeiro gera candidato AGREGADO (DIAG-006)
# ---------------------------------------------------------------------------


def test_rule_financial_archive_aggregates(tmp_path):
    """20 files in the same financial folder must produce exactly ONE candidate."""
    files = [
        _file_entry(
            f"boleto_{i:03d}.pdf",
            path_relative=f"Gerenciamento_financeiro/2024/boleto_{i:03d}.pdf",
            parent_path="Gerenciamento_financeiro/2024",
            size_bytes=50 * 1024,
        )
        for i in range(20)
    ]
    inv = _write_inventory(tmp_path / "inv", files)
    result = DocumentAnalyzer(inventory_path=inv).run()

    fin = [c for c in result.candidates if c.rule_id == "DIAG-006"]
    assert len(fin) == 1, "Must aggregate — not one candidate per file"
    assert "20" in fin[0].evidence_summary or "20" in fin[0].notes


def test_rule_financial_archive_separate_roots(tmp_path):
    """Two distinct financial roots must produce two separate candidates."""
    files = [
        _file_entry("a.pdf", path_relative="financeiro/a.pdf", parent_path="financeiro"),
        _file_entry("b.pdf", path_relative="emolumentos/b.pdf", parent_path="emolumentos"),
    ]
    inv = _write_inventory(tmp_path / "inv", files)
    result = DocumentAnalyzer(inventory_path=inv).run()
    fin = [c for c in result.candidates if c.rule_id == "DIAG-006"]
    assert len(fin) == 2


# ---------------------------------------------------------------------------
# 11. Detecta documento antigo em pasta de política/POP/LGPD (DIAG-007)
# ---------------------------------------------------------------------------


def test_rule_old_policy_docs(tmp_path):
    files = [
        _file_entry(
            "politica_seguranca.docx",
            path_relative="LGPD/politica_seguranca.docx",
            parent_path="LGPD",
            modified_at=_old_date(years=7),
        ),
        _file_entry(
            "relatorio_recente.pdf",
            path_relative="LGPD/relatorio_recente.pdf",
            parent_path="LGPD",
            modified_at="2025-01-01T00:00:00+00:00",
        ),
    ]
    inv = _write_inventory(tmp_path / "inv", files)
    result = DocumentAnalyzer(inventory_path=inv, old_file_years=5).run()

    old = [c for c in result.candidates if c.rule_id == "DIAG-007"]
    assert len(old) == 1
    assert "1" in old[0].evidence_summary  # 1 old file


def test_rule_old_policy_docs_pop_path(tmp_path):
    files = [
        _file_entry(
            "pop_atendimento.docx",
            path_relative="Procedimentos Operacionais Padrão/pop_atendimento.docx",
            parent_path="Procedimentos Operacionais Padrão",
            modified_at=_old_date(years=6),
        )
    ]
    inv = _write_inventory(tmp_path / "inv", files)
    result = DocumentAnalyzer(inventory_path=inv, old_file_years=5).run()
    old = [c for c in result.candidates if c.rule_id == "DIAG-007"]
    assert len(old) == 1


# ---------------------------------------------------------------------------
# 12. Não acessa arquivos originais
# ---------------------------------------------------------------------------


def test_no_original_file_access(tmp_path):
    """Analyzer runs correctly even when inventory paths don't exist locally."""
    files = [
        _file_entry(
            "arquivo_inexistente.pdf",
            path_relative="C:/Servidor/Acervo/arquivo_inexistente.pdf",
        ),
        _file_entry(
            "outro_inexistente.docx",
            path_relative="\\\\servidor\\share\\outro_inexistente.docx",
        ),
    ]
    inv = _write_inventory(tmp_path / "inv", files)
    # Must complete without FileNotFoundError — confirms no file access
    result = DocumentAnalyzer(inventory_path=inv).run()
    assert isinstance(result, DiagnosisResult)
    assert result.total_files_analyzed == 2


# ---------------------------------------------------------------------------
# 13. Gera os 4 artefatos
# ---------------------------------------------------------------------------


def test_write_all_generates_four_files(tmp_path):
    inv = _write_inventory(
        tmp_path / "inv",
        [_file_entry("doc.pdf"), _file_entry("senha.txt")],
    )
    result = DocumentAnalyzer(inventory_path=inv).run()
    artefacts = write_all(result, tmp_path / "out")

    assert (tmp_path / "out" / "document_diagnosis.json").exists()
    assert (tmp_path / "out" / "document_diagnosis.csv").exists()
    assert (tmp_path / "out" / "document_diagnosis.md").exists()
    assert (tmp_path / "out" / "diagnosis_manifest.json").exists()
    assert len(artefacts) == 4


# ---------------------------------------------------------------------------
# 14. Manifest contém read_only=true, content_read=false, original_files_accessed=false
# ---------------------------------------------------------------------------


def test_manifest_safety_flags(tmp_path):
    inv = _write_inventory(tmp_path / "inv", [_file_entry("teste.pdf")])
    result = DocumentAnalyzer(inventory_path=inv).run()
    write_all(result, tmp_path / "out")

    manifest = json.loads((tmp_path / "out" / "diagnosis_manifest.json").read_text("utf-8"))
    assert manifest["read_only"] is True
    assert manifest["content_read"] is False
    assert manifest["original_files_accessed"] is False


def test_manifest_has_sha256_for_outputs(tmp_path):
    inv = _write_inventory(tmp_path / "inv", [_file_entry("teste.pdf")])
    result = DocumentAnalyzer(inventory_path=inv).run()
    write_all(result, tmp_path / "out")

    manifest = json.loads((tmp_path / "out" / "diagnosis_manifest.json").read_text("utf-8"))
    for label, info in manifest["output_files"].items():
        assert info["sha256"], f"Missing sha256 for {label}"
        assert len(info["sha256"]) == 64


# ---------------------------------------------------------------------------
# 15. CSV usa UTF-8 BOM
# ---------------------------------------------------------------------------


def test_csv_utf8_bom(tmp_path):
    inv = _write_inventory(tmp_path / "inv", [_file_entry("senha.txt")])
    result = DocumentAnalyzer(inventory_path=inv).run()
    write_all(result, tmp_path / "out")

    raw = (tmp_path / "out" / "document_diagnosis.csv").read_bytes()
    assert raw[:3] == b"\xef\xbb\xbf", "CSV must start with UTF-8 BOM"


def test_csv_has_expected_headers(tmp_path):
    inv = _write_inventory(tmp_path / "inv", [_file_entry("teste.pdf")])
    result = DocumentAnalyzer(inventory_path=inv).run()
    write_all(result, tmp_path / "out")

    with open(tmp_path / "out" / "document_diagnosis.csv", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        headers = next(reader)
    assert "candidate_id" in headers
    assert "rule_id" in headers
    assert "severity" in headers


# ---------------------------------------------------------------------------
# 16. Markdown contém aviso de análise por metadados
# ---------------------------------------------------------------------------


def test_markdown_contains_metadata_notice(tmp_path):
    inv = _write_inventory(tmp_path / "inv", [_file_entry("doc.pdf")])
    result = DocumentAnalyzer(inventory_path=inv).run()
    write_all(result, tmp_path / "out")

    md = (tmp_path / "out" / "document_diagnosis.md").read_text("utf-8")
    assert "metadados" in md.lower()
    assert "nenhum arquivo original foi aberto" in md.lower()


# ---------------------------------------------------------------------------
# 17. Não cria AuditFinding no banco
# ---------------------------------------------------------------------------


def test_no_audit_finding_created(tmp_path):
    """DocumentAnalyzer returns DiagnosisResult, never AuditFinding or DB objects."""
    files = [
        _file_entry("senha.txt"),
        _file_entry("instalar.exe", extension=".exe"),
        _file_entry("doc.pdf", path_relative="Gerenciamento_financeiro/doc.pdf"),
    ]
    inv = _write_inventory(tmp_path / "inv", files)
    result = DocumentAnalyzer(inventory_path=inv).run()

    # Result is purely a data model, not a DB model
    assert isinstance(result, DiagnosisResult)
    assert not hasattr(result, "__tablename__")
    assert not hasattr(result, "_sa_class_manager")

    # All candidates have status=CANDIDATE — not an AuditStatus value
    for candidate in result.candidates:
        assert candidate.status == "CANDIDATE"
        assert candidate.origin == "SCANNER"

    # The diagnosis module has no DB imports — verified structurally
    import app.modules.audit.diagnosis.analyzer as ana_mod
    import app.modules.audit.diagnosis.rules as rules_mod

    for mod in (ana_mod, rules_mod):
        assert not hasattr(mod, "get_db")
        assert not hasattr(mod, "Session")
        assert not hasattr(mod, "AsyncSession")
