"""按稳定标识读取赛事事实。"""

from __future__ import annotations

from typing import Any

from ..config import ServiceMode
from ..result_envelope import result_meta
from ..schemas.tools import CompetitionGetDetailsInput
from .competition_common import demo_competition_facts
from .runtime import ToolRuntime


async def competition_get_details(runtime: ToolRuntime, raw: dict[str, Any]) -> dict[str, Any]:
    """读取指定赛事详情，不补全未知字段。"""

    async def operation() -> dict[str, Any]:
        request = runtime.validate_input(CompetitionGetDetailsInput, raw)
        if runtime.settings.mode is ServiceMode.PRODUCTION:
            response = await runtime.api_client.post(
                "/internal/mcp/competition/details", request.model_dump(mode="json")
            )
            competitions = list(response.get("competitions") or [])
            missing = list(response.get("missing_competition_ids") or [])
        else:
            by_id = {item["competition_id"]: item for item in demo_competition_facts(runtime)}
            competitions = [
                by_id[competition_id]
                for competition_id in request.competition_ids
                if competition_id in by_id
            ]
            missing = [
                competition_id
                for competition_id in request.competition_ids
                if competition_id not in by_id
            ]
        return {
            "status": "ok",
            "competitions": competitions,
            "missing_competition_ids": missing,
            "meta": result_meta(),
        }

    return await runtime.run(operation)
