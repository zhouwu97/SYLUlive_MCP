"""学业确定性汇总测试。"""

from __future__ import annotations

import json

import httpx

from sylulive_mcp.config import ServiceMode, Settings
from sylulive_mcp.tools.academic_calculate_summary import academic_calculate_summary
from sylulive_mcp.tools.academic_get_summary import academic_get_summary
from sylulive_mcp.tools.runtime import ToolRuntime


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


async def test_production_academic_summary_uses_grant_owned_go_data() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "result": {
                    "earned_credits": 86,
                    "required_credits": 160,
                    "failed_course_count": 2,
                    "failed_credits": 5,
                    "gpa": 2.84,
                    "data_completeness": "complete",
                },
            },
        )

    settings = Settings(mode=ServiceMode.PRODUCTION, api_base="https://internal.example")
    runtime = ToolRuntime(settings, api_transport=httpx.MockTransport(handler))
    try:
        with runtime.grants.bind("academic-grant"):
            result = await academic_get_summary(runtime, {})
    finally:
        await runtime.aclose()

    assert result["status"] == "ok"
    assert captured == {
        "authorization": "Bearer academic-grant",
        "payload": {"semester": "current"},
    }
    assert "courses" not in str(captured["payload"])
