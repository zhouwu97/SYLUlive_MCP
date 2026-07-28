"""diaofenyuan 运行时固定契约的回归测试。"""

from __future__ import annotations

from hy3_campus_decision_mcp.contracts import (
    PINNED_TOOL_CONTRACTS,
    SYLULIVE_RUNTIME_TOOL_NAMES,
    TOOL_CONTRACTS,
)


def test_runtime_schema_digests_match_go_pins() -> None:
    """Schema 漂移必须在测试阶段暴露，而不能由状态工具掩盖。"""

    for name in SYLULIVE_RUNTIME_TOOL_NAMES:
        contract = TOOL_CONTRACTS[name]
        assert contract.input_schema["type"] == "object"
        assert contract.output_schema["type"] == "object"
        assert contract.schema_sha256 == PINNED_TOOL_CONTRACTS[name]["schema_sha256"]
