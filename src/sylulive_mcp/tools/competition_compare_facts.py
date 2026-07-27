"""赛事事实的确定性并列比较。"""

from __future__ import annotations

from typing import Any

from ..config import ServiceMode
from ..result_envelope import result_meta
from ..schemas.tools import CompetitionCompareFactsInput, DemoCompetitionCompareFactsInput
from .runtime import ToolRuntime

_MAJOR_KEYWORDS = {
    "计算机": {"计算机", "软件", "网络", "人工智能", "数据"},
    "机械": {"机械", "自动化", "智能制造", "车辆"},
    "数学": {"数学", "统计", "数据"},
    "创新创业": {"经管", "管理", "商", "创新", "创业"},
}


def _major_matches(major: str, tags: list[str]) -> bool:
    normalized = major.casefold()
    for tag in tags:
        if tag.casefold() in normalized or normalized in tag.casefold():
            return True
        if any(keyword.casefold() in normalized for keyword in _MAJOR_KEYWORDS.get(tag, set())):
            return True
    return False


async def competition_compare_facts(runtime: ToolRuntime, raw: dict[str, Any]) -> dict[str, Any]:
    """只计算画像匹配并保留原始事实，不生成综合分或推荐。"""

    async def operation() -> dict[str, Any]:
        if runtime.settings.mode is ServiceMode.PRODUCTION:
            request = runtime.validate_input(CompetitionCompareFactsInput, raw)
            response = await runtime.api_client.post(
                "/internal/mcp/competition/compare", request.model_dump(mode="json")
            )
            return {
                "status": "ok",
                "competitions": response.get("competitions"),
                "meta": result_meta(),
            }

        request = runtime.validate_input(DemoCompetitionCompareFactsInput, raw)
        profile = request.student_profile
        comparisons = []
        for competition in request.competitions:
            grade_match = (
                profile.grade in competition.grade_eligibility
                if competition.grade_eligibility
                else None
            )
            comparisons.append(
                {
                    "competition_id": competition.competition_id,
                    "name": competition.name,
                    "school_recognition": competition.school_recognition,
                    "manual_rating": competition.manual_rating,
                    "eligible": competition.eligible,
                    "profile_match": {
                        "major": _major_matches(profile.major, competition.major_tags),
                        "grade": grade_match,
                        "time": profile.weekly_hours >= competition.weekly_hours,
                    },
                    "weekly_hours": competition.weekly_hours,
                    "evidence_quality": competition.evidence_quality,
                    "source_id": competition.source_id,
                }
            )
        return {"status": "ok", "competitions": comparisons, "meta": result_meta()}

    return await runtime.run(operation)
