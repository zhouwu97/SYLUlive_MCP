"""MCP 工具的公开输入、输出和版本化 Schema 契约。"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from .config import ToolProfile
from .constants import MCP_CONTRACT_VERSION
from .hy3.models import (
    AcademicOutput,
    CampusQuestionOutput,
    CompetitionCandidateExplanationOutput,
    CompetitionOutput,
    SelectedCompetitionComparisonOutput,
    WeeklyPlanOutput,
)
from .schemas import (
    AcademicAnalysisInput,
    CampusQuestionInput,
    CompareSelectedCompetitionsInput,
    CompetitionCompareInput,
    ExplainCompetitionCandidatesInput,
    PlanStudentWeekInput,
)
from .tools.analyze_academic_snapshot import analyze_academic_snapshot
from .tools.answer_campus_question import answer_campus_question
from .tools.compare_competitions import compare_competitions
from .tools.compare_selected_competitions import compare_selected_competitions
from .tools.explain_competition_candidates import explain_competition_candidates
from .tools.plan_student_week import plan_student_week
from .tools.runtime import ToolRuntime

RawToolHandler = Callable[[ToolRuntime, dict[str, Any]], Awaitable[dict[str, Any]]]


class StrictContractModel(BaseModel):
    """跨进程传输的协议对象必须拒绝未声明字段。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ModelMetadata(StrictContractModel):
    provider: Literal["hy3"]
    model: str = Field(min_length=1, max_length=200)
    mode: Literal["live", "fixture"]
    reasoning_effort: str = Field(min_length=1, max_length=100)


class ResultMetadata(StrictContractModel):
    schema_version: Literal["2"]
    generated_at: datetime


class SourceMetadata(StrictContractModel):
    source_id: str = Field(min_length=1, max_length=300)
    title: str = Field(min_length=1, max_length=500)
    path: str = Field(min_length=1, max_length=1_000)
    source_type: str = Field(min_length=1, max_length=100)
    official: bool | None = None
    effective_date: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=100)
    document_type: str | None = Field(default=None, max_length=200)
    department: str | None = Field(default=None, max_length=300)
    effective_to: str | None = Field(default=None, max_length=100)
    section_title: str | None = Field(default=None, max_length=500)


class ErrorEnvelope(StrictContractModel):
    status: Literal["error"]
    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=500)


class CampusQuestionFindings(StrictContractModel):
    retrieved_source_count: int = Field(ge=0, le=20)


class CompetitionRecognition(StrictContractModel):
    recognized: bool
    level: str = Field(min_length=1, max_length=100)
    note: str = Field(min_length=1, max_length=500)


class CompetitionHumanEvaluation(StrictContractModel):
    difficulty: str = Field(min_length=1, max_length=100)
    teamwork: str = Field(min_length=1, max_length=100)
    portfolio_value: str = Field(min_length=1, max_length=100)
    note: str = Field(min_length=1, max_length=500)


class CompetitionAlignment(StrictContractModel):
    level: Literal["low", "medium", "high"]
    matched_categories: list[str] = Field(default_factory=list, max_length=20)


class CompetitionTimeAlignment(StrictContractModel):
    level: Literal["low", "medium", "high"]
    available_weekly_hours: int = Field(ge=0, le=80)
    recommended_weekly_hours: int = Field(ge=1, le=40)


class CompetitionStudentFit(StrictContractModel):
    major_alignment: CompetitionAlignment
    time_alignment: CompetitionTimeAlignment


class CompetitionEvidenceQuality(StrictContractModel):
    level: str = Field(min_length=1, max_length=100)
    source_type: str = Field(min_length=1, max_length=100)
    official: bool


class CompetitionComparison(StrictContractModel):
    name: str = Field(min_length=1, max_length=200)
    school_recognition: CompetitionRecognition
    human_evaluation: CompetitionHumanEvaluation
    student_fit: CompetitionStudentFit
    evidence_quality: CompetitionEvidenceQuality


class CompetitionFindings(StrictContractModel):
    comparisons: list[CompetitionComparison] = Field(min_length=2, max_length=5)


class CandidateExplanationFindings(StrictContractModel):
    competition_ids: list[str] = Field(min_length=1, max_length=20)
    rule_order: list[int] = Field(min_length=1, max_length=20)


class SelectedComparisonFindings(StrictContractModel):
    competition_ids: list[str] = Field(min_length=2, max_length=4)


class AcademicFindings(StrictContractModel):
    failed_course_count: int = Field(ge=0, le=500)
    failed_required_credits: float = Field(ge=0, le=1_000)
    earned_credits: float = Field(ge=0, le=1_000)
    credit_gap: float = Field(ge=0, le=1_000)
    erke_gap: float = Field(ge=0, le=1_000)
    unknown_grade_course_count: int = Field(ge=0, le=500)
    missing_credit_course_count: int = Field(ge=0, le=500)
    data_completeness_percent: float = Field(ge=0, le=100)
    failed_courses: list[str] = Field(default_factory=list, max_length=500)


