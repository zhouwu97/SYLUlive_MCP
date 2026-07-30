"""工具输入的严格 Pydantic 契约。"""

from .academic import AcademicAnalysisInput, AcademicSnapshot
from .campus_question import CampusQuestionInput
from .competition import (
    CompareSelectedCompetitionsInput,
    CompetitionCompareInput,
    ExplainCompetitionCandidatesInput,
)
from .schedule import PlanStudentWeekInput

__all__ = [
    "AcademicAnalysisInput",
    "AcademicSnapshot",
    "CampusQuestionInput",
    "CompetitionCompareInput",
    "CompareSelectedCompetitionsInput",
    "ExplainCompetitionCandidatesInput",
    "PlanStudentWeekInput",
]
