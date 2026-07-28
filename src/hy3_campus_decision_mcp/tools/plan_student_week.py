"""受硬约束保护的周计划工具。"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from ..deterministic.schedule import build_week_plan, validate_week_plan
from ..errors import CampusMcpError
from ..hy3.models import WeeklyPlanOutput
from ..hy3.prompts import build_messages
from ..result_envelope import ok_envelope
from ..schemas.schedule import PlanStudentWeekInput, WeeklySchedule
from .runtime import ToolRuntime


async def plan_student_week(runtime: ToolRuntime, raw: dict[str, Any]) -> dict[str, Any]:
    """先由本地算法分配时间，再让 Hy3 只组织优先级和执行建议。"""

    async def operation() -> dict[str, Any]:
        request = runtime.validate_input(PlanStudentWeekInput, raw)
        sources: list[dict[str, Any]] = []
        if request.schedule is not None:
            schedule = request.schedule
        else:
            source_payload, source_path = runtime.load_json_source(request.schedule_path or "")
            try:
                schedule = WeeklySchedule.model_validate(source_payload)
            except ValidationError as error:
                raise CampusMcpError(
                    "invalid_input",
                    "The schedule JSON source does not match the required schema.",
                ) from error
            sources.append(
                {
                    "source_id": "schedule-input",
                    "title": "课表输入",
                    "path": source_path,
                    "source_type": "local_input",
                }
            )
        findings = build_week_plan(schedule, request)
        validation_issues = validate_week_plan(schedule, request.constraints, findings["plan"])
        if validation_issues:
            raise CampusMcpError(
                "plan_validation_failed",
                "The locally generated plan did not satisfy its hard constraints.",
            )
        generated = await runtime.client.generate_structured(
            tool_name="plan_student_week",
            messages=build_messages(
                "plan_student_week",
                {
                    "goals": [goal.model_dump(mode="json") for goal in request.goals],
                    "constraints": request.constraints.model_dump(mode="json"),
                    "deterministic_plan": findings["plan"],
                    "unscheduled": findings["unscheduled"],
                },
            ),
            output_model=WeeklyPlanOutput,
            reasoning_effort="high",
        )
        warnings: list[str] = []
        if findings["unscheduled"]:
            warnings.append("部分目标无法在当前硬约束内安排，未占用睡眠或固定事件。")
        return ok_envelope(
            result=generated.data,
            deterministic_findings=findings,
            sources=sources,
            warnings=warnings,
            settings=runtime.settings,
            reasoning_effort=generated.reasoning_effort,
        )

    return await runtime.run_core(operation)
