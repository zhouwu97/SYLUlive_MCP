"""解释 Go 已批准且已排序的赛事候选。"""

from __future__ import annotations

from typing import Any

from ..hy3.models import CompetitionCandidateExplanationOutput
from ..hy3.prompts import build_messages
from ..result_envelope import ok_envelope
from ..schemas.competition import ExplainCompetitionCandidatesInput
from .competition_output_guard import validate_candidate_explanation
from .runtime import ToolRuntime


async def explain_competition_candidates(
    runtime: ToolRuntime, raw: dict[str, Any]
) -> dict[str, Any]:
    """只解释候选，不新增赛事、不评分、不重排。"""

    async def operation() -> dict[str, Any]:
        request = runtime.validate_input(ExplainCompetitionCandidatesInput, raw)
        context = request.model_dump(mode="json")
        generated = await runtime.client.generate_structured(
            tool_name="explain_competition_candidates",
            messages=build_messages("explain_competition_candidates", context),
            output_model=CompetitionCandidateExplanationOutput,
            reasoning_effort="low",
        )
        expected_ids = [item.competition_id for item in request.candidates]
        validate_candidate_explanation(
            expected_ids,
            CompetitionCandidateExplanationOutput.model_validate(generated.data),
        )
        return ok_envelope(
            result=generated.data,
            deterministic_findings={
                "competition_ids": expected_ids,
                "rule_order": [item.rule_order for item in request.candidates],
            },
            sources=[],
            warnings=[],
            settings=runtime.settings,
            reasoning_effort=generated.reasoning_effort,
        )

    return await runtime.run_core(operation)
