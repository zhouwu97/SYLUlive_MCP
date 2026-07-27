"""赛事事实检索和比较测试。"""

from __future__ import annotations

from sylulive_mcp.tools.competition_compare_facts import competition_compare_facts
from sylulive_mcp.tools.competition_get_details import competition_get_details
from sylulive_mcp.tools.competition_search import competition_search


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
