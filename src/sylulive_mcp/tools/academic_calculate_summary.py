"""学业快照的确定性汇总工具。"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from ..deterministic.academic import analyze_academic_snapshot
from ..errors import CampusMcpError
from ..result_envelope import result_meta
from ..schemas.academic import AcademicAnalysisInput, AcademicSnapshot
from .runtime import ToolRuntime


async def academic_calculate_summary(runtime: ToolRuntime, raw: dict[str, Any]) -> dict[str, Any]:
    """计算学分、挂科和数据完整度，不输出风险叙事或行动建议。"""

    async def operation() -> dict[str, Any]:
        request = runtime.validate_input(AcademicAnalysisInput, raw)
        if request.snapshot is not None:
            snapshot = request.snapshot
        else:
            source, _ = runtime.load_json_source(request.snapshot_path or "")
            try:
                snapshot = AcademicSnapshot.model_validate(source)
            except ValidationError as error:
                raise CampusMcpError(
                    "invalid_input", "The academic snapshot does not match the required schema."
                ) from error
        findings = analyze_academic_snapshot(snapshot)
        completeness = findings["data_completeness_percent"]
        warnings = [] if completeness == 100 else ["部分课程数据缺失，汇总结果可能不完整。"]
        result = {
            "earned_credits": findings["earned_credits"],
            "required_credits": findings["required_credits"],
            "credit_gap": findings["credit_gap"],
            "failed_course_count": findings["failed_course_count"],
            "failed_credits": findings["failed_credits"],
            "failed_required_credits": findings["failed_required_credits"],
            "erke_gap": findings["erke_gap"],
            "gpa": findings["gpa"],
            "data_completeness": "complete" if completeness == 100 else "partial",
            "data_completeness_percent": completeness,
            "unknown_grade_course_count": findings["unknown_grade_course_count"],
            "missing_credit_course_count": findings["missing_credit_course_count"],
            "failed_courses": findings["failed_courses"],
        }
        return {
            "status": "ok",
            "result": result,
            "warnings": warnings,
            "meta": result_meta(),
        }

    return await runtime.run(operation)
