"""验证仓库中公开示例数据的结构和本地算法约束。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hy3_campus_decision_mcp.deterministic.academic import analyze_academic_snapshot
from hy3_campus_decision_mcp.deterministic.schedule import build_week_plan, validate_week_plan
from hy3_campus_decision_mcp.schemas.academic import AcademicSnapshot
from hy3_campus_decision_mcp.schemas.schedule import PlanStudentWeekInput, WeeklySchedule

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read_json(relative_path: str) -> dict[str, Any]:
    """读取仓库内的受控示例 JSON。"""

    return json.loads((PROJECT_ROOT / "examples" / relative_path).read_text(encoding="utf-8"))


def main() -> None:
    """验证学业和课表示例，失败时以非零退出码终止。"""

    academic = AcademicSnapshot.model_validate(_read_json("academic/safe_snapshot.json"))
    academic_findings = analyze_academic_snapshot(academic)
    schedule = WeeklySchedule.model_validate(_read_json("schedules/sample_week.json"))
    request = PlanStudentWeekInput.model_validate(
        {
            "schedule": schedule.model_dump(mode="json"),
            "goals": [{"name": "准备蓝桥杯", "weekly_minutes": 360, "priority": "high"}],
            "constraints": {},
        }
    )
    plan_findings = build_week_plan(schedule, request)
    issues = validate_week_plan(schedule, request.constraints, plan_findings["plan"])
    if issues:
        raise RuntimeError(f"课表示例不满足硬约束：{','.join(issues)}")
    print(
        json.dumps(
            {
                "status": "ok",
                "academic_failed_courses": academic_findings["failed_course_count"],
                "scheduled_minutes": plan_findings["total_scheduled_minutes"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
