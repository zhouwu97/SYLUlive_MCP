"""复核候选记录在 Go 目录中的当前有效性。"""

from __future__ import annotations

from typing import Any

from ..config import ServiceMode
from ..result_envelope import result_meta
from ..schemas.tools import CompetitionVerifyRecordsInput
from .competition_common import demo_competition_facts
from .competition_get_candidate_context import _demo_candidate
from .runtime import ToolRuntime


async def competition_verify_records(runtime: ToolRuntime, raw: dict[str, Any]) -> dict[str, Any]:
    """检查记录仍发布、仍在候选池且哈希及 AI 模式未改变。"""

    async def operation() -> dict[str, Any]:
        request = runtime.validate_input(CompetitionVerifyRecordsInput, raw)
        if runtime.settings.mode is ServiceMode.PRODUCTION:
            response = await runtime.api_client.post(
                "/internal/mcp/competition/verify-records",
                request.model_dump(mode="json"),
            )
            records = list(response.get("records") or [])
        else:
            current = {
                item["competition_id"]: _demo_candidate(item)
                for item in demo_competition_facts(runtime)
            }
            records = []
            for record in request.records:
                candidate = current.get(record.competition_id)
                valid = candidate is not None and candidate["record_hash"] == record.record_hash
                records.append(
                    {
                        "competition_id": record.competition_id,
                        "record_hash": candidate["record_hash"] if candidate else "",
                        "valid": valid,
                        "reason": "" if valid else "not_found_or_hash_changed",
                        "ai_mode": candidate["gates"]["ai_mode"] if candidate else "",
                    }
                )
        return {"status": "ok", "records": records, "meta": result_meta()}

    return await runtime.run(operation)
