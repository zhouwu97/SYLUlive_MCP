"""赛事比较工具的输入模型。"""

from __future__ import annotations

from typing import Any, Literal

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


class CapabilitySummary(StrictInputModel):
    name: str = Field(min_length=1, max_length=100)
    verified_count: int = Field(ge=0, le=1_000)
    self_reported_count: int = Field(ge=0, le=1_000)


class CompetitionUserContext(StrictInputModel):
    profile_version: str = Field(min_length=1, max_length=64)
    grade: str = Field(default="", max_length=100)
    college: str = Field(default="", max_length=200)
    major: str = Field(default="", max_length=200)
    goals: list[str] = Field(default_factory=list, max_length=20)
    direction_tags: list[str] = Field(default_factory=list, max_length=20)
    skills: list[CapabilitySummary] = Field(default_factory=list, max_length=100)
    roles: list[CapabilitySummary] = Field(default_factory=list, max_length=50)
    preferred_roles: list[str] = Field(default_factory=list, max_length=20)
    weekly_hours: int = Field(default=0, ge=0, le=80)
    accept_long_term_training: bool = False
    career_direction: str = Field(default="", max_length=200)
    experience_level: str = Field(default="", max_length=100)


class CandidateGates(StrictInputModel):
    candidate_pool_allowed: bool
    personalized_ranking_allowed: bool
    strong_recommendation_eligible: bool
    recommendation_permission_level: Literal["low", "medium", "high"]
    ai_mode: Literal["disabled", "candidate_explanation", "selected_comparison"]


class MatchDimensions(StrictInputModel):
    eligibility: str = Field(max_length=40)
    major: str = Field(max_length=40)
    college: str = Field(max_length=40)
    grade: str = Field(max_length=40)
    goal: str = Field(max_length=40)
    direction: str = Field(max_length=40)
    skill: str = Field(max_length=40)
    role: str = Field(max_length=40)
    time: str = Field(max_length=40)
    training: str = Field(max_length=40)


class ExplainableCompetitionCandidate(StrictInputModel):
    competition_id: str = Field(min_length=1, max_length=64)
    record_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    group_key: Literal["major_match", "college_match", "general_match", "needs_confirmation"]
    rule_order: int = Field(ge=1, le=10_000)
    facts: dict[str, Any] = Field(default_factory=dict, max_length=30)
    match_dimensions: MatchDimensions
    gates: CandidateGates


class ExplainCompetitionCandidatesInput(StrictInputModel):
    mode: Literal["candidate_explanation"]
    question: str | None = Field(default=None, max_length=500)
    user_context: CompetitionUserContext
    candidates: list[ExplainableCompetitionCandidate] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_candidate_order_and_gates(self) -> ExplainCompetitionCandidatesInput:
        ids = [item.competition_id for item in self.candidates]
        orders = [item.rule_order for item in self.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("competition_id_duplicate")
        if orders != sorted(orders) or len(orders) != len(set(orders)):
            raise ValueError("rule_order_invalid")
        if any(
            not item.gates.candidate_pool_allowed or item.gates.ai_mode != "candidate_explanation"
            for item in self.candidates
        ):
            raise ValueError("candidate_gate_invalid")
        return self


class CompareSelectedCompetitionsInput(StrictInputModel):
    mode: Literal["selected_comparison"] = "selected_comparison"
    question: str | None = Field(default=None, max_length=500)
    user_context: CompetitionUserContext
    competitions: list[ExplainableCompetitionCandidate] = Field(min_length=2, max_length=4)

    @model_validator(mode="after")
    def validate_selected_competitions(self) -> CompareSelectedCompetitionsInput:
        ids = [item.competition_id for item in self.competitions]
        if len(ids) != len(set(ids)):
            raise ValueError("competition_id_duplicate")
        if any(not item.gates.candidate_pool_allowed for item in self.competitions):
            raise ValueError("candidate_gate_invalid")
        return self
