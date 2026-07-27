"""日程工具共享的输入加载逻辑。"""

from __future__ import annotations

from pydantic import ValidationError

from ..errors import CampusMcpError
from ..schemas.schedule import WeeklySchedule
from ..schemas.tools import ScheduleSourceInput
from .runtime import ToolRuntime


def load_schedule(runtime: ToolRuntime, request: ScheduleSourceInput) -> WeeklySchedule:
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
