"""Read-only file system scanner.

SAFETY CONTRACT
---------------
- Never calls open() on any file inside the scanned tree.
- Never calls os.remove(), os.rename(), shutil.move(), or any write operation.
- Only uses os.stat(), os.walk(), os.path.* on the scanned tree.
- Writes output exclusively to the caller-supplied output_dir.
- output_dir must not be inside root_path (enforced at runtime).
"""

from __future__ import annotations

import fnmatch
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.core.logging import get_logger
from app.modules.audit.scanner.models import (
    DirectoryEntry,
    FileEntry,
    ScanError,
    ScanParameters,
    ScanResult,
)

logger = get_logger("audit.scanner")

# Common patterns excluded by default to avoid noisy system entries.
DEFAULT_EXCLUDES: list[str] = [
    "$RECYCLE.BIN",
    "System Volume Information",
    "desktop.ini",
    "Thumbs.db",
    ".Spotlight-V100",
    ".Trashes",
    ".fseventsd",
]


def _normalize(p: str) -> str:
    """Normalize path separators to forward slashes for portable output."""
    return p.replace("\\", "/")


def _safe_ts(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=UTC)


def _matches_exclusion(name: str, abs_path: str, patterns: list[str]) -> bool:
    """Return True if the entry should be excluded based on any pattern."""
    norm = abs_path.replace("\\", "/")
    for pat in patterns:
        if name == pat:
            return True
        if fnmatch.fnmatch(name, pat):
            return True
        pat_norm = pat.replace("\\", "/")
        # substring of name
        if pat_norm in name:
            return True
        # absolute path ends with the pattern
        if norm.endswith("/" + pat_norm):
            return True
    return False


