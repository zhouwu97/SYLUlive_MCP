"""周计划工具的输入模型和时间格式校验。"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator, model_validator

from .common import StrictInputModel

_TIME_FORMAT = "%H:%M"


def time_to_minutes(value: str) -> int:
    """把经过格式验证的 `HH:mm` 转为当天分钟数。"""

    parsed = datetime.strptime(value, _TIME_FORMAT)
    return parsed.hour * 60 + parsed.minute


def validate_time(value: str) -> str:
    """验证严格的二十四小时制时间格式。"""

    try:
        datetime.strptime(value, _TIME_FORMAT)
    except ValueError as error:
        raise ValueError("Time must use HH:mm") from error
    if len(value) != 5:
        raise ValueError("Time must use HH:mm")
    return value


class FixedEvent(StrictInputModel):
    """不允许被计划任务占用的固定日程。"""

    title: str = Field(min_length=1, max_length=200)
    weekday: int = Field(ge=1, le=7)
    start: str
    end: str

    @field_validator("start", "end")
    @classmethod
    def check_time_format(cls, value: str) -> str:
        """统一校验开始和结束时间。"""

        return validate_time(value)

    @model_validator(mode="after")
    def reject_cross_midnight(self) -> FixedEvent:
        """第一版的固定事件只能位于同一天。"""

        if time_to_minutes(self.end) <= time_to_minutes(self.start):
            raise ValueError("Fixed events must not cross midnight")
        return self


class WeeklySchedule(StrictInputModel):
    """一周固定课表及其本地时区。"""

    week_start: date
    timezone: str = Field(min_length=1, max_length=100)
    fixed_events: list[FixedEvent] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def check_calendar_rules(self) -> WeeklySchedule:
        """确保周一起始、IANA 时区合法且固定事件不重叠。"""

        if self.week_start.weekday() != 0:
            raise ValueError("week_start must be a Monday in the configured timezone")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError("timezone must be a valid IANA timezone") from error

        by_day: dict[int, list[FixedEvent]] = {}
        for event in self.fixed_events:
            by_day.setdefault(event.weekday, []).append(event)
        for events in by_day.values():
            ordered = sorted(events, key=lambda event: time_to_minutes(event.start))
            for previous, current in zip(ordered, ordered[1:], strict=False):
                if time_to_minutes(current.start) < time_to_minutes(previous.end):
                    raise ValueError("Fixed events must not overlap")
        return self


class ScheduleConstraints(StrictInputModel):
    """局部计划器必须同时满足的硬约束。"""

    minimum_block_minutes: int = Field(default=30, ge=15, le=240)
    daily_max_minutes: int = Field(default=240, ge=15, le=1_000)
    sleep_start: str = "23:30"
    sleep_end: str = "07:00"

    @field_validator("sleep_start", "sleep_end")
    @classmethod
    def check_sleep_time_format(cls, value: str) -> str:
        """睡眠边界使用与固定事件相同的时间格式。"""

        return validate_time(value)

    @model_validator(mode="after")
    def check_sleep_window(self) -> ScheduleConstraints:
        """避免零长度睡眠窗口。"""

        if self.sleep_start == self.sleep_end:
            raise ValueError("sleep_start and sleep_end must differ")
        return self
