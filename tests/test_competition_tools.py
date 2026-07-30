"""赛事事实检索和比较测试。"""

from __future__ import annotations

import json

import httpx

from sylulive_mcp.config import ServiceMode, Settings
from sylulive_mcp.tools.competition_compare_facts import competition_compare_facts
from sylulive_mcp.tools.competition_get_candidate_context import (
    competition_get_candidate_context,
)
from sylulive_mcp.tools.competition_get_details import competition_get_details
from sylulive_mcp.tools.competition_search import competition_search
from sylulive_mcp.tools.competition_verify_records import competition_verify_records
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


async def test_candidate_context_and_record_verification_use_go_as_authority() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path.endswith("/candidate-context"):
            return httpx.Response(
                200,
                json={
                    "status": "ok",
                    "candidates": [
                        {
                            "competition_id": "NAT-006",
                            "record_hash": "a" * 64,
                            "dataset_version": "catalog-v1",
                            "facts": {
                                "title": "程序设计竞赛",
                                "competition_level": "国家级",
                                "school_recognition_status": "recognized",
                                "school_recognition_grade": "B+",
                                "competition_rating": "A",
                                "participation_type": "团队赛",
                                "team_size_min": 3,
                                "team_size_max": 3,
                                "registration_time_text": "",
                                "event_time_text": "",
                                "time_status": "pending",
                                "major_fit_summary_public": "适配软件相关专业",
                                "evidence_summary_public": "公开通知已核验",
                                "evidence_subgrade": "A2",
                            },
                            "match_dimensions": {
                                key: "unknown"
                                for key in (
                                    "eligibility",
                                    "major",
                                    "college",
                                    "grade",
                                    "goal",
                                    "direction",
                                    "skill",
                                    "role",
                                    "time",
                                    "training",
                                )
                            },
                            "risk_tags": ["long_term_training"],
                            "gates": {
                                "candidate_pool_allowed": True,
                                "personalized_ranking_allowed": False,
                                "strong_recommendation_eligible": False,
                                "recommendation_permission_level": "low",
                                "ai_mode": "candidate_explanation",
                            },
                        }
                    ],
                    "missing_competition_ids": [],
                },
            )
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "records": [
                    {
                        "competition_id": "NAT-006",
                        "record_hash": "b" * 64,
                        "valid": False,
                        "reason": "record_hash_changed",
                        "ai_mode": "candidate_explanation",
                    }
                ],
            },
        )

    settings = Settings(mode=ServiceMode.PRODUCTION, api_base="https://internal.example")
    runtime = ToolRuntime(settings, api_transport=httpx.MockTransport(handler))
    try:
        with runtime.grants.bind("competition-grant"):
            context = await competition_get_candidate_context(
                runtime, {"competition_ids": ["NAT-006"]}
            )
            verified = await competition_verify_records(
                runtime,
                {"records": [{"competition_id": "NAT-006", "record_hash": "a" * 64}]},
            )
    finally:
        await runtime.aclose()

    assert context["candidates"][0]["gates"]["personalized_ranking_allowed"] is False
    assert verified["records"][0]["reason"] == "record_hash_changed"
    assert paths == [
        "/internal/mcp/competition/candidate-context",
        "/internal/mcp/competition/verify-records",
    ]
