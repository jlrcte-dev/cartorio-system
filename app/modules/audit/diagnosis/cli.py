"""CLI entry point for DocumentDiagnosis.

Usage
-----
    python -m app.modules.audit.diagnosis.cli \\
        --inventory "C:\\Audit_Reports\\2026-05-04\\scan\\file_inventory.json" \\
        --output-dir "C:\\Audit_Reports\\2026-05-04\\diagnosis" \\
        --run-name "diagnosis-inicial"

Reads file_inventory.json produced by the scanner.
Never opens any file listed in the inventory.
Never creates AuditFinding entries.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.core.logging import get_logger, setup_logging
from app.modules.audit.diagnosis.analyzer import DocumentAnalyzer, InventoryLoadError
from app.modules.audit.diagnosis.report import write_all

logger = get_logger("audit.diagnosis.cli")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.modules.audit.diagnosis.cli",
        description=(
            "DocumentDiagnosis: metadata-only analysis of a file_inventory.json "
            "produced by the Cartório System scanner. "
            "Generates candidates for manual review — never opens original files."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m app.modules.audit.diagnosis.cli \\\n"
            '      --inventory "C:\\\\Audit_Reports\\\\scan\\\\file_inventory.json" \\\n'
            '      --output-dir "C:\\\\Audit_Reports\\\\diagnosis" \\\n'
            '      --run-name "diagnosis-inicial"\n'
        ),
    )

    parser.add_argument(
        "--inventory",
        required=True,
        metavar="PATH",
        help="Path to file_inventory.json produced by the scanner.",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        metavar="PATH",
        help="Optional: path to scan_manifest.json (used to resolve scanner_run_id).",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        metavar="PATH",
        help="Directory where JSON, CSV, Markdown and manifest will be written.",
    )
    parser.add_argument(
        "--run-name",
        default="",
        metavar="NAME",
        help="Human-readable label for this diagnosis run. Auto-generated if omitted.",
    )
    parser.add_argument(
        "--old-file-years",
        type=int,
        default=5,
        metavar="N",
        help="Policy/LGPD files not modified for N+ years (default: 5).",
    )
    parser.add_argument(
        "--large-file-mb",
        type=int,
        default=50,
        metavar="MB",
        help="Non-PDF/video files above this size (MB) are flagged (default: 50).",
    )
    parser.add_argument(
        "--large-pdf-mb",
        type=int,
        default=10,
        metavar="MB",
        help="PDF files above this size (MB) are flagged (default: 10).",
    )
    parser.add_argument(
        "--include-low-priority",
        action="store_true",
        default=False,
        help="Include BACKLOG-priority candidates (videos, other large files, generic names).",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        default=False,
        help="Abort on the first loading error instead of continuing.",
    )
    return parser


def main() -> None:
    """Entry point for the CLI."""
    setup_logging()
    parser = _build_parser()
    args = parser.parse_args()

    inventory_path = Path(args.inventory)
    output_dir = Path(args.output_dir)

    print("Starting DocumentDiagnosis…")
    print(f"  inventory   : {inventory_path}")
    if args.manifest:
        print(f"  manifest    : {args.manifest}")
    print(f"  output-dir  : {output_dir}")
    print(f"  run-name    : {args.run_name or '(auto from inventory)'}")
    print(f"  old-file-years  : {args.old_file_years}")
    print(f"  large-file-mb   : {args.large_file_mb}")
    print(f"  large-pdf-mb    : {args.large_pdf_mb}")
    print(f"  include-low-priority: {args.include_low_priority}")

    analyzer = DocumentAnalyzer(
        inventory_path=inventory_path,
        manifest_path=args.manifest,
        old_file_years=args.old_file_years,
        large_file_mb=args.large_file_mb,
        large_pdf_mb=args.large_pdf_mb,
        include_low_priority=args.include_low_priority,
        fail_fast=args.fail_fast,
    )

    try:
        result = analyzer.run()
    except InventoryLoadError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    artefacts = write_all(result, output_dir)

    print()
    print("Diagnosis complete.")
    print(f"  files analyzed  : {result.total_files_analyzed:,}")
    print(f"  candidates found: {result.total_candidates}")
    print(f"  scanner_run_id  : {result.scanner_run_id}")
    print()
    print("Output files:")
    for label, path in artefacts.items():
        print(f"  {label:<30} {path}")

    logger.info(
        "Diagnosis complete: run_name=%s, files=%d, candidates=%d",
        result.run_name,
        result.total_files_analyzed,
        result.total_candidates,
    )


if __name__ == "__main__":
    main()
