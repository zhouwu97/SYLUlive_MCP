"""敏感字段递归扫描测试。"""

from __future__ import annotations

import pytest

from hy3_campus_decision_mcp.errors import SafetyViolationError
from hy3_campus_decision_mcp.safety.sensitive_fields import reject_sensitive_fields
from hy3_campus_decision_mcp.tools.analyze_academic_snapshot import analyze_academic_snapshot
from hy3_campus_decision_mcp.tools.runtime import ToolRuntime


@pytest.mark.parametrize(
    "field_name",
    ["student_id", "StudentNumber", "access-token", "REFRESH_TOKEN", "realName"],
)
def test_sensitive_field_name_variants_are_rejected(field_name: str) -> None:
    """大小写、短横线、下划线和驼峰形式都不能绕过扫描。"""

    with pytest.raises(SafetyViolationError):
        reject_sensitive_fields({"outer": [{"inner": {field_name: "secret"}}]})


async def test_academic_scans_before_schema_validation(fixture_runtime: ToolRuntime) -> None:
    """深层敏感字段即使位于未知扩展字段中也不能到达 Provider。"""

    result = await analyze_academic_snapshot(
        fixture_runtime,
        {
            "snapshot": {
                "courses": [
                    {
                        "course_name": "课程",
                        "credits": 3,
                        "grade": 80,
                        "nested": {"access_token": "secret"},
                    }
                ],
                "earned_credits": 3,
                "required_credits": 108,
                "erke_earned": 0,
                "erke_required": 60,
            }
        },
    )
    assert result["status"] == "error"
    assert result["code"] == "sensitive_field_rejected"
