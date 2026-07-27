"""经 Go 授权数据源读取学业最小汇总。"""

from __future__ import annotations

from typing import Any

from ..result_envelope import result_meta
from ..schemas.tools import AcademicGetSummaryInput
from .runtime import ToolRuntime


async def academic_get_summary(runtime: ToolRuntime, raw: dict[str, Any]) -> dict[str, Any]:
    """仅按当前 Grant 获取学业汇总，不接收课程或成绩明细。"""

    async def operation() -> dict[str, Any]:
        request = runtime.validate_input(AcademicGetSummaryInput, raw)
        response = await runtime.api_client.post(
            "/internal/mcp/academic/summary", request.model_dump(mode="json")
        )
        return {
            "status": "ok",
            "result": response.get("result"),
            "meta": result_meta(),
        }

    return await runtime.run(operation)
