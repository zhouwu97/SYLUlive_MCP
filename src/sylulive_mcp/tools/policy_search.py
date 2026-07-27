"""政策资料检索工具；不生成解释或行动建议。"""

from __future__ import annotations

from datetime import date
from typing import Any

from ..config import ServiceMode
from ..result_envelope import result_meta
from ..schemas.tools import PolicySearchInput
from .runtime import ToolRuntime


def _is_historical(effective_to: str | None) -> bool:
    if not effective_to:
        return False
    try:
        return date.fromisoformat(effective_to) < date.today()
    except ValueError:
        return False


async def policy_search(runtime: ToolRuntime, raw: dict[str, Any]) -> dict[str, Any]:
    """按多个受限查询返回可引用的政策事实片段。"""

    async def operation() -> dict[str, Any]:
        request = runtime.validate_input(PolicySearchInput, raw)
        payload = request.model_dump(mode="json")
        if runtime.settings.mode is ServiceMode.PRODUCTION:
            response = await runtime.api_client.post("/internal/mcp/policy/search", payload)
            metadata = response.get("meta") if isinstance(response.get("meta"), dict) else {}
            results = response.get("results") if isinstance(response.get("results"), list) else []
            return {
                "status": "ok",
                "results": results[: request.limit],
                "degraded_modes": list(response.get("degraded_modes") or []),
                "meta": result_meta(
                    query_count=len(request.queries),
                    candidate_count=int(metadata.get("candidate_count", len(results))),
                    returned_count=min(len(results), request.limit),
                ),
            }

        candidates: list[tuple[str, Any]] = []
        for query in request.queries:
            for document in runtime.campus_documents.search(
                query, category="policy", max_sources=20
            ):
                candidates.append((query, document))
        unique: dict[str, tuple[str, Any]] = {}
        for query, document in candidates:
            if request.document_types and document.document_type not in request.document_types:
                continue
            historical = _is_historical(document.effective_to)
            if request.historical_mode == "forbid" and historical:
                continue
            if request.historical_mode == "only" and not historical:
                continue
            unique.setdefault(document.source_id, (query, document))

        selected = list(unique.values())[: request.limit]
        results = []
        for query, document in selected:
            exact = float(
                query.casefold()
                in f"{document.title}\n{document.section_title}\n{document.text}".casefold()
            )
            results.append(
                {
                    "source_id": document.source_id,
                    "document_id": None,
                    "chunk_id": None,
                    "title": document.title,
                    "document_type": document.document_type,
                    "department": document.department,
                    "version_status": "historical"
                    if _is_historical(document.effective_to)
                    else "current",
                    "effective_from": document.effective_date,
                    "effective_to": document.effective_to,
                    "section": document.section_title,
                    "text": document.text,
                    "scores": {
                        "exact": exact,
                        "fts": None,
                        "vector": None,
                        "rerank": None,
                    },
                }
            )
        return {
            "status": "ok",
            "results": results,
            "degraded_modes": ["demo_local_retrieval"],
            "meta": result_meta(
                query_count=len(request.queries),
                candidate_count=len(candidates),
                returned_count=len(results),
            ),
        }

    return await runtime.run(operation)
