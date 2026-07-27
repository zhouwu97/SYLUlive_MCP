"""赛事事实工具共享的演示数据转换。"""

from __future__ import annotations

import hashlib
from typing import Any

from .runtime import ToolRuntime


def demo_competition_facts(runtime: ToolRuntime) -> list[dict[str, Any]]:
    """把本地演示目录转换为稳定、无叙事的赛事事实。"""

    facts: list[dict[str, Any]] = []
    for entry in runtime.competition_catalog.list_entries():
        competition_id = "demo-" + hashlib.sha256(entry.name.encode("utf-8")).hexdigest()[:12]
        facts.append(
            {
                "competition_id": competition_id,
                "name": entry.name,
                "categories": entry.categories,
                "school_recognition": entry.recognition_level,
                "manual_rating": entry.difficulty,
                "eligible": None,
                "major_tags": entry.categories,
                "grade_eligibility": [],
                "weekly_hours": entry.recommended_weekly_hours,
                "evidence_quality": entry.evidence_quality,
                "source_id": f"demo-competition-catalog:{competition_id}",
            }
        )
    return facts
