"""Agent 候选周计划的确定性硬约束校验。"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from ..config import ServiceMode
from ..deterministic.schedule import _overlaps, _sleep_intervals
from ..result_envelope import result_meta
from ..schemas.schedule import time_to_minutes
from ..schemas.tools import DemoValidatePlanInput, ValidatePlanInput
from .runtime import ToolRuntime
from .schedule_common import load_authorized_schedule, load_demo_schedule


async def schedule_validate_plan(runtime: ToolRuntime, raw: dict[str, Any]) -> dict[str, Any]:
    """检查固定事件、睡眠、时长、重叠和单日上限。"""

    async def operation() -> dict[str, Any]:
        if runtime.settings.mode is ServiceMode.PRODUCTION:
            request = runtime.validate_input(ValidatePlanInput, raw)
            schedule = await load_authorized_schedule(runtime, request.week_start.isoformat())
        else:
            request = runtime.validate_input(DemoValidatePlanInput, raw)
            schedule = load_demo_schedule(runtime, request)
        fixed_by_day: dict[int, list[tuple[str, int, int]]] = defaultdict(list)
        for event in schedule.fixed_events:
            fixed_by_day[event.weekday].append(
                (event.title, time_to_minutes(event.start), time_to_minutes(event.end))
            )

        conflicts: list[dict[str, str]] = []
        seen_conflicts: set[tuple[str, str]] = set()
        by_day: dict[int, list[tuple[str, int, int, int]]] = defaultdict(list)
        sleep = _sleep_intervals(request.constraints)

        def add_conflict(item: str, code: str, reason: str) -> None:
            key = (item, code)
            if key not in seen_conflicts:
                conflicts.append({"item": item, "code": code, "reason": reason})
                seen_conflicts.add(key)

        for item in request.plan:
            start = time_to_minutes(item.start)
            end = time_to_minutes(item.end)
            if end <= start or end - start != item.minutes:
                add_conflict(item.item, "duration_invalid", "起止时间与申报时长不一致。")
            if item.minutes < request.constraints.minimum_block_minutes:
                add_conflict(item.item, "block_too_short", "任务时长小于允许的最小时间块。")
            for title, fixed_start, fixed_end in fixed_by_day[item.weekday]:
                if _overlaps(start, end, fixed_start, fixed_end):
                    add_conflict(item.item, "fixed_event_conflict", f"与固定日程“{title}”冲突。")
            if any(
                _overlaps(start, end, sleep_start, sleep_end) for sleep_start, sleep_end in sleep
            ):
                add_conflict(item.item, "sleep_conflict", "占用了受保护的睡眠时间。")
            by_day[item.weekday].append((item.item, start, end, item.minutes))

        daily_overages = []
        for weekday, items in by_day.items():
            assigned = sum(item[3] for item in items)
            if assigned > request.constraints.daily_max_minutes:
                daily_overages.append(
                    {
                        "weekday": weekday,
                        "assigned_minutes": assigned,
                        "limit_minutes": request.constraints.daily_max_minutes,
                    }
                )
            ordered = sorted(items, key=lambda item: item[1])
            for previous, current in zip(ordered, ordered[1:], strict=False):
                if _overlaps(previous[1], previous[2], current[1], current[2]):
                    add_conflict(current[0], "plan_item_overlap", f"与计划项“{previous[0]}”重叠。")

        scheduled_minutes = sum(item.minutes for item in request.plan)
        unscheduled = max((request.requested_minutes or scheduled_minutes) - scheduled_minutes, 0)
        return {
            "status": "ok",
            "valid": not conflicts and not daily_overages and unscheduled == 0,
            "conflicts": conflicts,
            "daily_overages": daily_overages,
            "unscheduled_minutes": unscheduled,
            "meta": result_meta(),
        }

    return await runtime.run(operation)
