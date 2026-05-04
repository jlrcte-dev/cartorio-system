from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Literal


@dataclasses.dataclass(slots=True)
class FileEntry:
    """Metadata for a single file — collected read-only via os.stat()."""

    name: str
    extension: str  # lower-cased, e.g. ".pdf"; empty string if no extension
    path_relative: str  # relative to the scan root, forward slashes
    parent_path: str  # relative path of the immediate parent directory
    entry_type: Literal["file"]
    depth: int  # 1 for files directly inside root
    size_bytes: int
    modified_at: datetime | None
    created_at: datetime | None  # st_ctime: creation on Windows, metadata-change on POSIX
    error: str | None = None  # set when stat() raised an exception


@dataclasses.dataclass(slots=True)
class DirectoryEntry:
    """Metadata for a single directory — collected read-only via os.walk()."""

    name: str
    path_relative: str  # "." for the scan root itself
    parent_path: str  # empty string for the scan root
    entry_type: Literal["directory"]
    depth: int  # 0 for scan root
    direct_files: int = 0
    direct_subdirs: int = 0
    total_size_bytes: int = 0  # sum of direct child file sizes (non-recursive)
    error: str | None = None


@dataclasses.dataclass(slots=True)
class ScanError:
    """Record of a non-fatal error encountered during traversal."""

    path_relative: str
    error_type: str  # class name, e.g. "PermissionError"
    message: str  # truncated to 200 chars
    depth: int


@dataclasses.dataclass
class ScanParameters:
    """Immutable record of the parameters used for a scan run."""

    max_depth: int | None
    follow_symlinks: bool
    include_hidden: bool
    fail_fast: bool
    exclude_patterns: list[str]


@dataclasses.dataclass
class ScanResult:
    """Complete, read-only result of one scan run."""

    run_id: str
    run_name: str
    root_path_display: str  # always "[root]" in exported artefacts
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    files: list[FileEntry]
    directories: list[DirectoryEntry]
    errors: list[ScanError]
    excluded_count: int
    parameters: ScanParameters

    @property
    def total_files(self) -> int:
        return len(self.files)

    @property
    def total_directories(self) -> int:
        return len(self.directories)

    @property
    def total_size_bytes(self) -> int:
        return sum(f.size_bytes for f in self.files)

    @property
    def errors_count(self) -> int:
        return len(self.errors)
