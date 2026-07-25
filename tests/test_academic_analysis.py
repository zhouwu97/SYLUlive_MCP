"""学业确定性计算测试。"""

from __future__ import annotations

from hy3_campus_decision_mcp.deterministic.academic import analyze_academic_snapshot
from hy3_campus_decision_mcp.schemas.academic import AcademicSnapshot


def test_credit_and_failure_findings_are_deterministic() -> None:
    """挂科、必修挂科学分、缺口与未知成绩来自本地规则。"""

    snapshot = AcademicSnapshot.model_validate(
        {
            "courses": [
                {"course_name": "必修 A", "credits": 3, "is_required": True, "grade": 59},
                {"course_name": "选修 B", "credits": 2, "is_required": False, "passed": False},
                {"course_name": "课程 C", "credits": None, "is_required": True, "grade": None},
            ],
            "earned_credits": 96,
            "required_credits": 108,
            "erke_earned": 38,
            "erke_required": 60,
        }
    )
    result = analyze_academic_snapshot(snapshot)
    assert result["failed_course_count"] == 2
    assert result["failed_required_credits"] == 3
    assert result["credit_gap"] == 12
    assert result["erke_gap"] == 22
    assert result["unknown_grade_course_count"] == 1
    assert result["missing_credit_course_count"] == 1
