"""政策检索与来源复核测试。"""

from __future__ import annotations

from sylulive_mcp.tools.policy_get_sources import policy_get_sources
from sylulive_mcp.tools.policy_search import policy_search


async def test_policy_search_returns_facts_without_answer(demo_runtime) -> None:
    result = await policy_search(
        demo_runtime,
        {
            "queries": ["交不起学费怎么办", "国家助学贷款"],
            "historical_mode": "forbid",
            "limit": 8,
        },
    )
    assert result["status"] == "ok"
    assert result["results"]
    assert len(result["results"]) <= 8
    assert "answer" not in result
    assert "model" not in result
    assert result["degraded_modes"] == ["demo_local_retrieval"]


async def test_policy_source_recheck_returns_hash_and_missing_ids(demo_runtime) -> None:
    searched = await policy_search(
        demo_runtime,
        {"queries": ["挂科怎么办"], "historical_mode": "forbid", "limit": 2},
    )
    source_id = searched["results"][0]["source_id"]
    checked = await policy_get_sources(demo_runtime, {"source_ids": [source_id, "not-present"]})
    assert checked["status"] == "ok"
    assert checked["sources"][0]["content_hash"].startswith("sha256:")
    assert checked["missing_source_ids"] == ["not-present"]


async def test_policy_limits_are_enforced(demo_runtime) -> None:
    result = await policy_search(
        demo_runtime,
        {"queries": ["a", "b", "c", "d", "e"], "limit": 20},
    )
    assert result["status"] == "error"
    assert result["code"] == "invalid_input"
