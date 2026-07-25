"""工具输入 schema 的边界测试。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hy3_campus_decision_mcp.schemas.academic import AcademicAnalysisInput
from hy3_campus_decision_mcp.schemas.campus_question import CampusQuestionInput
from hy3_campus_decision_mcp.schemas.competition import CompetitionCompareInput
from hy3_campus_decision_mcp.schemas.schedule import PlanStudentWeekInput


def test_extra_fields_are_rejected() -> None:
    """所有继承严格输入基类的工具模型都拒绝未声明字段。"""

    with pytest.raises(ValidationError):
        CampusQuestionInput.model_validate({"query": "测试", "unexpected": True})


def test_academic_requires_exactly_one_source() -> None:
    """内联快照和文件路径不能同时存在或同时缺失。"""

    with pytest.raises(ValidationError):
        AcademicAnalysisInput.model_validate({})
    with pytest.raises(ValidationError):
        AcademicAnalysisInput.model_validate(
            {
                "snapshot": {
                    "courses": [],
                    "earned_credits": 0,
                    "required_credits": 0,
                    "erke_earned": 0,
                    "erke_required": 0,
                },
                "snapshot_path": "academic/safe_snapshot.json",
            }
        )


def test_competition_count_and_mode_are_enforced() -> None:
    """赛事比较需要且仅需要 2 至 5 个同一来源的赛事。"""

    profile = {"major": "计算机科学与技术", "grade": "大三", "weekly_hours": 8}
    with pytest.raises(ValidationError):
        CompetitionCompareInput.model_validate(
            {"competition_names": ["蓝桥杯"], "student_profile": profile}
        )
    with pytest.raises(ValidationError):
        CompetitionCompareInput.model_validate(
            {
                "competition_names": ["蓝桥杯", "中国国际大学生创新大赛"],
                "competitions": [{"name": "自定义 A"}, {"name": "自定义 B"}],
                "student_profile": profile,
            }
        )


def test_schedule_requires_monday_and_single_source() -> None:
    """周计划禁止非周一起点和重复来源。"""

    with pytest.raises(ValidationError):
        PlanStudentWeekInput.model_validate(
            {
                "schedule": {
                    "week_start": "2026-07-28",
                    "timezone": "Asia/Shanghai",
                    "fixed_events": [],
                },
                "goals": [],
                "constraints": {},
            }
        )
    with pytest.raises(ValidationError):
        PlanStudentWeekInput.model_validate(
            {
                "schedule": {
                    "week_start": "2026-07-27",
                    "timezone": "Asia/Shanghai",
                    "fixed_events": [],
                },
                "schedule_path": "schedules/sample_week.json",
                "goals": [],
                "constraints": {},
            }
        )
