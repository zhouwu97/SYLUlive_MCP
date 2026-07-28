"""不能由模型覆盖的本地计算。"""

from .academic import analyze_academic_snapshot
from .competition import compare_competitions
from .schedule import build_week_plan, validate_week_plan

__all__ = [
    "analyze_academic_snapshot",
    "build_week_plan",
    "compare_competitions",
    "validate_week_plan",
]
