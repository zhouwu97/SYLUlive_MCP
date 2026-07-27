"""运行公开的 30 案例确定性与安全评测。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hy3_campus_decision_mcp.deterministic.academic import analyze_academic_snapshot  # noqa: E402
from hy3_campus_decision_mcp.deterministic.competition import compare_competitions  # noqa: E402
from hy3_campus_decision_mcp.deterministic.schedule import (  # noqa: E402
    build_week_plan,
    validate_week_plan,
)
from hy3_campus_decision_mcp.errors import CampusMcpError  # noqa: E402
from hy3_campus_decision_mcp.safety.path_policy import WorkspacePathPolicy  # noqa: E402
from hy3_campus_decision_mcp.safety.sensitive_fields import reject_sensitive_fields  # noqa: E402
from hy3_campus_decision_mcp.schemas.academic import AcademicSnapshot  # noqa: E402
from hy3_campus_decision_mcp.schemas.competition import StudentProfile  # noqa: E402
from hy3_campus_decision_mcp.schemas.schedule import (  # noqa: E402
    PlanStudentWeekInput,
    WeeklySchedule,
)

CASES_FILE = Path(__file__).with_name("cases.json")
RESULTS_FILE = Path(__file__).with_name("results.json")


def _academic(case: dict[str, Any]) -> None:
    """逐字段核对学业确定性结果。"""

    actual = analyze_academic_snapshot(AcademicSnapshot.model_validate(case["snapshot"]))
    for key, expected in case["expected"].items():
        if actual.get(key) != expected:
            raise AssertionError(f"{key}: expected {expected!r}, got {actual.get(key)!r}")


def _schedule(case: dict[str, Any]) -> None:
    """生成计划并确认所有硬约束均无违规。"""

    schedule = WeeklySchedule.model_validate(
        {
            "week_start": "2026-07-27",
            "timezone": "Asia/Shanghai",
            "fixed_events": [
                {"title": "课程", "weekday": 1, "start": "08:00", "end": "11:40"},
                {"title": "实验课", "weekday": 3, "start": "14:00", "end": "17:00"},
            ],
        }
    )
    request = PlanStudentWeekInput.model_validate(
        {
            "schedule": schedule.model_dump(mode="json"),
            **{key: case[key] for key in ("goals", "constraints")},
        }
    )
    findings = build_week_plan(schedule, request)
    issues = validate_week_plan(schedule, request.constraints, findings["plan"])
    if issues:
        raise AssertionError(f"hard constraint violations: {issues}")


def _competition(case: dict[str, Any]) -> None:
    """确认四个维度保持分离，且不生成综合分。"""

    candidates = [
        {
            "name": "候选赛事A",
            "categories": [case["category"]],
            "recognized": False,
            "recommended_weekly_hours": case["recommended_hours"],
        },
        {
            "name": "候选赛事B",
            "categories": ["创新创业"],
            "recognized": True,
            "recommended_weekly_hours": 5,
        },
    ]
    profile = StudentProfile(major=case["major"], grade="大二", weekly_hours=case["weekly_hours"])
    result = compare_competitions(candidates, profile)
    first = result["comparisons"][0]
    required = {"school_recognition", "human_evaluation", "student_fit", "evidence_quality"}
    if not required.issubset(first) or "score" in first:
        raise AssertionError("competition dimensions were mixed or collapsed")
    if first["school_recognition"]["recognized"] is not False:
        raise AssertionError("school recognition was invented")
    if first["student_fit"]["major_alignment"]["level"] != case["expected_major"]:
        raise AssertionError("major alignment mismatch")
    if first["student_fit"]["time_alignment"]["level"] != case["expected_time"]:
        raise AssertionError("time alignment mismatch")


def _security(case: dict[str, Any]) -> None:
    """确认危险输入以稳定错误码安全失败。"""

    try:
        if case["scenario"] == "path":
            policy = WorkspacePathPolicy(PROJECT_ROOT / "examples", max_file_bytes=1_048_576)
            policy.resolve_file(case["value"])
        else:
            reject_sensitive_fields(case["value"])
    except CampusMcpError as error:
        if error.code != case["expected_code"]:
            raise AssertionError(f"expected {case['expected_code']}, got {error.code}") from error
        return
    raise AssertionError("unsafe input was accepted")


RUNNERS = {
    "academic": _academic,
    "schedule": _schedule,
    "competition": _competition,
    "security": _security,
}


def evaluate() -> dict[str, Any]:
    """执行全部案例并返回稳定、可提交的聚合结果。"""

    suite = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    details: list[dict[str, str]] = []
    by_type: dict[str, dict[str, int]] = {}
    for case in suite["cases"]:
        case_type = case["type"]
        bucket = by_type.setdefault(case_type, {"passed": 0, "total": 0})
        bucket["total"] += 1
        try:
            RUNNERS[case_type](case)
        except Exception as error:
            details.append({"id": case["id"], "status": "failed", "reason": str(error)})
        else:
            bucket["passed"] += 1
            details.append({"id": case["id"], "status": "passed"})

    passed = sum(item["status"] == "passed" for item in details)
    total = len(details)
    return {
        "benchmark_version": suite["benchmark_version"],
        "case_count": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate_percent": round(passed / total * 100, 2),
        "metrics": {
            "academic_deterministic_cases": by_type["academic"],
            "schedule_hard_constraint_violations": 0
            if by_type["schedule"]["passed"] == by_type["schedule"]["total"]
            else None,
            "competition_dimension_separation": by_type["competition"],
            "security_rejections": by_type["security"],
        },
        "cases": details,
    }


def main() -> None:
    """生成结果，或检查提交结果是否仍与实现一致。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = evaluate()
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not RESULTS_FILE.is_file() or RESULTS_FILE.read_text(encoding="utf-8") != encoded:
            raise SystemExit("evaluation/results.json 与当前实现不一致")
    else:
        RESULTS_FILE.write_text(encoded, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {key: result[key] for key in ("case_count", "passed", "failed", "pass_rate_percent")},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
