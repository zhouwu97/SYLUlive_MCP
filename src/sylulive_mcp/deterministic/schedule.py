"""固定日程的时间区间计算。"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any

from ..schemas.schedule import ScheduleConstraints, WeeklySchedule, time_to_minutes


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
    for weekday in range(1, 8):
        blocked[weekday].extend(_sleep_intervals(constraints))
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


def find_free_windows(
    schedule: WeeklySchedule,
    constraints: ScheduleConstraints,
    *,
    minimum_window_minutes: int,
) -> list[dict[str, Any]]:
    """返回满足最小时长的确定性空闲窗口。"""

    windows: list[dict[str, Any]] = []
    for weekday, intervals in _available_intervals(schedule, constraints).items():
        for start, end in intervals:
            minutes = end - start
            if minutes < minimum_window_minutes:
                continue
            windows.append(
                {
                    "weekday": weekday,
                    "date": (schedule.week_start + timedelta(days=weekday - 1)).isoformat(),
                    "start": _format_minutes(start),
                    "end": _format_minutes(end),
                    "minutes": minutes,
                }
            )
    return windows


def _overlaps(first_start: int, first_end: int, second_start: int, second_end: int) -> bool:
    """判断两个同日半开区间是否相交。"""

    return first_start < second_end and second_start < first_end
