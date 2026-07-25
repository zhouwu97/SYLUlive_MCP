"""赛事比较的四维可解释计算。"""

from __future__ import annotations

from typing import Any

from ..schemas.competition import StudentProfile

_MAJOR_KEYWORDS = {
    "计算机": {"计算机", "软件", "网络", "人工智能", "数据"},
    "机械": {"机械", "自动化", "智能制造", "车辆"},
    "数学": {"数学", "统计", "数据"},
    "创新创业": {"经管", "管理", "商", "创新", "创业"},
}


def _fit_level(score: int) -> str:
    """把局部适配评分转成可读等级，不形成综合分。"""

    if score >= 4:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def _major_alignment(profile: StudentProfile, categories: list[str]) -> tuple[int, list[str]]:
    """根据显式类别和专业关键词计算单独的专业匹配维度。"""

    major = profile.major.lower()
    matched_categories = [
        category
        for category in categories
        if any(keyword in major for keyword in _MAJOR_KEYWORDS.get(category, set()))
    ]
    if matched_categories:
        return 5, matched_categories
    if categories:
        return 3, []
    return 2, []


def compare_competitions(
    competitions: list[dict[str, Any]],
    profile: StudentProfile,
) -> dict[str, Any]:
    """分别返回学校认定、人工评价、学生适配和证据质量四个维度。"""

    comparisons: list[dict[str, Any]] = []
    for competition in competitions:
        categories = list(competition.get("categories") or [])
        if competition.get("category") and competition["category"] not in categories:
            categories.append(competition["category"])
        major_score, matches = _major_alignment(profile, categories)
        recommended_hours = int(competition.get("recommended_weekly_hours") or 6)
        if profile.weekly_hours >= recommended_hours:
            time_score = 5
        elif profile.weekly_hours >= max(1, recommended_hours - 2):
            time_score = 3
        else:
            time_score = 1
        comparisons.append(
            {
                "name": competition["name"],
                "school_recognition": {
                    "recognized": bool(competition.get("recognized", False)),
                    "level": competition.get("recognition_level", "not_provided"),
                    "note": competition.get("recognition_note", "未提供学校认定说明"),
                },
                "human_evaluation": {
                    "difficulty": competition.get("difficulty", "not_provided"),
                    "teamwork": competition.get("teamwork", "not_provided"),
                    "portfolio_value": competition.get("portfolio_value", "not_provided"),
                    "note": competition.get(
                        "human_evaluation_note", "示例人工评价，仅供比较参考。"
                    ),
                },
                "student_fit": {
                    "major_alignment": {
                        "level": _fit_level(major_score),
                        "matched_categories": matches,
                    },
                    "time_alignment": {
                        "level": _fit_level(time_score),
                        "available_weekly_hours": profile.weekly_hours,
                        "recommended_weekly_hours": recommended_hours,
                    },
                },
                "evidence_quality": {
                    "level": competition.get("evidence_quality", "custom_input"),
                    "source_type": competition.get("source_type", "user_supplied"),
                    "official": bool(competition.get("official", False)),
                },
            }
        )
    return {"comparisons": comparisons}
