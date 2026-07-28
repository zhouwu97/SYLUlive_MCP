"""状态工具和 tools/list 共享同一注册来源。"""

from __future__ import annotations

from hy3_campus_decision_mcp.config import Hy3Mode, Settings, ToolProfile
from hy3_campus_decision_mcp.contracts import PINNED_TOOL_CONTRACTS
from hy3_campus_decision_mcp.tools.status import build_status


def test_status_contract_version_and_hashes() -> None:
    """Go 校验所需字段必须稳定且脱敏。"""

    status = build_status(Settings(mode=Hy3Mode.FIXTURE, tool_profile=ToolProfile.SYLULIVE_RUNTIME))
    assert status["contract_version"] == "sylulive-hy3/1"
    assert status["tool_contracts"] == PINNED_TOOL_CONTRACTS
    assert status["mode"] == "fixture"
    assert "test-key" not in str(status)
