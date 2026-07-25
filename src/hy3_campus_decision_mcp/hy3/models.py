"""严格的模型自有叙事输出契约。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StrictOutputModel(BaseModel):
    """拒绝不属于明确模型叙事职责范围的字段。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CampusQuestionOutput(StrictOutputModel):
    """校园问答 Provider 返回的叙事内容。"""

    answer: str = Field(min_length=1, max_length=4_000)
    rationale: str = Field(min_length=1, max_length=4_000)
    source_ids: list[str] = Field(default_factory=list, max_length=20)
    missing_information: list[str] = Field(default_factory=list, max_length=20)


class CompetitionOutput(StrictOutputModel):
    """赛事比较结果对应的叙事内容。"""

    recommendation: str = Field(min_length=1, max_length=4_000)
    rationale: str = Field(min_length=1, max_length=4_000)
    considerations: list[str] = Field(default_factory=list, max_length=20)


class AcademicOutput(StrictOutputModel):
    """对本地计算出的学业结论进行叙事解释。"""

    risk_summary: str = Field(min_length=1, max_length=4_000)
    priority_actions: list[str] = Field(default_factory=list, max_length=20)
    items_to_confirm: list[str] = Field(default_factory=list, max_length=20)


class WeeklyPlanOutput(StrictOutputModel):
    """伴随本地校验周计划的叙事组织内容。"""

    weekly_strategy: str = Field(min_length=1, max_length=4_000)
    priority_order: list[str] = Field(default_factory=list, max_length=20)
    notes: list[str] = Field(default_factory=list, max_length=20)
