"""赛事事实比较所需的最小学生画像。"""

from __future__ import annotations

from pydantic import Field

from .common import StrictInputModel


class StudentProfile(StrictInputModel):
    """仅包含专业、年级和可用时间，不包含任何身份字段。"""

    major: str = Field(min_length=1, max_length=100)
    grade: str = Field(min_length=1, max_length=40)
    weekly_hours: int = Field(ge=0, le=80)
