"""赛事事实检索工具。"""

from __future__ import annotations

from typing import Any

from ..config import ServiceMode
from ..result_envelope import result_meta
from ..schemas.tools import CompetitionSearchInput
from .competition_common import demo_competition_facts
from .runtime import ToolRuntime


async def competition_search(runtime: ToolRuntime, raw: dict[str, Any]) -> dict[str, Any]:
    """检索赛事候选，不对赛事做推荐或排序结论。"""

    async def operation() -> dict[str, Any]:
        request = runtime.validate_input(CompetitionSearchInput, raw)
        if runtime.settings.mode is ServiceMode.PRODUCTION:
            response = await runtime.api_client.post(
                "/internal/mcp/competition/search", request.model_dump(mode="json")
            )
            competitions = list(response.get("competitions") or [])[: request.limit]
        else:
            competitions = demo_competition_facts(runtime)
            if request.query:
                query = request.query.casefold()
                competitions = [
                    item
                    for item in competitions
                    if query in item["name"].casefold()
                    or any(query in category.casefold() for category in item["categories"])
                ]
            if request.categories:
                required = {category.casefold() for category in request.categories}
                competitions = [
                    item
                    for item in competitions
                    if required & {category.casefold() for category in item["categories"]}
                ]
            competitions = competitions[: request.limit]
        return {"status": "ok", "competitions": competitions, "meta": result_meta()}

    return await runtime.run(operation)
