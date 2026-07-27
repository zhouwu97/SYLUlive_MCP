"""固定日程的确定性空闲窗口计算。"""

from __future__ import annotations

from typing import Any

from ..deterministic.schedule import find_free_windows
from ..result_envelope import result_meta
from ..schemas.tools import FindFreeWindowsInput
from .runtime import ToolRuntime
from .schedule_common import load_schedule


async def schedule_find_free_windows(runtime: ToolRuntime, raw: dict[str, Any]) -> dict[str, Any]:
    """扣除固定事件和睡眠，返回可供 Agent 规划的空闲窗口。"""

    async def operation() -> dict[str, Any]:
        request = runtime.validate_input(FindFreeWindowsInput, raw)
        schedule = load_schedule(runtime, request)
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