class PlanItem(StrictContractModel):
    goal: str = Field(min_length=1, max_length=200)
    priority: Literal["high", "medium", "low"]
    weekday: int = Field(ge=1, le=7)
    date: str = Field(min_length=10, max_length=10)
    start: str = Field(min_length=5, max_length=5)
    end: str = Field(min_length=5, max_length=5)
    minutes: int = Field(ge=15, le=1_000)


class UnscheduledGoal(StrictContractModel):
    goal: str = Field(min_length=1, max_length=200)
    minutes: int = Field(ge=1, le=10_080)


class WeekPlanFindings(StrictContractModel):
    plan: list[PlanItem] = Field(default_factory=list, max_length=350)
    daily_assigned_minutes: dict[int, int] = Field(min_length=7, max_length=7)
    total_requested_minutes: int = Field(ge=0, le=504_000)
    total_available_minutes: int = Field(ge=0, le=10_080)
    total_scheduled_minutes: int = Field(ge=0, le=504_000)
    unscheduled: list[UnscheduledGoal] = Field(default_factory=list, max_length=50)


class CampusQuestionSuccessEnvelope(StrictContractModel):
    status: Literal["ok"]
    result: CampusQuestionOutput
    deterministic_findings: CampusQuestionFindings
    sources: list[SourceMetadata] = Field(default_factory=list, max_length=20)
    warnings: list[str] = Field(default_factory=list, max_length=20)
    model: ModelMetadata
    meta: ResultMetadata


class CompetitionSuccessEnvelope(StrictContractModel):
    status: Literal["ok"]
    result: CompetitionOutput
    deterministic_findings: CompetitionFindings
    sources: list[SourceMetadata] = Field(default_factory=list, max_length=20)
    warnings: list[str] = Field(default_factory=list, max_length=20)
    model: ModelMetadata
    meta: ResultMetadata


class CandidateExplanationSuccessEnvelope(StrictContractModel):
    status: Literal["ok"]
    result: CompetitionCandidateExplanationOutput
    deterministic_findings: CandidateExplanationFindings
    sources: list[SourceMetadata] = Field(default_factory=list, max_length=0)
    warnings: list[str] = Field(default_factory=list, max_length=20)
    model: ModelMetadata
    meta: ResultMetadata


class SelectedComparisonSuccessEnvelope(StrictContractModel):
    status: Literal["ok"]
    result: SelectedCompetitionComparisonOutput
    deterministic_findings: SelectedComparisonFindings
    sources: list[SourceMetadata] = Field(default_factory=list, max_length=0)
    warnings: list[str] = Field(default_factory=list, max_length=20)
    model: ModelMetadata
    meta: ResultMetadata


class AcademicSuccessEnvelope(StrictContractModel):
    status: Literal["ok"]
    result: AcademicOutput
    deterministic_findings: AcademicFindings
    sources: list[SourceMetadata] = Field(default_factory=list, max_length=20)
    warnings: list[str] = Field(default_factory=list, max_length=20)
    model: ModelMetadata
    meta: ResultMetadata


class WeeklyPlanSuccessEnvelope(StrictContractModel):
    status: Literal["ok"]
    result: WeeklyPlanOutput
    deterministic_findings: WeekPlanFindings
    sources: list[SourceMetadata] = Field(default_factory=list, max_length=20)
    warnings: list[str] = Field(default_factory=list, max_length=20)
    model: ModelMetadata
    meta: ResultMetadata


CampusQuestionResponse = Annotated[
    CampusQuestionSuccessEnvelope | ErrorEnvelope, Field(discriminator="status")
]
CompetitionResponse = Annotated[
    CompetitionSuccessEnvelope | ErrorEnvelope, Field(discriminator="status")
]
CandidateExplanationResponse = Annotated[
    CandidateExplanationSuccessEnvelope | ErrorEnvelope, Field(discriminator="status")
]
SelectedComparisonResponse = Annotated[
    SelectedComparisonSuccessEnvelope | ErrorEnvelope, Field(discriminator="status")
]
AcademicResponse = Annotated[AcademicSuccessEnvelope | ErrorEnvelope, Field(discriminator="status")]
WeeklyPlanResponse = Annotated[
    WeeklyPlanSuccessEnvelope | ErrorEnvelope, Field(discriminator="status")
]


@dataclass(frozen=True)
class ToolContract:
    """工具名、公开 Schema 与业务处理器的唯一注册来源。"""

    name: str
    description: str
    input_model: type[BaseModel]
    output_model: Any
    handler: RawToolHandler

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.input_model.model_json_schema()

    @property
    def output_schema(self) -> dict[str, Any]:
        schema = TypeAdapter(self.output_model).json_schema()
        # MCP 的 Tool 输出必须是对象；`oneOf` 仍保留成功/错误信封的严格分支。
        schema["type"] = "object"
        return schema

    @property
    def schema_sha256(self) -> str:
        return schema_digest(self.input_schema, self.output_schema)


