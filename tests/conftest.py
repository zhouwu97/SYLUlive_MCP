"""测试使用的独立演示配置。"""

from __future__ import annotations

from pathlib import Path

import pytest

from sylulive_mcp.config import ServiceMode, Settings
from sylulive_mcp.tools.runtime import ToolRuntime

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def demo_settings() -> Settings:
    return Settings(mode=ServiceMode.DEMO, demo_root=PROJECT_ROOT / "examples")


@pytest.fixture
async def demo_runtime(demo_settings: Settings):
    runtime = ToolRuntime(demo_settings)
    try:
        yield runtime
    finally:
        await runtime.aclose()
