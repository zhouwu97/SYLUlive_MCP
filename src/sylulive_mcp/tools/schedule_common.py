"""日程工具共享的输入加载逻辑。"""

from __future__ import annotations

from pydantic import ValidationError

from ..errors import CampusMcpError, InternalApiError
from ..schemas.schedule import WeeklySchedule
from ..schemas.tools import DemoScheduleSourceInput
from .runtime import ToolRuntime


def load_demo_schedule(runtime: ToolRuntime, request: DemoScheduleSourceInput) -> WeeklySchedule:
    """从内联对象或受限相对路径读取一周固定日程。"""

    if request.schedule is not None:
        return request.schedule
    payload, _ = runtime.load_json_source(request.schedule_path or "")
    try:
        return WeeklySchedule.model_validate(payload)
    except ValidationError as error:
        raise CampusMcpError(
            "invalid_input", "The schedule does not match the required schema."
        ) from error


async def load_authorized_schedule(runtime: ToolRuntime, week_start: str) -> WeeklySchedule:
    """通过当前 Grant 获取指定周的服务端课表，并严格校验响应。"""

    response = await runtime.api_client.post(
        "/internal/mcp/schedule/week", {"week_start": week_start}
    )
    try:
        schedule = WeeklySchedule.model_validate(response.get("schedule"))
    except ValidationError as error:
        raise InternalApiError(
            "internal_api_invalid_response",
            "The internal API returned an invalid schedule.",
        ) from error
    if schedule.week_start.isoformat() != week_start:
        raise InternalApiError(
            "internal_api_invalid_response",
            "The internal API returned a schedule for a different week.",
        )
    return schedule