def scan(
    root_path: str | Path,
    run_name: str = "",
    exclude_patterns: list[str] | None = None,
    max_depth: int | None = None,
    follow_symlinks: bool = False,
    include_hidden: bool = True,
    fail_fast: bool = False,
) -> ScanResult:
    """Traverse *root_path* read-only and return a :class:`ScanResult`.

    Parameters
    ----------
    root_path:
        Directory to scan.  Must exist and be a directory.
    run_name:
        Human-readable label for this run.  Auto-generated if empty.
    exclude_patterns:
        Names, substrings, or glob patterns for entries to skip.
        DEFAULT_EXCLUDES are always prepended.
    max_depth:
        Maximum traversal depth from root.  ``None`` means unlimited.
        depth 0 = root itself; depth 1 = direct children.
    follow_symlinks:
        Follow symbolic links.  ``False`` by default to avoid loops.
    include_hidden:
        Include entries whose names start with ``"."`` .
    fail_fast:
        Re-raise the first OS-level error instead of recording it.
    """
    root = Path(root_path).resolve()
    if not root.exists():
        raise FileNotFoundError("Scan root does not exist: [REDACTED]")
    if not root.is_dir():
        raise NotADirectoryError("Scan root is not a directory: [REDACTED]")

    run_id = str(uuid.uuid4())
    if not run_name:
        run_name = f"scan-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"

    patterns = list(DEFAULT_EXCLUDES) + list(exclude_patterns or [])
    parameters = ScanParameters(
        max_depth=max_depth,
        follow_symlinks=follow_symlinks,
        include_hidden=include_hidden,
        fail_fast=fail_fast,
        exclude_patterns=list(exclude_patterns or []),
    )

    files: list[FileEntry] = []
    directories: list[DirectoryEntry] = []
    scan_errors: list[ScanError] = []
    excluded_count = 0
    root_depth = len(root.parts)

    def _on_error(exc: OSError) -> None:
        if fail_fast:
            raise exc
        try:
            rel = _normalize(str(Path(str(exc.filename or "")).relative_to(root)))
        except (ValueError, TypeError):
            rel = str(exc.filename or "[unknown]")
        scan_errors.append(
            ScanError(
                path_relative=rel,
                error_type=type(exc).__name__,
                message=str(exc)[:200],
                depth=0,
            )
        )
        logger.warning("Walk error: type=%s", type(exc).__name__)

    started_at = datetime.now(UTC)
    logger.info("Scan started: run_id=%s, run_name=%s", run_id, run_name)

    # dir_size_acc: accumulate direct child file sizes per directory
    dir_size_acc: dict[str, int] = {}

    for dirpath, dirnames, filenames in os.walk(
        str(root),
        topdown=True,
        onerror=_on_error,
        followlinks=follow_symlinks,
    ):
        current = Path(dirpath)
        try:
            path_rel = _normalize(str(current.relative_to(root)))
        except ValueError:
            path_rel = _normalize(dirpath)

        current_depth = len(current.parts) - root_depth

        # --- Prune dirnames in-place so os.walk won't descend ---
        to_remove: list[str] = []
        for d in list(dirnames):
            d_abs = str(current / d)
            if (not include_hidden and d.startswith(".")) or _matches_exclusion(d, d_abs, patterns):
                to_remove.append(d)
                excluded_count += 1
        for d in to_remove:
            dirnames.remove(d)

        # Prune depth: if we are already at max_depth, don't go deeper
        if max_depth is not None and current_depth >= max_depth:
            dirnames.clear()

        # --- Collect directory entry ---
        dir_name = current.name if path_rel != "." else root.name
        parent_rel = _normalize(str(current.parent.relative_to(root))) if current_depth > 0 else ""
        dir_entry = DirectoryEntry(
            name=dir_name,
            path_relative=path_rel,
            parent_path=parent_rel,
            entry_type="directory",
            depth=current_depth,
            direct_files=len(filenames),
            direct_subdirs=len(dirnames),
        )
        directories.append(dir_entry)
        dir_size_acc[path_rel] = 0  # initialise; will be filled per file below

        # --- Collect file entries (only within max_depth) ---
        # current_depth is the depth of the directory; files inside are at current_depth+1.
        # max_depth=1 means: collect files only at depth 0 (root's direct files).
        # max_depth=0 means: collect nothing (only the root directory entry itself).
        if max_depth is not None and current_depth >= max_depth:
            continue

        for fname in filenames:
            if not include_hidden and fname.startswith("."):
                excluded_count += 1
                continue
            f_abs = str(current / fname)
            if _matches_exclusion(fname, f_abs, patterns):
                excluded_count += 1
                continue

            _, ext = os.path.splitext(fname)
            file_rel = _normalize(str(Path(path_rel) / fname) if path_rel != "." else fname)

            try:
                st = os.stat(f_abs)
                size_bytes = st.st_size
                modified_at: datetime | None = _safe_ts(st.st_mtime)
                created_at: datetime | None = _safe_ts(st.st_ctime)
            except (PermissionError, FileNotFoundError, OSError) as exc:
                if fail_fast:
                    raise
                scan_errors.append(
                    ScanError(
                        path_relative=file_rel,
                        error_type=type(exc).__name__,
                        message=str(exc)[:200],
                        depth=current_depth + 1,
                    )
                )
                logger.warning(
                    "stat error: type=%s, depth=%d", type(exc).__name__, current_depth + 1
                )
                continue

            files.append(
                FileEntry(
                    name=fname,
                    extension=ext.lower(),
                    path_relative=file_rel,
                    parent_path=path_rel,
                    entry_type="file",
                    depth=current_depth + 1,
                    size_bytes=size_bytes,
                    modified_at=modified_at,
                    created_at=created_at,
                )
            )
            dir_size_acc[path_rel] = dir_size_acc.get(path_rel, 0) + size_bytes

    # Propagate accumulated direct-file sizes back to DirectoryEntry objects
    for d in directories:
        d.total_size_bytes = dir_size_acc.get(d.path_relative, 0)

    finished_at = datetime.now(UTC)
    duration = (finished_at - started_at).total_seconds()

    logger.info(
        "Scan finished: run_id=%s, files=%d, dirs=%d, errors=%d, excluded=%d, duration=%.2fs",
        run_id,
        len(files),
        len(directories),
        len(scan_errors),
        excluded_count,
        duration,
    )

    return ScanResult(
        run_id=run_id,
        run_name=run_name,
        root_path_display="[root]",
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=duration,
        files=files,
        directories=directories,
        errors=scan_errors,
        excluded_count=excluded_count,
        parameters=parameters,
    )


def validate_output_dir(root_path: str | Path, output_dir: str | Path) -> None:
    """Raise ValueError if output_dir is inside root_path.

    Writing scan results inside the scanned tree would contaminate the analysis
    and violates the read-only-on-server contract.
    """
    root = Path(root_path).resolve()
    out = Path(output_dir).resolve()
    try:
        out.relative_to(root)
        raise ValueError(
            "output_dir must not be inside root_path. "
            "Writing scan results into the scanned tree is not allowed."
        )
    except ValueError as exc:
        # re-raise only the intentional one
        if "output_dir must not" in str(exc):
            raise
