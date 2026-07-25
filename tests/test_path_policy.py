"""工作区路径隔离测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from hy3_campus_decision_mcp.errors import SafetyViolationError
from hy3_campus_decision_mcp.safety.path_policy import WorkspacePathPolicy


def _policy(root: Path) -> WorkspacePathPolicy:
    """创建一个供单测使用的小型路径策略。"""

    return WorkspacePathPolicy(root, max_file_bytes=1_024)


def test_relative_json_file_is_resolved_inside_workspace(tmp_path: Path) -> None:
    """正常相对路径可读，并以 POSIX 相对标识返回。"""

    root = tmp_path / "examples"
    root.mkdir()
    source = root / "academic.json"
    source.write_text("{}", encoding="utf-8")
    policy = _policy(root)
    assert policy.resolve_file("academic.json") == source.resolve()
    assert policy.relative_identifier(source) == "academic.json"


@pytest.mark.parametrize("value", ["../outside.json", "C:/outside.json", "/outside.json"])
def test_traversal_and_absolute_paths_are_rejected(tmp_path: Path, value: str) -> None:
    """用户不能借由平台路径格式跳出工作区。"""

    root = tmp_path / "examples"
    root.mkdir()
    with pytest.raises(SafetyViolationError):
        _policy(root).resolve_file(value)


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    """解析后的符号链接目标仍必须留在工作区中。"""

    root = tmp_path / "examples"
    root.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    link = root / "escaped.json"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("当前 Windows 环境未授予创建符号链接权限")
    with pytest.raises(SafetyViolationError):
        _policy(root).resolve_file("escaped.json")