TOOL_CONTRACTS: dict[str, ToolContract] = {
    "answer_campus_question": ToolContract(
        name="answer_campus_question",
        description="基于本地校园文档回答问题，并返回可核验来源。",
        input_model=CampusQuestionInput,
        output_model=CampusQuestionResponse,
        handler=answer_campus_question,
    ),
    "compare_competitions": ToolContract(
        name="compare_competitions",
        description="在学校认定、人工评价、学生适配和证据质量四维比较 2 至 5 项赛事。",
        input_model=CompetitionCompareInput,
        output_model=CompetitionResponse,
        handler=compare_competitions,
    ),
    "explain_competition_candidates": ToolContract(
        name="explain_competition_candidates",
        description="只解释 Go 已批准且已排序的赛事候选，不新增、不评分、不重排。",
        input_model=ExplainCompetitionCandidatesInput,
        output_model=CandidateExplanationResponse,
        handler=explain_competition_candidates,
    ),
    "compare_selected_competitions": ToolContract(
        name="compare_selected_competitions",
        description="比较用户主动选择的 2 至 4 项赛事，不生成综合分。",
        input_model=CompareSelectedCompetitionsInput,
        output_model=SelectedComparisonResponse,
        handler=compare_selected_competitions,
    ),
    "analyze_academic_snapshot": ToolContract(
        name="analyze_academic_snapshot",
        description="分析非身份化学业快照，计算学分、挂科和数据完整度。",
        input_model=AcademicAnalysisInput,
        output_model=AcademicResponse,
        handler=analyze_academic_snapshot,
    ),
    "plan_student_week": ToolContract(
        name="plan_student_week",
        description="在固定事件、睡眠、最小时间块和每日上限内安排一周目标。",
        input_model=PlanStudentWeekInput,
        output_model=WeeklyPlanResponse,
        handler=plan_student_week,
    ),
}

# 这些摘要由 diaofenyuan 的 Go Runtime 固定校验；修改任一 Schema 时必须
# 同步升级契约版本并同时更新两端，而不能仅修改状态响应。
SYLULIVE_RUNTIME_TOOL_NAMES = (
    "compare_competitions",
    "explain_competition_candidates",
    "compare_selected_competitions",
    "analyze_academic_snapshot",
    "plan_student_week",
)
PINNED_TOOL_CONTRACTS = {
    "compare_competitions": {
        "schema_sha256": "183668200d82156e6385342d747d229e5ab8fe49ba4351afaf8fccc9c896905c",
    },
    "explain_competition_candidates": {
        "schema_sha256": "869bed351400771f7272b5c05b97d2c20875c7ddff0db65cb9d064b5c1f84721",
    },
    "compare_selected_competitions": {
        "schema_sha256": "b8e151f2e964f96dcbc5d533632da63f5adf9b7106f681d861edb7f05cc0b463",
    },
    "analyze_academic_snapshot": {
        "schema_sha256": "fc50ff6b196c409d59df53df777f49b265fd4bfa66e34969e5787527a38fad23",
    },
    "plan_student_week": {
        "schema_sha256": "0cb4a9c774ea6799b8f95945d89c21195c0cb228315ab73fd849259814cc7518",
    },
}


def contracts_for_profile(profile: ToolProfile) -> dict[str, ToolContract]:
    """按便携或生产运行时配置返回实际注册的工具。"""

    if profile is ToolProfile.SYLULIVE_RUNTIME:
        return {name: TOOL_CONTRACTS[name] for name in SYLULIVE_RUNTIME_TOOL_NAMES}
    return TOOL_CONTRACTS


NON_CONTRACT_KEYS = frozenset({"title", "description", "examples"})


def normalize_schema(value: Any) -> Any:
    """移除展示性字段，保留所有影响输入和输出语义的 Schema 约束。"""

    if isinstance(value, dict):
        return {
            key: normalize_schema(child)
            for key, child in sorted(value.items())
            if key not in NON_CONTRACT_KEYS
        }
    if isinstance(value, list):
        return [normalize_schema(child) for child in value]
    return value


def schema_digest(input_schema: dict[str, Any], output_schema: dict[str, Any]) -> str:
    """使用可复现 JSON 编码生成单个工具的输入/输出契约摘要。"""

    normalized = normalize_schema({"input_schema": input_schema, "output_schema": output_schema})
    encoded = json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_contract_manifest() -> dict[str, Any]:
    """生成应提交到仓库的工具契约清单。"""

    return {
        "contract_version": MCP_CONTRACT_VERSION,
        "tools": {
            name: {
                "schema_sha256": contract.schema_sha256,
                "input_schema": contract.input_schema,
                "output_schema": contract.output_schema,
            }
            for name, contract in sorted(TOOL_CONTRACTS.items())
        },
    }


def committed_manifest_path() -> Path:
    """返回版本化清单在仓库中的固定位置。"""

    return Path(__file__).resolve().parents[2] / "assets" / "contracts" / "sylulive-hy3-v2.json"
