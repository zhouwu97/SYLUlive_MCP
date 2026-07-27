"""固定日程的确定性空闲窗口计算。"""

from __future__ import annotations

from typing import Any

from ..config import ServiceMode
from ..deterministic.schedule import find_free_windows
from ..result_envelope import result_meta
from ..schemas.tools import DemoFindFreeWindowsInput, FindFreeWindowsInput
from .runtime import ToolRuntime
from .schedule_common import load_authorized_schedule, load_demo_schedule


async def schedule_find_free_windows(runtime: ToolRuntime, raw: dict[str, Any]) -> dict[str, Any]:
    """扣除固定事件和睡眠，返回可供 Agent 规划的空闲窗口。"""

    async def operation() -> dict[str, Any]:
        if runtime.settings.mode is ServiceMode.PRODUCTION:
            request = runtime.validate_input(FindFreeWindowsInput, raw)
            schedule = await load_authorized_schedule(runtime, request.week_start.isoformat())
        else:
            request = runtime.validate_input(DemoFindFreeWindowsInput, raw)
            schedule = load_demo_schedule(runtime, request)
        windows = find_free_windows(
            schedule,
            request.constraints,
            minimum_window_minutes=request.minimum_window_minutes,
        )
        return {
            "status": "ok",
            "windows": windows,
            "total_free_minutes": sum(window["minutes"] for window in windows),
            "meta": result_meta(),
        }

    return await runtime.run(operation)
