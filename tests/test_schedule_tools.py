"""空闲窗口和计划校验测试。"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from sylulive_mcp.config import ServiceMode, Settings
from sylulive_mcp.tools.runtime import ToolRuntime
from sylulive_mcp.tools.schedule_find_free_windows import schedule_find_free_windows
from sylulive_mcp.tools.schedule_validate_plan import schedule_validate_plan

PROJECT_ROOT = Path(__file__).resolve().parents[1]


async def test_free_windows_exclude_sleep_and_fixed_events(demo_runtime) -> None:
    result = await schedule_find_free_windows(
        demo_runtime,
        {"schedule_path": "schedules/sample_week.json", "minimum_window_minutes": 30},
    )
    assert result["status"] == "ok"
    monday = [window for window in result["windows"] if window["weekday"] == 1]
    assert [(window["start"], window["end"]) for window in monday] == [
        ("07:00", "08:00"),
        ("11:40", "23:30"),
    ]


async def test_plan_validation_reports_conflict_and_unscheduled_time(demo_runtime) -> None:
    result = await schedule_validate_plan(
        demo_runtime,
        {
            "schedule_path": "schedules/sample_week.json",
            "plan": [
                {
                    "item": "准备竞赛",
                    "weekday": 3,
                    "start": "15:00",
                    "end": "16:00",
                    "minutes": 60,
                }
            ],
            "requested_minutes": 120,
        },
    )
    assert result["status"] == "ok"
    assert result["valid"] is False
    assert result["conflicts"][0]["code"] == "fixed_event_conflict"
    assert result["unscheduled_minutes"] == 60


async def test_valid_plan_passes(demo_runtime) -> None:
    result = await schedule_validate_plan(
        demo_runtime,
        {
            "schedule_path": "schedules/sample_week.json",
            "plan": [
                {
                    "item": "准备竞赛",
                    "weekday": 1,
                    "start": "12:00",
                    "end": "13:00",
                    "minutes": 60,
                }
            ],
            "requested_minutes": 60,
        },
    )
    assert result["valid"] is True


async def test_production_schedule_is_fetched_by_week_and_grant() -> None:
    schedule = json.loads(
        (PROJECT_ROOT / "examples" / "schedules" / "sample_week.json").read_text(encoding="utf-8")
    )
    captured: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        assert request.headers["Authorization"] == "Bearer schedule-grant"
        return httpx.Response(200, json={"status": "ok", "schedule": schedule})

    settings = Settings(mode=ServiceMode.PRODUCTION, api_base="https://internal.example")
    runtime = ToolRuntime(settings, api_transport=httpx.MockTransport(handler))
    try:
        with runtime.grants.bind("schedule-grant"):
            windows = await schedule_find_free_windows(
                runtime,
                {"week_start": schedule["week_start"], "minimum_window_minutes": 30},
            )
            validation = await schedule_validate_plan(
                runtime,
                {
                    "week_start": schedule["week_start"],
                    "plan": [
                        {
                            "item": "准备竞赛",
                            "weekday": 1,
                            "start": "12:00",
                            "end": "13:00",
                            "minutes": 60,
                        }
                    ],
                    "requested_minutes": 60,
                },
            )
    finally:
        await runtime.aclose()

    assert windows["status"] == "ok"
    assert validation["valid"] is True
    assert captured == [
        {"week_start": schedule["week_start"]},
        {"week_start": schedule["week_start"]},
    ]
