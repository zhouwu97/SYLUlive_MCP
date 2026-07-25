"""赛事的四维比较工具。"""

from __future__ import annotations

from typing import Any

from ..deterministic.competition import compare_competitions as compute_comparison
from ..deterministic.evidence import demo_warning
from ..hy3.models import CompetitionOutput
from ..hy3.prompts import build_messages
from ..result_envelope import ok_envelope
from ..schemas.competition import CompetitionCompareInput
from .runtime import ToolRuntime


async def compare_competitions(runtime: ToolRuntime, raw: dict[str, Any]) -> dict[str, Any]:
    """比较 2 至 5 项赛事，不生成不可解释的单一综合分。"""

    async def operation() -> dict[str, Any]:
        request = runtime.validate_input(CompetitionCompareInput, raw)
        if request.competition_names is not None:
            competitions = runtime.competition_catalog.resolve_names(request.competition_names)
            sources = [runtime.competition_catalog.source_metadata()]
        else:
            competitions = runtime.competition_catalog.from_custom(request.competitions or [])
            sources = []
        findings = compute_comparison(competitions, request.student_profile)
        generated = await runtime.client.generate_structured(
            tool_name="compare_competitions",
            messages=build_messages(
                "compare_competitions",
                {
                    "student_profile": request.student_profile.model_dump(mode="json"),
                    "competition_facts": competitions,
                    "deterministic_findings": findings,
                },
            ),
            output_model=CompetitionOutput,
            reasoning_effort="medium",
        )
        return ok_envelope(
            result=generated.data,
            deterministic_findings=findings,
            sources=sources,
            warnings=demo_warning(sources),
            settings=runtime.settings,
            reasoning_effort=generated.reasoning_effort,
        )

    return await runtime.run_core(operation)
