"""正式 CLI 与安装资源的回归测试。"""

from __future__ import annotations

import json
import subprocess
import sys

from hy3_campus_decision_mcp.config import default_campus_root, default_fixture_root
from hy3_campus_decision_mcp.constants import PACKAGE_VERSION


def test_packaged_defaults_are_available() -> None:
    """源码与 wheel 模式都必须能找到自包含演示资源。"""

    assert (default_campus_root() / "policy_bundle" / "policy-bundle-manifest.json").is_file()
    assert (default_fixture_root() / "answer_campus_question.json").is_file()


def test_version_cli() -> None:
    """版本查询不得启动或污染 MCP stdio。"""

    result = subprocess.run(
        [sys.executable, "-m", "hy3_campus_decision_mcp", "--version"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.stdout.strip() == PACKAGE_VERSION
    assert result.stderr == ""


def test_selfcheck_cli() -> None:
    """自检必须通过真实子进程完成 MCP 握手和四个核心工具调用。"""

    result = subprocess.run(
        [sys.executable, "-m", "hy3_campus_decision_mcp", "--selfcheck"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["tool_count"] == 5
