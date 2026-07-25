"""Workspace-constrained path resolution for local examples."""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath

from ..constants import ALLOWED_SOURCE_EXTENSIONS
from ..errors import InputLimitError, SafetyViolationError


class WorkspacePathPolicy:
    """Resolve only existing, supported files under a configured workspace root."""

    def __init__(
        self,
        root: Path,
        *,
        max_file_bytes: int,
        allowed_extensions: frozenset[str] = ALLOWED_SOURCE_EXTENSIONS,
    ) -> None:
        self._root = root.resolve()
        self._max_file_bytes = max_file_bytes
        self._allowed_extensions = allowed_extensions

    @property
    def root(self) -> Path:
        """Return the internal root for trusted application code only."""

        return self._root

    def resolve_file(self, relative_path: str) -> Path:
        """Resolve one allowed relative file while preventing traversal and symlink escape."""

        if not relative_path or relative_path.strip() != relative_path:
            raise SafetyViolationError("path_invalid", "A non-empty relative path is required.")

        windows_path = PureWindowsPath(relative_path)
        posix_path = PurePosixPath(relative_path)
        if windows_path.is_absolute() or posix_path.is_absolute() or windows_path.drive:
            raise SafetyViolationError("path_absolute_rejected", "Absolute paths are not allowed.")
        if ".." in windows_path.parts or ".." in posix_path.parts:
            raise SafetyViolationError("path_traversal_rejected", "Path traversal is not allowed.")

        candidate = (self._root / Path(relative_path)).resolve()
        if not candidate.is_relative_to(self._root):
            raise SafetyViolationError(
                "path_outside_workspace", "The requested path is outside the workspace."
            )
        if not candidate.is_file():
            raise SafetyViolationError(
                "source_not_found", "The requested source file does not exist."
            )
        if candidate.suffix.lower() not in self._allowed_extensions:
            raise SafetyViolationError(
                "source_extension_rejected", "This source file type is not supported."
            )
        if candidate.stat().st_size > self._max_file_bytes:
            raise InputLimitError(
                "source_file_too_large", "The requested source file exceeds the size limit."
            )
        return candidate

    def relative_identifier(self, file_path: Path) -> str:
        """Return a portable workspace-relative identifier for client-visible source metadata."""

        resolved = file_path.resolve()
        if not resolved.is_relative_to(self._root):
            raise SafetyViolationError(
                "path_outside_workspace", "The requested path is outside the workspace."
            )
        return resolved.relative_to(self._root).as_posix()
