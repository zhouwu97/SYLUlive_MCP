"""周计划的时间区间计算和最终冲突复核。"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any

from ..schemas.schedule import (
    PlanStudentWeekInput,
    ScheduleConstraints,
    WeeklySchedule,
    time_to_minutes,
)

_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _format_minutes(value: int) -> str:
    """把当天分钟数稳定格式化为 `HH:mm`。"""

    return f"{value // 60:02d}:{value % 60:02d}"


def _merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """合并同一天内的重叠或相邻阻塞区间。"""

    merged: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def _sleep_intervals(constraints: ScheduleConstraints) -> list[tuple[int, int]]:
    """把跨午夜睡眠窗口拆成当天起始和结束两个保护区间。"""

    start = time_to_minutes(constraints.sleep_start)
    end = time_to_minutes(constraints.sleep_end)
    if start < end:
        return [(start, end)]
    return [(0, end), (start, 24 * 60)]


def _available_intervals(
    schedule: WeeklySchedule,
    constraints: ScheduleConstraints,
) -> dict[int, list[tuple[int, int]]]:
    """扣除固定事件和睡眠后计算每天可安排区间。"""

    blocked: dict[int, list[tuple[int, int]]] = defaultdict(list)
    sleep = _sleep_intervals(constraints)
    for weekday in range(1, 8):
        blocked[weekday].extend(sleep)
    for event in schedule.fixed_events:
        blocked[event.weekday].append((time_to_minutes(event.start), time_to_minutes(event.end)))

    available: dict[int, list[tuple[int, int]]] = {}
    for weekday in range(1, 8):
        cursor = 0
        day_available: list[tuple[int, int]] = []
        for start, end in _merge_intervals(blocked[weekday]):
            if cursor < start:
                day_available.append((cursor, start))
            cursor = max(cursor, end)
        if cursor < 24 * 60:
            day_available.append((cursor, 24 * 60))
        available[weekday] = day_available
    return available


def _consume_interval(
    intervals: list[tuple[int, int]],
    minutes: int,
) -> tuple[int, int] | None:
    """从当天最早可用区间取出一个确定性时间块。"""

    for index, (start, end) in enumerate(intervals):
        if end - start >= minutes:
            selected = (start, start + minutes)
            if start + minutes == end:
                intervals.pop(index)
            else:
                intervals[index] = (start + minutes, end)
            return selected
    return None


def _next_block_size(
    intervals: list[tuple[int, int]],
    *,
    remaining: int,
    daily_remaining: int,
    minimum_block_minutes: int,
) -> int | None:
    """在可用区间和硬约束内选择一个不会无故留下短余量的时间块。"""

    longest_available = max((end - start for start, end in intervals), default=0)
    block_size = min(120, remaining, daily_remaining, longest_available)
    if block_size < minimum_block_minutes:
        return None

    remainder = remaining - block_size
    # 例如 135 分钟不能先分配 120 分钟再遗留 15 分钟；优先调整为 105+30。
    if 0 < remainder < minimum_block_minutes:
        adjusted_size = remaining - minimum_block_minutes
        if minimum_block_minutes <= adjusted_size <= block_size:
            block_size = adjusted_size
    return block_size


def build_week_plan(
    schedule: WeeklySchedule,
    request: PlanStudentWeekInput,
) -> dict[str, Any]:
    """按优先级、最小块和单日上限生成一个本地可验证计划。"""

    constraints = request.constraints
    available = _available_intervals(schedule, constraints)
    daily_assigned = {weekday: 0 for weekday in range(1, 8)}
    plan: list[dict[str, Any]] = []
    unscheduled: list[dict[str, Any]] = []

    goals = sorted(request.goals, key=lambda goal: _PRIORITY_ORDER[goal.priority])
    for goal in goals:
        remaining = goal.weekly_minutes
        while remaining >= constraints.minimum_block_minutes:
            made_progress = False
            for weekday in range(1, 8):
                daily_remaining = constraints.daily_max_minutes - daily_assigned[weekday]
                if daily_remaining < constraints.minimum_block_minutes:
                    continue
                block_size = _next_block_size(
                    available[weekday],
                    remaining=remaining,
                    daily_remaining=daily_remaining,
                    minimum_block_minutes=constraints.minimum_block_minutes,
                )
                if block_size is None:
                    continue
                selected = _consume_interval(available[weekday], block_size)
                if selected is None:
                    continue
                start, end = selected
                date_value = schedule.week_start + timedelta(days=weekday - 1)
                plan.append(
                    {
                        "goal": goal.name,
                        "priority": goal.priority,
                        "weekday": weekday,
                        "date": date_value.isoformat(),
                        "start": _format_minutes(start),
                        "end": _format_minutes(end),
                        "minutes": block_size,
                    }
                )
                daily_assigned[weekday] += block_size
                remaining -= block_size
                made_progress = True
                if remaining < constraints.minimum_block_minutes:
                    break
            if not made_progress:
                break
        if remaining > 0:
            unscheduled.append({"goal": goal.name, "minutes": remaining})

    total_available = sum(
        min(sum(end - start for start, end in intervals), constraints.daily_max_minutes)
        for intervals in _available_intervals(schedule, constraints).values()
    )
    return {
        "plan": plan,
        "daily_assigned_minutes": daily_assigned,
        "total_requested_minutes": sum(goal.weekly_minutes for goal in request.goals),
        "total_available_minutes": total_available,
        "total_scheduled_minutes": sum(item["minutes"] for item in plan),
        "unscheduled": unscheduled,
    }


def _overlaps(first_start: int, first_end: int, second_start: int, second_end: int) -> bool:
    """判断两个同日半开区间是否相交。"""

    return first_start < second_end and second_start < first_end


def validate_week_plan(
    schedule: WeeklySchedule,
    constraints: ScheduleConstraints,
    plan: list[dict[str, Any]],
) -> list[str]:
    """复核固定事件、睡眠、时长、最小块和任务重叠约束。"""

    issues: list[str] = []
    by_day: dict[int, list[dict[str, Any]]] = defaultdict(list)
    sleep = _sleep_intervals(constraints)
    fixed_by_day: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for event in schedule.fixed_events:
        fixed_by_day[event.weekday].append(
            (time_to_minutes(event.start), time_to_minutes(event.end))
        )

    for item in plan:
        weekday = item.get("weekday")
        if not isinstance(weekday, int) or not 1 <= weekday <= 7:
            issues.append("weekday_invalid")
            continue
        try:
            start = time_to_minutes(str(item["start"]))
            end = time_to_minutes(str(item["end"]))
            minutes = int(item["minutes"])
        except (KeyError, ValueError):
            issues.append("plan_time_invalid")
            continue
        if end <= start or end - start != minutes:
            issues.append("plan_duration_invalid")
        if minutes < constraints.minimum_block_minutes:
            issues.append("plan_block_too_short")
        if any(
            _overlaps(start, end, event_start, event_end)
            for event_start, event_end in fixed_by_day[weekday]
        ):
            issues.append("plan_conflicts_fixed_event")
        if any(_overlaps(start, end, sleep_start, sleep_end) for sleep_start, sleep_end in sleep):
            issues.append("plan_conflicts_sleep")
        by_day[weekday].append(item)

    for _weekday, items in by_day.items():
        if sum(int(item["minutes"]) for item in items) > constraints.daily_max_minutes:
            issues.append("plan_exceeds_daily_max")
        ordered = sorted(items, key=lambda item: time_to_minutes(str(item["start"])))
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if _overlaps(
                time_to_minutes(str(previous["start"])),
                time_to_minutes(str(previous["end"])),
                time_to_minutes(str(current["start"])),
                time_to_minutes(str(current["end"])),
            ):
                issues.append("plan_items_overlap")
    return sorted(set(issues))
