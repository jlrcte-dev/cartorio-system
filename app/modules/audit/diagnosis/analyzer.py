"""DocumentAnalyzer: loads file_inventory.json and runs diagnosis rules.

SAFETY CONTRACT
---------------
- Only opens file_inventory.json and optionally scan_manifest.json.
- Never opens any file path listed inside the inventory.
- Never accesses the original file system tree.
- Never creates or modifies AuditFinding records.
- No database connection of any kind.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.modules.audit.diagnosis.models import DiagnosisCandidate, DiagnosisResult
from app.modules.audit.diagnosis.rules import (
    rule_credential_by_name,
    rule_executable_by_extension,
    rule_financial_archive,
    rule_generic_name,
    rule_large_files,
    rule_old_policy_docs,
    rule_temp_folder,
)
from app.modules.audit.findings.enums import AuditPriority


class InventoryLoadError(ValueError):
    """Raised when file_inventory.json cannot be loaded or parsed."""


class DocumentAnalyzer:
    """Analyzes file_inventory.json to produce DiagnosisCandidate entries.

    Does not access original files.
    Does not create AuditFinding entries.
    Does not connect to any database.
    """

    def __init__(
        self,
        inventory_path: Path | str,
        manifest_path: Path | str | None = None,
        old_file_years: int = 5,
        large_file_mb: int = 50,
        large_pdf_mb: int = 10,
        include_low_priority: bool = False,
        fail_fast: bool = False,
    ) -> None:
        self.inventory_path = Path(inventory_path)
        self.manifest_path = Path(manifest_path) if manifest_path else None
        self.old_file_years = old_file_years
        self.large_file_mb = large_file_mb
        self.large_pdf_mb = large_pdf_mb
        self.include_low_priority = include_low_priority
        self.fail_fast = fail_fast

    # ------------------------------------------------------------------
    # Internal: loading
    # ------------------------------------------------------------------

    def _load_inventory(self) -> dict:
        try:
            with open(self.inventory_path, encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError as exc:
            raise InventoryLoadError(f"Inventory file not found: {self.inventory_path}") from exc
        except json.JSONDecodeError as exc:
            raise InventoryLoadError(f"Invalid JSON in inventory: {exc}") from exc

        if not isinstance(data, dict):
            raise InventoryLoadError("Inventory must be a JSON object at the root level.")
        if "files" not in data:
            raise InventoryLoadError("Inventory JSON is missing the required 'files' key.")
        if not isinstance(data["files"], list):
            raise InventoryLoadError("Inventory 'files' must be a JSON array.")

        return data

    def _load_manifest(self) -> dict | None:
        if self.manifest_path is None:
            return None
        try:
            with open(self.manifest_path, encoding="utf-8") as fh:
                return json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    # ------------------------------------------------------------------
    # Internal: run_id resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_scanner_run_id(inventory: dict, manifest: dict | None) -> str:
        # Manifest takes precedence — it was written after the scan completed
        if manifest:
            run_id = (manifest.get("run") or {}).get("run_id") or manifest.get("run_id")
            if run_id:
                return str(run_id)
        metadata = inventory.get("metadata") or {}
        run_id = metadata.get("run_id")
        return str(run_id) if run_id else "unknown"

    # ------------------------------------------------------------------
    # Public: main entry point
    # ------------------------------------------------------------------

    def run(self) -> DiagnosisResult:
        """Load inventory, apply all rules, and return a DiagnosisResult.

        This method is the only public interface. It never touches the original
        files referenced in the inventory — only the JSON artefact itself.
        """
        inventory = self._load_inventory()
        manifest = self._load_manifest()

        scanner_run_id = self._resolve_scanner_run_id(inventory, manifest)
        files: list[dict] = inventory.get("files") or []
        run_name: str = (inventory.get("metadata") or {}).get("run_name") or "unknown"

        candidates: list[DiagnosisCandidate] = []
        candidates += rule_credential_by_name(files, scanner_run_id)
        candidates += rule_executable_by_extension(files, scanner_run_id)
        candidates += rule_temp_folder(files, scanner_run_id)
        candidates += rule_large_files(files, scanner_run_id, self.large_file_mb, self.large_pdf_mb)
        candidates += rule_generic_name(files, scanner_run_id)
        candidates += rule_financial_archive(files, scanner_run_id)
        candidates += rule_old_policy_docs(files, scanner_run_id, self.old_file_years)

        if not self.include_low_priority:
            candidates = [c for c in candidates if c.priority != AuditPriority.BACKLOG]

        return DiagnosisResult(
            run_name=run_name,
            scanner_run_id=scanner_run_id,
            inventory_path=str(self.inventory_path),
            total_files_analyzed=len(files),
            total_candidates=len(candidates),
            candidates=candidates,
        )
