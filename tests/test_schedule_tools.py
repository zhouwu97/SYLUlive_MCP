"""空闲窗口和计划校验测试。"""

from __future__ import annotations

from sylulive_mcp.tools.schedule_find_free_windows import schedule_find_free_windows
from sylulive_mcp.tools.schedule_validate_plan import schedule_validate_plan


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
