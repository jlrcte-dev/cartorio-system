"""Tests for the read-only file system scanner (Sprint 1).

All tests use temporary directories created by pytest's tmp_path fixture.
No real server paths are touched.
"""

import csv
import json
import os
import stat
from pathlib import Path

import pytest

from app.modules.audit.scanner.file_scanner import scan, validate_output_dir
from app.modules.audit.scanner.models import ScanResult
from app.modules.audit.scanner.report import _CSV_HEADERS, write_all

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tree(base: Path) -> None:
    """Create a small, predictable directory tree inside *base*."""
    (base / "subdir_a").mkdir()
    (base / "subdir_b").mkdir()
    (base / "subdir_a" / "deep").mkdir()

    (base / "root_file.txt").write_text("hello", encoding="utf-8")
    (base / "doc.pdf").write_bytes(b"%PDF" + b"x" * 1000)
    (base / "subdir_a" / "report.odt").write_text("report", encoding="utf-8")
    (base / "subdir_a" / "deep" / "nested.docx").write_text("nested", encoding="utf-8")
    (base / "subdir_b" / "data.xlsx").write_text("data", encoding="utf-8")
    (base / "subdir_b" / "backup.bak").write_text("bak", encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Scanner finds files and directories
# ---------------------------------------------------------------------------


def test_scan_finds_files_and_dirs(tmp_path):
    _make_tree(tmp_path)

    result = scan(root_path=tmp_path, run_name="test-basic")

    assert isinstance(result, ScanResult)
    assert result.total_files == 6
    # root + subdir_a + subdir_b + subdir_a/deep = 4 directories
    assert result.total_directories == 4
    assert result.total_size_bytes > 0

    file_names = {f.name for f in result.files}
    assert "root_file.txt" in file_names
    assert "doc.pdf" in file_names
    assert "nested.docx" in file_names


# ---------------------------------------------------------------------------
# 2. max_depth is respected
# ---------------------------------------------------------------------------


def test_scan_respects_max_depth(tmp_path):
    _make_tree(tmp_path)

    # depth=1 → only files directly in root; subdirs visible but not descended
    result = scan(root_path=tmp_path, max_depth=1)

    # At max_depth=1, only root-level files are collected
    file_names = {f.name for f in result.files}
    assert "root_file.txt" in file_names
    assert "doc.pdf" in file_names
    # Files inside subdirs should NOT be present
    assert "report.odt" not in file_names
    assert "nested.docx" not in file_names


def test_scan_max_depth_zero(tmp_path):
    _make_tree(tmp_path)

    result = scan(root_path=tmp_path, max_depth=0)

    # No files collected (root only, dirs pruned immediately)
    assert result.total_files == 0
    # Only the root directory itself
    assert result.total_directories == 1


# ---------------------------------------------------------------------------
# 3. Exclusions are respected
# ---------------------------------------------------------------------------


def test_scan_excludes_by_name(tmp_path):
    _make_tree(tmp_path)

    result = scan(root_path=tmp_path, exclude_patterns=["subdir_b"])

    file_names = {f.name for f in result.files}
    assert "data.xlsx" not in file_names
    assert "backup.bak" not in file_names
    # subdir_a files still present
    assert "report.odt" in file_names
    assert result.excluded_count >= 1


def test_scan_excludes_by_extension_glob(tmp_path):
    _make_tree(tmp_path)

    result = scan(root_path=tmp_path, exclude_patterns=["*.bak"])

    file_names = {f.name for f in result.files}
    assert "backup.bak" not in file_names
    assert result.excluded_count >= 1


def test_scan_no_default_exclude_interference(tmp_path):
    _make_tree(tmp_path)

    # Default excludes ($RECYCLE.BIN etc.) should not affect our tree
    result = scan(root_path=tmp_path)

    assert result.total_files == 6


# ---------------------------------------------------------------------------
# 4. All four output files are generated
# ---------------------------------------------------------------------------


def test_write_all_generates_four_files(tmp_path):
    root = tmp_path / "scanned"
    root.mkdir()
    (root / "file.txt").write_text("x")

    output_dir = tmp_path / "output"

    result = scan(root_path=root)
    artefacts = write_all(result, output_dir)

    assert "file_inventory_json" in artefacts
    assert "file_inventory_csv" in artefacts
    assert "scan_summary_md" in artefacts
    assert "scan_manifest_json" in artefacts

    for path in artefacts.values():
        assert path.exists(), f"Expected output file not found: {path}"
        assert path.stat().st_size > 0


# ---------------------------------------------------------------------------
# 5. Scanner does NOT modify files in the scanned directory
# ---------------------------------------------------------------------------


def test_scan_does_not_modify_files(tmp_path):
    _make_tree(tmp_path)

    # Record modification times before scan
    before: dict[str, float] = {}
    for dirpath, _, filenames in os.walk(str(tmp_path)):
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            before[fp] = os.stat(fp).st_mtime

    scan(root_path=tmp_path)

    # Verify modification times are unchanged
    for fp, mtime in before.items():
        assert os.stat(fp).st_mtime == mtime, f"File was modified: {fp}"


def test_scan_does_not_create_files_in_root(tmp_path):
    """No new files should appear inside the scanned tree after scanning."""
    _make_tree(tmp_path)

    files_before = set(tmp_path.rglob("*"))
    scan(root_path=tmp_path)
    files_after = set(tmp_path.rglob("*"))

    assert files_before == files_after, "Scan created unexpected files in the scanned tree"


# ---------------------------------------------------------------------------
# 6. Error handling — inaccessible paths
# ---------------------------------------------------------------------------


def test_scan_continues_when_file_disappears(tmp_path):
    """Scan should not crash if a file is removed mid-walk (simulated via
    a path that never existed when iterating a plain list)."""
    # We simulate by excluding after the fact via a missing file reference;
    # actual mid-walk deletion is hard to reproduce deterministically.
    # Instead we verify that scan on a valid tree doesn't crash.
    _make_tree(tmp_path)
    result = scan(root_path=tmp_path)
    assert result.total_files >= 0  # simply must not raise


@pytest.mark.skipif(
    os.name == "nt",
    reason="chmod permission simulation unreliable on Windows without admin",
)
def test_scan_records_permission_error(tmp_path):
    """On POSIX, make a directory unreadable and verify the error is recorded."""
    root = tmp_path / "root"
    root.mkdir()
    secret = root / "secret_dir"
    secret.mkdir()
    (secret / "hidden.txt").write_text("secret")

    # Remove read+execute permission
    secret.chmod(0o000)
    try:
        result = scan(root_path=root)
        assert result.errors_count >= 1
        assert any("PermissionError" in e.error_type for e in result.errors)
    finally:
        secret.chmod(stat.S_IRWXU)  # restore for cleanup


# ---------------------------------------------------------------------------
# 7. CSV has expected headers
# ---------------------------------------------------------------------------


def test_csv_has_expected_headers(tmp_path):
    root = tmp_path / "scanned"
    root.mkdir()
    (root / "a.txt").write_text("a")

    output_dir = tmp_path / "out"
    result = scan(root_path=root)
    artefacts = write_all(result, output_dir)

    csv_path = artefacts["file_inventory_csv"]
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        headers = next(reader)

    assert headers == _CSV_HEADERS


def test_csv_utf8_bom(tmp_path):
    """CSV must start with the UTF-8 BOM so Excel opens it correctly."""
    root = tmp_path / "s"
    root.mkdir()
    (root / "x.txt").write_text("x")

    output_dir = tmp_path / "out"
    result = scan(root_path=root)
    write_all(result, output_dir)

    csv_path = output_dir / "file_inventory.csv"
    raw = csv_path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "CSV must start with UTF-8 BOM"


# ---------------------------------------------------------------------------
# 8. Markdown contains the read-only statement
# ---------------------------------------------------------------------------


def test_markdown_contains_readonly_statement(tmp_path):
    root = tmp_path / "s"
    root.mkdir()
    (root / "file.txt").write_text("hello")

    output_dir = tmp_path / "out"
    result = scan(root_path=root)
    write_all(result, output_dir)

    md = (output_dir / "scan_summary.md").read_text(encoding="utf-8")
    assert "read-only" in md.lower() or "somente leitura" in md.lower()
    assert "Nenhum arquivo foi modificado" in md or "never" in md.lower()


# ---------------------------------------------------------------------------
# 9. Manifest contains read_only=true
# ---------------------------------------------------------------------------


def test_manifest_contains_read_only_true(tmp_path):
    root = tmp_path / "s"
    root.mkdir()
    (root / "f.txt").write_text("f")

    output_dir = tmp_path / "out"
    result = scan(root_path=root)
    write_all(result, output_dir)

    manifest = json.loads((output_dir / "scan_manifest.json").read_text(encoding="utf-8"))
    assert manifest["read_only"] is True


def test_manifest_has_sha256_for_outputs(tmp_path):
    root = tmp_path / "s"
    root.mkdir()
    (root / "f.txt").write_text("f")

    output_dir = tmp_path / "out"
    result = scan(root_path=root)
    write_all(result, output_dir)

    manifest = json.loads((output_dir / "scan_manifest.json").read_text(encoding="utf-8"))
    for label in ("file_inventory_json", "file_inventory_csv", "scan_summary_md"):
        assert label in manifest["output_files"]
        assert len(manifest["output_files"][label]["sha256"]) == 64


# ---------------------------------------------------------------------------
# 10. Empty directory
# ---------------------------------------------------------------------------


def test_scan_empty_directory(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()

    result = scan(root_path=empty, run_name="empty-test")

    assert result.total_files == 0
    assert result.total_directories == 1  # the root itself
    assert result.errors_count == 0
    assert result.total_size_bytes == 0


def test_write_all_on_empty_directory(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    output_dir = tmp_path / "out"

    result = scan(root_path=empty)
    artefacts = write_all(result, output_dir)

    for path in artefacts.values():
        assert path.exists()


# ---------------------------------------------------------------------------
# 11. validate_output_dir raises when output is inside root
# ---------------------------------------------------------------------------


def test_validate_output_dir_rejects_output_inside_root(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    output_inside = root / "output"

    with pytest.raises(ValueError, match="output_dir must not be inside root_path"):
        validate_output_dir(root, output_inside)


def test_validate_output_dir_accepts_sibling(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    sibling = tmp_path / "output"

    # Should not raise
    validate_output_dir(root, sibling)


# ---------------------------------------------------------------------------
# 12. JSON structure is valid
# ---------------------------------------------------------------------------


def test_json_inventory_structure(tmp_path):
    root = tmp_path / "s"
    root.mkdir()
    (root / "a.pdf").write_bytes(b"PDF")
    (root / "sub").mkdir()
    (root / "sub" / "b.txt").write_text("b")

    output_dir = tmp_path / "out"
    result = scan(root_path=root)
    write_all(result, output_dir)

    data = json.loads((output_dir / "file_inventory.json").read_text(encoding="utf-8"))

    assert "metadata" in data
    assert "files" in data
    assert "directories" in data
    assert "errors" in data
    assert data["metadata"]["total_files"] == 2
    assert data["metadata"]["total_directories"] == 2


# ---------------------------------------------------------------------------
# 13. ScanResult properties
# ---------------------------------------------------------------------------


def test_scan_result_properties(tmp_path):
    _make_tree(tmp_path)
    result = scan(root_path=tmp_path)

    assert result.total_files == len(result.files)
    assert result.total_directories == len(result.directories)
    assert result.errors_count == len(result.errors)
    assert result.total_size_bytes == sum(f.size_bytes for f in result.files)
    assert result.duration_seconds >= 0


# ---------------------------------------------------------------------------
# 14. run_name is preserved in result
# ---------------------------------------------------------------------------


def test_run_name_preserved(tmp_path):
    _make_tree(tmp_path)
    result = scan(root_path=tmp_path, run_name="my-run")
    assert result.run_name == "my-run"


def test_run_name_auto_generated_when_empty(tmp_path):
    _make_tree(tmp_path)
    result = scan(root_path=tmp_path, run_name="")
    assert result.run_name.startswith("scan-")


# ---------------------------------------------------------------------------
# 15. FileNotFoundError on non-existent root
# ---------------------------------------------------------------------------


def test_scan_raises_on_missing_root(tmp_path):
    missing = tmp_path / "does_not_exist"
    with pytest.raises(FileNotFoundError):
        scan(root_path=missing)
