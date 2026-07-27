"""纯工具型 MCP 的公开输入与输出模型。"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .academic import AcademicAnalysisInput
from .common import StrictInputModel
from .competition import StudentProfile
from .schedule import ScheduleConstraints, WeeklySchedule


class StrictOutputModel(BaseModel):
    """跨进程输出拒绝未声明字段，防止上游契约静默漂移。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ResultMetadata(StrictOutputModel):
    schema_version: Literal["3"]
    generated_at: datetime


QueryText = Annotated[str, Field(min_length=1, max_length=1_000)]
DocumentType = Annotated[str, Field(min_length=1, max_length=200)]
StableId = Annotated[str, Field(min_length=1, max_length=300)]
Category = Annotated[str, Field(min_length=1, max_length=100)]


class PolicySearchInput(StrictInputModel):
    queries: list[QueryText] = Field(min_length=1, max_length=4)
    document_types: list[DocumentType] = Field(default_factory=list, max_length=10)
    historical_mode: Literal["forbid", "allow", "only"] = "forbid"
    limit: int = Field(default=20, ge=1, le=20)


class PolicyScores(StrictOutputModel):
    exact: float = 0
    fts: float | None = None
    vector: float | None = None
    rerank: float | None = None


class PolicySearchResult(StrictOutputModel):
    source_id: str = Field(min_length=1, max_length=300)
    document_id: int | None = Field(default=None, ge=1)
    chunk_id: int | None = Field(default=None, ge=1)
    title: str = Field(min_length=1, max_length=500)
    document_type: str = Field(max_length=200)
    department: str = Field(max_length=300)
    version_status: Literal["current", "historical", "unknown"]
    effective_from: str | None = Field(default=None, max_length=100)
    effective_to: str | None = Field(default=None, max_length=100)
    section: str = Field(max_length=500)
    text: str = Field(min_length=1, max_length=8_000)
    scores: PolicyScores


class PolicySearchMeta(ResultMetadata):
    query_count: int = Field(ge=1, le=4)
    candidate_count: int = Field(ge=0)
    returned_count: int = Field(ge=0, le=20)


class PolicySearchSuccess(StrictOutputModel):
    status: Literal["ok"]
    results: list[PolicySearchResult] = Field(default_factory=list, max_length=20)
    degraded_modes: list[str] = Field(default_factory=list, max_length=10)
    meta: PolicySearchMeta


class PolicyGetSourcesInput(StrictInputModel):
    source_ids: list[StableId] = Field(min_length=1, max_length=8)


class PolicySourceStatus(StrictOutputModel):
    source_id: str = Field(min_length=1, max_length=300)
    published: bool
    current: bool
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    title: str = Field(min_length=1, max_length=500)
    section: str = Field(max_length=500)


class PolicySourcesSuccess(StrictOutputModel):
    status: Literal["ok"]
    sources: list[PolicySourceStatus] = Field(default_factory=list, max_length=8)
    missing_source_ids: list[str] = Field(default_factory=list, max_length=8)
    meta: ResultMetadata


class CompetitionSearchInput(StrictInputModel):
    query: str | None = Field(default=None, min_length=1, max_length=500)
    categories: list[Category] = Field(default_factory=list, max_length=10)
    limit: int = Field(default=10, ge=1, le=20)


class CompetitionFact(StrictInputModel):
    competition_id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    categories: list[Category] = Field(default_factory=list, max_length=10)
    school_recognition: str = Field(default="not_provided", max_length=100)
    manual_rating: str = Field(default="not_provided", max_length=100)
    eligible: bool | None = None
    major_tags: list[Category] = Field(default_factory=list, max_length=20)
    grade_eligibility: list[Category] = Field(default_factory=list, max_length=20)
    weekly_hours: int = Field(default=6, ge=1, le=40)
    evidence_quality: str = Field(default="unknown", max_length=100)
    source_id: str = Field(min_length=1, max_length=300)


class CompetitionSearchSuccess(StrictOutputModel):
    status: Literal["ok"]
    competitions: list[CompetitionFact] = Field(default_factory=list, max_length=20)
    meta: ResultMetadata


class CompetitionGetDetailsInput(StrictInputModel):
    competition_ids: list[StableId] = Field(min_length=1, max_length=5)


class CompetitionDetailsSuccess(StrictOutputModel):
    status: Literal["ok"]
    competitions: list[CompetitionFact] = Field(default_factory=list, max_length=5)
    missing_competition_ids: list[str] = Field(default_factory=list, max_length=5)
    meta: ResultMetadata


class CompetitionCompareFactsInput(StrictInputModel):
    competition_ids: list[StableId] = Field(min_length=2, max_length=5)
    available_weekly_hours: int | None = Field(default=None, ge=1, le=40)


class DemoCompetitionCompareFactsInput(StrictInputModel):
    competitions: list[CompetitionFact] = Field(min_length=2, max_length=5)
    student_profile: StudentProfile


class ProfileMatch(StrictOutputModel):
    major: bool
    grade: bool | None
    time: bool


