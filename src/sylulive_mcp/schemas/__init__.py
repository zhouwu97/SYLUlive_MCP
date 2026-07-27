"""纯工具输入与输出的严格 Pydantic 契约。"""

from .academic import AcademicAnalysisInput, AcademicSnapshot
from .competition import StudentProfile
from .schedule import ScheduleConstraints, WeeklySchedule

__all__ = [
    "AcademicAnalysisInput",
    "AcademicSnapshot",
    "ScheduleConstraints",
    "StudentProfile",
    "WeeklySchedule",
]
