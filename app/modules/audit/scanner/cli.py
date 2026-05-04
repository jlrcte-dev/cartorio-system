"""CLI entry point for the read-only file scanner.

Usage
-----
    python -m app.modules.audit.scanner.cli \\
        --root "C:\\Dados\\Servidor" \\
        --output-dir "exports\\audit\\scan-2026-05-04" \\
        --run-name "scan-inicial"

All output is written to --output-dir.  The scanned tree is never modified.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.core.logging import get_logger, setup_logging
from app.modules.audit.scanner.file_scanner import scan, validate_output_dir
from app.modules.audit.scanner.report import write_all

logger = get_logger("audit.scanner.cli")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.modules.audit.scanner.cli",
        description=(
            "Read-only file system scanner for the Cartório System audit module. "
            "Traverses a directory tree, collects metadata, and generates "
            "JSON / CSV / Markdown / manifest reports."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m app.modules.audit.scanner.cli \\\n"
            '      --root "C:\\\\Dados\\\\Servidor" \\\n'
            '      --output-dir "exports\\\\audit\\\\scan-inicial" \\\n'
            '      --run-name "scan-inicial"\n\n'
            "  python -m app.modules.audit.scanner.cli \\\n"
            "      --root /mnt/servidor \\\n"
            "      --output-dir ./exports/audit/scan-test \\\n"
            "      --max-depth 5 \\\n"
            '      --exclude "$RECYCLE.BIN" --exclude ".git"\n'
        ),
    )

    parser.add_argument(
        "--root",
        required=True,
        metavar="PATH",
        help="Root directory to scan (read-only).",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        metavar="PATH",
        help=(
            "Directory where JSON, CSV, Markdown, and manifest will be written. "
            "Must NOT be inside --root."
        ),
    )
    parser.add_argument(
        "--run-name",
        default="",
        metavar="NAME",
        help="Human-readable label for this run. Auto-generated if omitted.",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        metavar="N",
        help="Maximum traversal depth from root (0 = root only). Unlimited if omitted.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="PATTERN",
        dest="exclude_patterns",
        help="Name, substring, or glob pattern to exclude. Repeatable.",
    )
    parser.add_argument(
        "--follow-symlinks",
        action="store_true",
        default=False,
        help="Follow symbolic links (disabled by default to avoid loops).",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        default=True,
        help="Include hidden entries (names starting with '.').  Default: true.",
    )
    parser.add_argument(
        "--no-hidden",
        action="store_false",
        dest="include_hidden",
        help="Exclude hidden entries.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        default=False,
        help="Abort on first OS-level error instead of recording it and continuing.",
    )
    return parser


def main() -> None:
    """Entry point for the CLI."""
    setup_logging()
    parser = _build_parser()
    args = parser.parse_args()

    root = Path(args.root)
    output_dir = Path(args.output_dir)

    # Safety: reject output inside the scanned tree
    try:
        validate_output_dir(root, output_dir)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Starting read-only scan…")
    print(f"  root        : {root}")
    print(f"  output-dir  : {output_dir}")
    print(f"  run-name    : {args.run_name or '(auto)'}")
    if args.max_depth is not None:
        print(f"  max-depth   : {args.max_depth}")
    if args.exclude_patterns:
        print(f"  excludes    : {', '.join(args.exclude_patterns)}")

    try:
        result = scan(
            root_path=root,
            run_name=args.run_name,
            exclude_patterns=args.exclude_patterns or None,
            max_depth=args.max_depth,
            follow_symlinks=args.follow_symlinks,
            include_hidden=args.include_hidden,
            fail_fast=args.fail_fast,
        )
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    artefacts = write_all(result, output_dir)

    print()
    print("Scan complete.")
    print(f"  files       : {result.total_files:,}")
    print(f"  directories : {result.total_directories:,}")
    print(f"  errors      : {result.errors_count:,}")
    print(f"  excluded    : {result.excluded_count:,}")
    print(f"  duration    : {result.duration_seconds:.2f}s")
    print()
    print("Output files:")
    for label, path in artefacts.items():
        print(f"  {label:<30} {path}")


if __name__ == "__main__":
    main()
