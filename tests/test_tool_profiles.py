"""便携与 SYLUlive Runtime 工具注册模式测试。"""

from __future__ import annotations

from hy3_campus_decision_mcp.config import Hy3Mode, Settings, ToolProfile
from hy3_campus_decision_mcp.contracts import contracts_for_profile
from hy3_campus_decision_mcp.tools.status import build_status


def test_portable_profile_keeps_question_tool() -> None:
    """便携客户端仍可使用问答工具。"""

    settings = Settings(mode=Hy3Mode.FIXTURE, tool_profile=ToolProfile.PORTABLE)
    assert "answer_campus_question" in contracts_for_profile(settings.tool_profile)
    assert len(build_status(settings)["available_tools"]) == 5


def test_sylulive_profile_exposes_only_three_decision_tools() -> None:
    """Go Runtime 不应看到便携问答工具。"""

    settings = Settings(mode=Hy3Mode.FIXTURE, tool_profile=ToolProfile.SYLULIVE_RUNTIME)
    assert list(contracts_for_profile(settings.tool_profile)) == [
        "compare_competitions",
        "analyze_academic_snapshot",
        "plan_student_week",
    ]
    assert build_status(settings)["available_tools"] == [
        "hy3_campus_status",
        "compare_competitions",
        "analyze_academic_snapshot",
        "plan_student_week",
    ]


def test_disabled_profile_only_reports_status() -> None:
    """禁用模式不声明任何可调用决策工具。"""

    status = build_status(Settings(mode=Hy3Mode.DISABLED))
    assert status["available_tools"] == ["hy3_campus_status"]
    assert status["tool_contracts"] == {}
