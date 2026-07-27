"""政策来源状态与内容哈希复核工具。"""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Any

from ..config import ServiceMode
from ..result_envelope import result_meta
from ..schemas.tools import PolicyGetSourcesInput
from .runtime import ToolRuntime


def _current(effective_to: str | None) -> bool:
    if not effective_to:
        return True
    try:
        return date.fromisoformat(effective_to) >= date.today()
    except ValueError:
        return False


async def policy_get_sources(runtime: ToolRuntime, raw: dict[str, Any]) -> dict[str, Any]:
    """重新读取已检索来源，避免引用被撤回、过期或内容已变化的资料。"""

    async def operation() -> dict[str, Any]:
        request = runtime.validate_input(PolicyGetSourcesInput, raw)
        payload = request.model_dump(mode="json")
        if runtime.settings.mode is ServiceMode.PRODUCTION:
            response = await runtime.api_client.post("/internal/mcp/policy/sources", payload)
            return {
                "status": "ok",
                "sources": list(response.get("sources") or []),
                "missing_source_ids": list(response.get("missing_source_ids") or []),
                "meta": result_meta(),
            }

        documents, missing = runtime.campus_documents.get_sources(request.source_ids)
        sources = [
            {
                "source_id": document.source_id,
                "published": True,
                "current": _current(document.effective_to),
                "content_hash": "sha256:"
                + hashlib.sha256(document.text.encode("utf-8")).hexdigest(),
                "title": document.title,
                "section": document.section_title,
            }
            for document in documents
        ]
        return {
            "status": "ok",
            "sources": sources,
            "missing_source_ids": missing,
            "meta": result_meta(),
        }

    return await runtime.run(operation)
