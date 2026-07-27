"""验证仓库公开示例数据与确定性算法。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sylulive_mcp.deterministic.academic import analyze_academic_snapshot
from sylulive_mcp.deterministic.schedule import find_free_windows
from sylulive_mcp.schemas.academic import AcademicSnapshot
from sylulive_mcp.schemas.schedule import ScheduleConstraints, WeeklySchedule

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read_json(relative_path: str) -> dict[str, Any]:
    return json.loads((PROJECT_ROOT / "examples" / relative_path).read_text(encoding="utf-8"))


def main() -> None:
    academic = AcademicSnapshot.model_validate(_read_json("academic/safe_snapshot.json"))
    findings = analyze_academic_snapshot(academic)
    schedule = WeeklySchedule.model_validate(_read_json("schedules/sample_week.json"))
    windows = find_free_windows(schedule, ScheduleConstraints(), minimum_window_minutes=30)
    if not windows:
        raise RuntimeError("课表示例没有可用空闲窗口")
    print(
        json.dumps(
            {
                "status": "ok",
                "academic_failed_courses": findings["failed_course_count"],
                "free_window_count": len(windows),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
