"""针对 Fixture、Disabled 与 Live 模式配置边界的测试。"""

from __future__ import annotations

from pathlib import Path

from hy3_campus_decision_mcp.config import Hy3Mode, Settings
from hy3_campus_decision_mcp.tools.analyze_academic_snapshot import analyze_academic_snapshot
from hy3_campus_decision_mcp.tools.answer_campus_question import answer_campus_question
from hy3_campus_decision_mcp.tools.runtime import ToolRuntime
from hy3_campus_decision_mcp.tools.status import build_status


async def test_fixture_mode_marks_result(fixture_runtime: ToolRuntime) -> None:
    """Fixture 输出仍经过完整信封，并显式标注运行模式。"""

    result = await answer_campus_question(
        fixture_runtime,
        {"query": "创新创业学分如何认定？", "category": "policy", "max_sources": 5},
    )
    assert result["status"] == "ok"
    assert result["model"]["mode"] == "fixture"


async def test_disabled_mode_returns_hy3_disabled() -> None:
    """直接调用核心实现时，禁用模式不会伪造确定性完整结果。"""

    result = await analyze_academic_snapshot(
        ToolRuntime(Settings(mode=Hy3Mode.DISABLED)),
        {"snapshot_path": "academic/safe_snapshot.json"},
    )
    assert result == {
        "status": "error",
        "code": "hy3_disabled",
        "message": "Hy3 provider is disabled; only status is available.",
    }


async def test_live_mode_does_not_fall_back_when_key_is_missing(fixture_settings: Settings) -> None:
    """Live 缺少 Key 时返回配置错误，而不是读取 Fixture。"""

    settings = fixture_settings.model_copy(update={"mode": Hy3Mode.LIVE})
    result = await answer_campus_question(
        ToolRuntime(settings),
        {"query": "创新创业学分如何认定？", "category": "policy", "max_sources": 5},
    )
    assert result["status"] == "error"
    assert result["code"] == "hy3_api_key_missing"


def test_status_hides_an_absolute_workspace_path(tmp_path: Path) -> None:
    """状态工具只能暴露工作区末级相对标识，不能回显绝对目录。"""

    workspace = tmp_path / "private-campus-root"
    status = build_status(Settings(campus_root=workspace))

    assert status["workspace"] == "private-campus-root"
    assert str(workspace) not in str(status)
