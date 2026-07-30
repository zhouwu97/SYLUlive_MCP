"""比较用户主动选择的 2 至 4 项赛事。"""

from __future__ import annotations

from typing import Any

from ..hy3.models import SelectedCompetitionComparisonOutput
from ..hy3.prompts import build_messages
from ..result_envelope import ok_envelope
from ..schemas.competition import CompareSelectedCompetitionsInput
from .competition_output_guard import validate_selected_comparison
from .runtime import ToolRuntime


async def compare_selected_competitions(
    runtime: ToolRuntime, raw: dict[str, Any]
) -> dict[str, Any]:
    """按固定维度组织用户选择的赛事事实，不生成总分。"""

    async def operation() -> dict[str, Any]:
        request = runtime.validate_input(CompareSelectedCompetitionsInput, raw)
        context = request.model_dump(mode="json")
        generated = await runtime.client.generate_structured(
            tool_name="compare_selected_competitions",
            messages=build_messages("compare_selected_competitions", context),
            output_model=SelectedCompetitionComparisonOutput,
            reasoning_effort="low",
        )
        expected_ids = [item.competition_id for item in request.competitions]
        validate_selected_comparison(
            expected_ids,
            SelectedCompetitionComparisonOutput.model_validate(generated.data),
        )
        return ok_envelope(
            result=generated.data,
            deterministic_findings={"competition_ids": expected_ids},
            sources=[],
            warnings=[],
            settings=runtime.settings,
            reasoning_effort=generated.reasoning_effort,
        )

    return await runtime.run_core(operation)
