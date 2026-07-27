"""学业确定性汇总测试。"""

from __future__ import annotations

from sylulive_mcp.tools.academic_calculate_summary import academic_calculate_summary


async def test_academic_summary_is_deterministic(demo_runtime) -> None:
    result = await academic_calculate_summary(
        demo_runtime, {"snapshot_path": "academic/safe_snapshot.json"}
    )
    assert result["status"] == "ok"
    assert result["result"]["earned_credits"] == 96
    assert result["result"]["credit_gap"] == 12
    assert result["result"]["failed_course_count"] == 1
    assert result["result"]["failed_credits"] == 3
    assert result["result"]["data_completeness"] == "partial"
    assert "risk" not in result["result"]
    assert "model" not in result


async def test_sensitive_identity_fields_are_rejected_before_schema(demo_runtime) -> None:
    result = await academic_calculate_summary(
        demo_runtime,
        {
            "snapshot": {
                "student_id": "secret",
                "courses": [],
                "earned_credits": 0,
                "required_credits": 1,
                "erke_earned": 0,
                "erke_required": 1,
            }
        },
    )
    assert result["code"] == "sensitive_field_rejected"
