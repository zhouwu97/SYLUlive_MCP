"""周计划硬约束测试。"""

from __future__ import annotations

from hy3_campus_decision_mcp.deterministic.schedule import build_week_plan, validate_week_plan
from hy3_campus_decision_mcp.schemas.schedule import PlanStudentWeekInput


def test_plan_protects_sleep_and_fixed_events() -> None:
    """本地规划器生成的任务不与课程、睡眠冲突且遵守每日上限。"""

    request = PlanStudentWeekInput.model_validate(
        {
            "schedule": {
                "week_start": "2026-07-27",
                "timezone": "Asia/Shanghai",
                "fixed_events": [{"title": "课程", "weekday": 1, "start": "08:00", "end": "11:40"}],
            },
            "goals": [{"name": "准备蓝桥杯", "weekly_minutes": 360, "priority": "high"}],
            "constraints": {
                "minimum_block_minutes": 30,
                "daily_max_minutes": 120,
                "sleep_start": "23:30",
                "sleep_end": "07:00",
            },
        }
    )
    result = build_week_plan(request.schedule, request)
    assert result["total_scheduled_minutes"] == 360
    assert validate_week_plan(request.schedule, request.constraints, result["plan"]) == []
    assert all(value <= 120 for value in result["daily_assigned_minutes"].values())


def test_plan_reports_unavailable_capacity_without_breaking_constraints() -> None:
    """需求超过可用容量时保留未安排项，而不是侵占睡眠或固定事件。"""

    request = PlanStudentWeekInput.model_validate(
        {
            "schedule": {
                "week_start": "2026-07-27",
                "timezone": "Asia/Shanghai",
                "fixed_events": [],
            },
            "goals": [{"name": "超量目标", "weekly_minutes": 600, "priority": "high"}],
            "constraints": {
                "minimum_block_minutes": 30,
                "daily_max_minutes": 30,
                "sleep_start": "23:30",
                "sleep_end": "07:00",
            },
        }
    )
    result = build_week_plan(request.schedule, request)
    assert result["total_scheduled_minutes"] == 210
    assert result["unscheduled"] == [{"goal": "超量目标", "minutes": 390}]
    assert validate_week_plan(request.schedule, request.constraints, result["plan"]) == []


def test_plan_avoids_stranding_a_remainder_shorter_than_minimum_block() -> None:
    """135 分钟目标应拆成合法时间块，而不是安排 120 分钟并遗留 15 分钟。"""

    request = PlanStudentWeekInput.model_validate(
        {
            "schedule": {
                "week_start": "2026-07-27",
                "timezone": "Asia/Shanghai",
                "fixed_events": [],
            },
            "goals": [{"name": "短余量回归", "weekly_minutes": 135, "priority": "high"}],
            "constraints": {
                "minimum_block_minutes": 30,
                "daily_max_minutes": 120,
                "sleep_start": "23:30",
                "sleep_end": "07:00",
            },
        }
    )

    result = build_week_plan(request.schedule, request)

    assert result["total_scheduled_minutes"] == 135
    assert result["unscheduled"] == []
    assert validate_week_plan(request.schedule, request.constraints, result["plan"]) == []
