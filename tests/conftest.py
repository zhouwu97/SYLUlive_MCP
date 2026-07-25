"""测试使用的独立 Fixture 配置。"""

from __future__ import annotations

from pathlib import Path

import pytest

from hy3_campus_decision_mcp.config import Hy3Mode, Settings
from hy3_campus_decision_mcp.tools.runtime import ToolRuntime

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def fixture_settings() -> Settings:
    """返回不依赖环境变量或真实 API Key 的测试设置。"""

    return Settings(
        mode=Hy3Mode.FIXTURE,
        campus_root=PROJECT_ROOT / "examples",
        fixture_root=PROJECT_ROOT / "tests" / "fixtures" / "hy3",
    )


@pytest.fixture
def fixture_runtime(fixture_settings: Settings) -> ToolRuntime:
    """创建一个指向示例数据与固定响应的工具运行时。"""

    return ToolRuntime(fixture_settings)
