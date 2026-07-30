"""赛事解释输出的 ID、顺序、来源与措辞门禁。"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..errors import Hy3ProviderError
from ..hy3.models import (
    CompetitionCandidateExplanationOutput,
    CompetitionExplanationReason,
    SelectedCompetitionComparisonOutput,
)

ALLOWED_SOURCE_FIELDS = frozenset(
    {
        "competition_level",
        "school_recognition_status",
        "school_recognition_grade",
        "competition_rating",
        "participation_type",
        "team_size_min",
        "team_size_max",
        "registration_time_text",
        "event_time_text",
        "time_status",
        "manual_rating_reason_public",
        "major_fit_summary_public",
        "evidence_summary_public",
        "evidence_subgrade",
        "risk_tags",
        "match_dimensions",
        "gates",
    }
)
FORBIDDEN_LANGUAGE = (
    "最适合",
    "强烈推荐",
    "获奖概率",
    "成功率",
    "综合分",
    "top 1",
    "top1",
)
DATE_PATTERN = re.compile(r"20\d{2}(?:[-/.年]\d{1,2})")
PROBABILITY_PATTERN = re.compile(r"\d+(?:\.\d+)?%")


def _validate_text(value: str) -> None:
    normalized = value.strip().casefold()
    if any(term in normalized for term in FORBIDDEN_LANGUAGE):
        raise Hy3ProviderError(
            "hy3_competition_language_invalid",
            "Hy3 used language outside the candidate explanation boundary.",
        )
    if DATE_PATTERN.search(normalized) or PROBABILITY_PATTERN.search(normalized):
        raise Hy3ProviderError(
            "hy3_competition_fact_invalid",
            "Hy3 introduced a date or probability that was not an allowed output.",
        )


def _validate_reasons(reasons: Iterable[CompetitionExplanationReason]) -> None:
    for reason in reasons:
        _validate_text(reason.text)
        if not set(reason.source_fields).issubset(ALLOWED_SOURCE_FIELDS):
            raise Hy3ProviderError(
                "hy3_competition_source_field_invalid",
                "Hy3 referenced a field outside the public candidate context.",
            )


def validate_candidate_explanation(
    expected_ids: list[str], output: CompetitionCandidateExplanationOutput
) -> None:
    """候选解释必须覆盖同一 ID 集合并保持输入顺序。"""

    actual_ids = [item.competition_id for item in output.items]
    if actual_ids != expected_ids or len(actual_ids) != len(set(actual_ids)):
        raise Hy3ProviderError(
            "hy3_competition_ids_invalid",
            "Hy3 added, removed, duplicated, or reordered a competition.",
        )
    _validate_text(output.summary)
    for item in output.items:
        _validate_text(item.core_reason)
        _validate_reasons([*item.reasons, *item.cautions])
        for question in item.questions_to_confirm:
            _validate_text(question)


def validate_selected_comparison(
    expected_ids: list[str], output: SelectedCompetitionComparisonOutput
) -> None:
    """主动对比必须逐项覆盖用户选择且保持选择顺序。"""

    actual_ids = [item.competition_id for item in output.items]
    if actual_ids != expected_ids or len(actual_ids) != len(set(actual_ids)):
        raise Hy3ProviderError(
            "hy3_competition_ids_invalid",
            "Hy3 changed the selected competition set or order.",
        )
    _validate_text(output.summary)
    for item in output.items:
        _validate_reasons([*item.observations, *item.cautions])
        for question in item.questions_to_confirm:
            _validate_text(question)
