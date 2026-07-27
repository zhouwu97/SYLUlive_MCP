"""不依赖模型的确定性算法。"""

from .academic import analyze_academic_snapshot
from .schedule import find_free_windows

__all__ = ["analyze_academic_snapshot", "find_free_windows"]