class CompetitionComparison(StrictOutputModel):
    competition_id: str
    name: str
    school_recognition: str
    manual_rating: str
    eligible: bool | None
    profile_match: ProfileMatch
    weekly_hours: int
    evidence_quality: str
    source_id: str


class CompetitionCompareSuccess(StrictOutputModel):
    status: Literal["ok"]
    competitions: list[CompetitionComparison] = Field(min_length=2, max_length=5)
    meta: ResultMetadata


class AcademicSummary(StrictOutputModel):
    earned_credits: float
    required_credits: float
    credit_gap: float
    failed_course_count: int
    failed_credits: float
    failed_required_credits: float
    erke_gap: float
    gpa: float | None
    data_completeness: Literal["complete", "partial"]
    data_completeness_percent: float
    unknown_grade_course_count: int
    missing_credit_course_count: int
    failed_courses: list[str] = Field(default_factory=list, max_length=500)


class AcademicSummarySuccess(StrictOutputModel):
    status: Literal["ok"]
    result: AcademicSummary
    warnings: list[str] = Field(default_factory=list, max_length=20)
    meta: ResultMetadata


class AcademicGetSummaryInput(StrictInputModel):
    semester: Literal["current"] = "current"


class AuthorizedAcademicSummary(StrictOutputModel):
    earned_credits: float = Field(ge=0, le=1_000)
    required_credits: float = Field(ge=0, le=1_000)
    failed_course_count: int = Field(ge=0, le=500)
    failed_credits: float = Field(ge=0, le=1_000)
    gpa: float | None = Field(default=None, ge=0, le=10)
    data_completeness: Literal["complete", "partial"]


class AcademicGetSummarySuccess(StrictOutputModel):
    status: Literal["ok"]
    result: AuthorizedAcademicSummary
    meta: ResultMetadata


class DemoScheduleSourceInput(StrictInputModel):
    schedule: WeeklySchedule | None = None
    schedule_path: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def exactly_one_source(self) -> DemoScheduleSourceInput:
        if (self.schedule is None) == (self.schedule_path is None):
            raise ValueError("Provide exactly one of schedule or schedule_path")
        return self


class DemoFindFreeWindowsInput(DemoScheduleSourceInput):
    constraints: ScheduleConstraints = Field(default_factory=ScheduleConstraints)
    minimum_window_minutes: int = Field(default=30, ge=15, le=480)


class FreeWindow(StrictOutputModel):
    weekday: int = Field(ge=1, le=7)
    date: str = Field(min_length=10, max_length=10)
    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")
    minutes: int = Field(ge=15, le=1_440)


class FreeWindowsSuccess(StrictOutputModel):
    status: Literal["ok"]
    windows: list[FreeWindow] = Field(default_factory=list, max_length=200)
    total_free_minutes: int = Field(ge=0, le=10_080)
    meta: ResultMetadata


class FindFreeWindowsInput(StrictInputModel):
    week_start: date
    constraints: ScheduleConstraints = Field(default_factory=ScheduleConstraints)
    minimum_window_minutes: int = Field(default=30, ge=15, le=480)

    @field_validator("week_start")
    @classmethod
    def require_monday(cls, value: date) -> date:
        if value.weekday() != 0:
            raise ValueError("week_start must be a Monday")
        return value


class ProposedPlanItem(StrictInputModel):
    item: str = Field(min_length=1, max_length=200)
    weekday: int = Field(ge=1, le=7)
    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")
    minutes: int = Field(ge=1, le=1_440)

    @field_validator("start", "end")
    @classmethod
    def check_time(cls, value: str) -> str:
        from .schedule import validate_time

        return validate_time(value)


class DemoValidatePlanInput(DemoScheduleSourceInput):
    constraints: ScheduleConstraints = Field(default_factory=ScheduleConstraints)
    plan: list[ProposedPlanItem] = Field(default_factory=list, max_length=200)
    requested_minutes: int | None = Field(default=None, ge=0, le=10_080)


class ValidatePlanInput(StrictInputModel):
    week_start: date
    constraints: ScheduleConstraints = Field(default_factory=ScheduleConstraints)
    plan: list[ProposedPlanItem] = Field(default_factory=list, max_length=200)
    requested_minutes: int | None = Field(default=None, ge=0, le=10_080)

    @field_validator("week_start")
    @classmethod
    def require_monday(cls, value: date) -> date:
        if value.weekday() != 0:
            raise ValueError("week_start must be a Monday")
        return value


class PlanConflict(StrictOutputModel):
    item: str
    reason: str
    code: str


class DailyOverage(StrictOutputModel):
    weekday: int = Field(ge=1, le=7)
    assigned_minutes: int = Field(ge=0)
    limit_minutes: int = Field(ge=1)


class PlanValidationSuccess(StrictOutputModel):
    status: Literal["ok"]
    valid: bool
    conflicts: list[PlanConflict] = Field(default_factory=list, max_length=400)
    daily_overages: list[DailyOverage] = Field(default_factory=list, max_length=7)
    unscheduled_minutes: int = Field(ge=0, le=10_080)
    meta: ResultMetadata


# 仅用于合同类型标注；业务入口仍复用原有经过验证的学业输入。
AcademicCalculateSummaryInput = AcademicAnalysisInput
