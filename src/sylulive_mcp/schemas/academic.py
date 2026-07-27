"""学业快照工具的输入模型。"""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from .common import StrictInputModel


class CourseRecord(StrictInputModel):
    """单门课程的最小非身份化记录。"""

    course_name: str = Field(min_length=1, max_length=200)
    credits: float | None = Field(default=None, ge=0, le=100)
    is_required: bool = False
    grade: str | float | None = None
    passed: bool | None = None

    @field_validator("grade")
    @classmethod
    def limit_text_grade(cls, value: str | float | None) -> str | float | None:
        """限制文字成绩长度，同时保留数值成绩的计算语义。"""

        if isinstance(value, str) and len(value) > 100:
            raise ValueError("grade text is too long")
        return value


class AcademicSnapshot(StrictInputModel):
    """本地计算所需的课程、学分和二课进度数据。"""

    courses: list[CourseRecord] = Field(default_factory=list, max_length=500)
    earned_credits: float = Field(ge=0, le=1_000)
    required_credits: float = Field(ge=0, le=1_000)
    erke_earned: float = Field(ge=0, le=1_000)
    erke_required: float = Field(ge=0, le=1_000)
    gpa: float | None = Field(default=None, ge=0, le=10)


class AcademicAnalysisInput(StrictInputModel):
    """要求内联快照和相对文件路径二选一。"""

    snapshot: AcademicSnapshot | None = None
    snapshot_path: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def exactly_one_source(self) -> AcademicAnalysisInput:
        """禁止隐式偏好某个来源，确保输入行为可预测。"""

        has_inline = self.snapshot is not None
        has_path = self.snapshot_path is not None
        if has_inline == has_path:
            raise ValueError("Provide exactly one of snapshot or snapshot_path")
        return self
