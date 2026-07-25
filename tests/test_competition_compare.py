"""赛事四维比较测试。"""

from __future__ import annotations

from hy3_campus_decision_mcp.deterministic.competition import compare_competitions
from hy3_campus_decision_mcp.schemas.competition import StudentProfile


def test_competition_dimensions_remain_separate() -> None:
    """结果不能出现把四个维度混合的总分字段。"""

    result = compare_competitions(
        [
            {
                "name": "赛事 A",
                "categories": ["计算机"],
                "recognized": True,
                "recommended_weekly_hours": 8,
                "evidence_quality": "demonstration",
            },
            {
                "name": "赛事 B",
                "categories": ["机械"],
                "recognized": False,
                "recommended_weekly_hours": 6,
                "evidence_quality": "custom_input",
            },
        ],
        StudentProfile(major="计算机科学与技术", grade="大三", weekly_hours=8),
    )
    for item in result["comparisons"]:
        assert set(item) == {
            "name",
            "school_recognition",
            "human_evaluation",
            "student_fit",
            "evidence_quality",
        }
        assert "total_score" not in item
