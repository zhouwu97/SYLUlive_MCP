"""Strict, model-owned narrative output contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StrictOutputModel(BaseModel):
    """Reject model fields that are not part of the explicitly owned narrative surface."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CampusQuestionOutput(StrictOutputModel):
    """Narrative content returned by the campus-question provider."""

    answer: str = Field(min_length=1, max_length=4_000)
    rationale: str = Field(min_length=1, max_length=4_000)
    source_ids: list[str] = Field(default_factory=list, max_length=20)
    missing_information: list[str] = Field(default_factory=list, max_length=20)


class CompetitionOutput(StrictOutputModel):
    """Narrative content returned for a comparison result."""

    recommendation: str = Field(min_length=1, max_length=4_000)
    rationale: str = Field(min_length=1, max_length=4_000)
    considerations: list[str] = Field(default_factory=list, max_length=20)


class AcademicOutput(StrictOutputModel):
    """Narrative interpretation of locally computed academic findings."""

    risk_summary: str = Field(min_length=1, max_length=4_000)
    priority_actions: list[str] = Field(default_factory=list, max_length=20)
    items_to_confirm: list[str] = Field(default_factory=list, max_length=20)


class WeeklyPlanOutput(StrictOutputModel):
    """Narrative organization accompanying a locally validated weekly schedule."""

    weekly_strategy: str = Field(min_length=1, max_length=4_000)
    priority_order: list[str] = Field(default_factory=list, max_length=20)
    notes: list[str] = Field(default_factory=list, max_length=20)
