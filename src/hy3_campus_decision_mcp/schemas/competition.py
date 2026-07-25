"""赛事比较工具的输入模型。"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .common import StrictInputModel


class StudentProfile(StrictInputModel):
    """仅包含用于适配评估的最小学生画像。"""

    major: str = Field(min_length=1, max_length=100)
    grade: str = Field(min_length=1, max_length=40)
    weekly_hours: int = Field(ge=0, le=80)


class CompetitionCandidate(StrictInputModel):
    """自定义赛事对象，第一版仅接受必要的可解释属性。"""

    name: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=80)
    recognition_note: str | None = Field(default=None, max_length=500)
    difficulty: Literal["low", "medium", "high"] | None = None
    recommended_weekly_hours: int | None = Field(default=None, ge=1, le=40)


class CompetitionCompareInput(StrictInputModel):
    """要求目录名模式和自定义对象模式二选一。"""

    competition_names: list[str] | None = None
    competitions: list[CompetitionCandidate] | None = None
    student_profile: StudentProfile

    @model_validator(mode="after")
    def exactly_one_competition_source(self) -> CompetitionCompareInput:
        """同时防止空比较和混合数据来源。"""

        uses_names = self.competition_names is not None
        uses_objects = self.competitions is not None
        if uses_names == uses_objects:
            raise ValueError("Provide exactly one of competition_names or competitions")
        count = len(self.competition_names) if uses_names else len(self.competitions or [])
        if not 2 <= count <= 5:
            raise ValueError("competition_count_invalid")
        if uses_names and any(not name.strip() for name in self.competition_names or []):
            raise ValueError("Competition names must not be empty")
        return self
