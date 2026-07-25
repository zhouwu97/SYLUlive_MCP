"""本地示例使用的工作区受限路径解析。"""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath

from ..constants import ALLOWED_SOURCE_EXTENSIONS
from ..errors import InputLimitError, SafetyViolationError


class WorkspacePathPolicy:
    """仅解析配置工作区根目录下存在且受支持的文件。"""

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
        """仅向可信应用代码返回内部根目录。"""

        return self._root

    @property
    def max_file_bytes(self) -> int:
        """返回供只读仓库执行预筛选的文件大小上限。"""

        return self._max_file_bytes

    def resolve_file(self, relative_path: str) -> Path:
        """解析一个允许的相对文件，并防止路径穿越和符号链接越界。"""

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
        """为客户端可见的来源元数据返回可移植工作区相对标识。"""

        resolved = file_path.resolve()
        if not resolved.is_relative_to(self._root):
            raise SafetyViolationError(
                "path_outside_workspace", "The requested path is outside the workspace."
            )
        return resolved.relative_to(self._root).as_posix()
