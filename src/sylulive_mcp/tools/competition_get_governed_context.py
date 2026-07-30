"""读取 Go 治理后的公开候选上下文。"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ..config import ServiceMode
from ..result_envelope import result_meta
from ..schemas.tools import CompetitionCandidateContextInput
from .competition_common import demo_competition_facts
from .runtime import ToolRuntime


def _demo_candidate(item: dict[str, Any]) -> dict[str, Any]:
    """将演示事实投影为明确关闭排名与强推荐的候选上下文。"""

    encoded = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "competition_id": item["competition_id"],
        "record_hash": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        "dataset_version": "demo",
        "facts": {
            "title": item["name"],
            "competition_level": "",
            "school_recognition_status": "",
            "school_recognition_grade": item["school_recognition"],
            "competition_rating": item["manual_rating"],
            "manual_rating_reason_public": "",
            "participation_type": "",
            "team_size_min": 0,
            "team_size_max": 0,
            "registration_time_text": "",
            "event_time_text": "",
            "time_status": "pending",
            "major_fit_summary_public": "",
            "evidence_summary_public": "",
            "evidence_subgrade": item["evidence_quality"],
        },
        "match_dimensions": {
            key: "unknown"
            for key in (
                "eligibility",
                "major",
                "college",
                "grade",
                "goal",
                "direction",
                "skill",
                "role",
                "time",
                "training",
            )
        },
        "risk_tags": ["demo_data"],
        "gates": {
            "candidate_pool_allowed": True,
            "personalized_ranking_allowed": False,
            "strong_recommendation_eligible": False,
            "recommendation_permission_level": "low",
            "ai_mode": "candidate_explanation",
        },
    }


async def competition_get_governed_context(
    runtime: ToolRuntime, raw: dict[str, Any]
) -> dict[str, Any]:
    """按输入顺序返回 Go 治理后的公开事实、哈希与权限门。"""

    async def operation() -> dict[str, Any]:
        request = runtime.validate_input(CompetitionCandidateContextInput, raw)
        if runtime.settings.mode is ServiceMode.PRODUCTION:
            response = await runtime.api_client.post(
                "/internal/mcp/competition/candidate-context",
                request.model_dump(mode="json"),
            )
            candidates = list(response.get("candidates") or [])
            missing = list(response.get("missing_competition_ids") or [])
        else:
            by_id = {
                item["competition_id"]: _demo_candidate(item)
                for item in demo_competition_facts(runtime)
            }
            candidates = [
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
            "candidates": candidates,
            "missing_competition_ids": missing,
            "meta": result_meta(),
        }

    return await runtime.run(operation)
