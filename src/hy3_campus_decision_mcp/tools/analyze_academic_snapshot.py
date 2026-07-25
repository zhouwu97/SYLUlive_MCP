"""学业快照的敏感字段保护与确定性分析工具。"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from ..deterministic.academic import analyze_academic_snapshot as compute_academic_analysis
from ..errors import CampusMcpError
from ..hy3.models import AcademicOutput
from ..hy3.prompts import build_messages
from ..result_envelope import ok_envelope
from ..safety.limits import enforce_input_size
from ..safety.sensitive_fields import reject_sensitive_fields
from ..schemas.academic import AcademicAnalysisInput, AcademicSnapshot
from .runtime import ToolRuntime


async def analyze_academic_snapshot(runtime: ToolRuntime, raw: dict[str, Any]) -> dict[str, Any]:
    """在模型调用前递归拒绝身份和凭据字段，再执行本地学业计算。"""

    async def operation() -> dict[str, Any]:
        enforce_input_size(raw, runtime.settings.max_input_chars)
        inline_snapshot = raw.get("snapshot")
        if inline_snapshot is not None:
            reject_sensitive_fields(inline_snapshot)
        request = runtime.validate_input(AcademicAnalysisInput, raw)
        sources: list[dict[str, Any]] = []
        if request.snapshot is not None:
            snapshot = request.snapshot
        else:
            source_payload, source_path = runtime.load_json_source(request.snapshot_path or "")
            reject_sensitive_fields(source_payload)
            try:
                snapshot = AcademicSnapshot.model_validate(source_payload)
            except ValidationError as error:
                raise CampusMcpError(
                    "invalid_input",
                    "The academic JSON source does not match the required schema.",
                ) from error
            sources.append(
                {
                    "source_id": "academic-snapshot-input",
                    "title": "学业快照输入",
                    "path": source_path,
                    "source_type": "local_input",
                }
            )
        findings = compute_academic_analysis(snapshot)
        generated = await runtime.client.generate_structured(
            tool_name="analyze_academic_snapshot",
            messages=build_messages(
                "analyze_academic_snapshot",
                {
                    "deterministic_findings": findings,
                    "course_count": len(snapshot.courses),
                },
            ),
            output_model=AcademicOutput,
            reasoning_effort="high",
        )
        warnings: list[str] = []
        if findings["data_completeness_percent"] < 100:
            warnings.append("学业快照存在缺失字段，建议在采纳建议前补全数据。")
        return ok_envelope(
            result=generated.data,
            deterministic_findings=findings,
            sources=sources,
            warnings=warnings,
            settings=runtime.settings,
            reasoning_effort=generated.reasoning_effort,
        )

    return await runtime.run_core(operation)
