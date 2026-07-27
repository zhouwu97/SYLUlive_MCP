"""赛事事实检索和比较测试。"""

from __future__ import annotations

import json

import httpx

from sylulive_mcp.config import ServiceMode, Settings
from sylulive_mcp.tools.competition_compare_facts import competition_compare_facts
from sylulive_mcp.tools.competition_get_details import competition_get_details
from sylulive_mcp.tools.competition_search import competition_search
from sylulive_mcp.tools.runtime import ToolRuntime


async def test_competition_flow_keeps_dimensions_separate(demo_runtime) -> None:
    searched = await competition_search(demo_runtime, {"categories": ["计算机"], "limit": 3})
    assert searched["status"] == "ok"
    assert len(searched["competitions"]) >= 2
    ids = [item["competition_id"] for item in searched["competitions"][:2]]
    details = await competition_get_details(demo_runtime, {"competition_ids": ids})
    compared = await competition_compare_facts(
        demo_runtime,
        {
            "competitions": details["competitions"],
            "student_profile": {
                "major": "计算机科学与技术",
                "grade": "大三",
                "weekly_hours": 8,
            },
        },
    )
    assert compared["status"] == "ok"
    assert all(item["profile_match"]["major"] for item in compared["competitions"])
    assert all("score" not in item for item in compared["competitions"])
    assert "recommendation" not in compared


async def test_production_comparison_accepts_only_ids_and_returns_go_facts() -> None:
    captured_payload: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "competitions": [
                    {
                        "competition_id": competition_id,
                        "name": f"赛事 {index}",
                        "school_recognition": "A",
                        "manual_rating": "B",
                        "eligible": True,
                        "profile_match": {"major": True, "grade": True, "time": False},
                        "weekly_hours": 8,
                        "evidence_quality": "official",
                        "source_id": f"source-{index}",
                    }
                    for index, competition_id in enumerate(["competition-a", "competition-b"])
                ],
            },
        )

    settings = Settings(mode=ServiceMode.PRODUCTION, api_base="https://internal.example")
    runtime = ToolRuntime(settings, api_transport=httpx.MockTransport(handler))
    try:
        with runtime.grants.bind("competition-grant"):
            result = await competition_compare_facts(
                runtime,
                {
                    "competition_ids": ["competition-a", "competition-b"],
                    "available_weekly_hours": 6,
                },
            )
            rejected = await competition_compare_facts(
                runtime,
                {
                    "competitions": [
                        {"competition_id": "fake", "school_recognition": "S"},
                        {"competition_id": "fake-2", "school_recognition": "S"},
                    ]
                },
            )
    finally:
        await runtime.aclose()

    assert result["status"] == "ok"
    assert captured_payload == {
        "competition_ids": ["competition-a", "competition-b"],
        "available_weekly_hours": 6,
    }
    assert rejected["code"] == "invalid_input"
