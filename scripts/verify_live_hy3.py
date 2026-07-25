"""显式 Live 模式下的 Hy3 验证脚本。"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from hy3_campus_decision_mcp.config import Hy3Mode, load_settings
from hy3_campus_decision_mcp.tools.analyze_academic_snapshot import analyze_academic_snapshot
from hy3_campus_decision_mcp.tools.answer_campus_question import answer_campus_question
from hy3_campus_decision_mcp.tools.compare_competitions import compare_competitions
from hy3_campus_decision_mcp.tools.plan_student_week import plan_student_week
from hy3_campus_decision_mcp.tools.runtime import ToolRuntime


async def verify_live() -> dict[str, Any]:
    """调用四个核心工具，拒绝 Fixture 或缺失 Key 的伪验证。"""

    settings = load_settings()
    if settings.mode is not Hy3Mode.LIVE:
        raise RuntimeError("请显式设置 HY3_MODE=live 后再执行验证")
    if not settings.has_api_key:
        raise RuntimeError("HY3_MODE=live 时必须设置 HY3_API_KEY")
    runtime = ToolRuntime(settings)
    calls = {
        "answer_campus_question": answer_campus_question(
            runtime,
            {"query": "创新创业学分如何认定？", "category": "policy", "max_sources": 5},
        ),
        "compare_competitions": compare_competitions(
            runtime,
            {
                "competition_names": ["蓝桥杯", "中国国际大学生创新大赛"],
                "student_profile": {
                    "major": "计算机科学与技术",
                    "grade": "大三",
                    "weekly_hours": 8,
                },
            },
        ),
        "analyze_academic_snapshot": analyze_academic_snapshot(
            runtime,
            {"snapshot_path": "academic/safe_snapshot.json"},
        ),
        "plan_student_week": plan_student_week(
            runtime,
            {
                "schedule_path": "schedules/sample_week.json",
                "goals": [{"name": "准备蓝桥杯", "weekly_minutes": 360, "priority": "high"}],
                "constraints": {},
            },
        ),
    }
    validated: dict[str, dict[str, str]] = {}
    for tool_name, call in calls.items():
        response = await call
        if response.get("status") != "ok":
            raise RuntimeError(
                f"Live 工具调用失败：{tool_name} ({response.get('code', 'unknown')})"
            )
        if response["model"]["mode"] != "live":
            raise RuntimeError(f"Live 验证被拒绝：{tool_name} 未标记为 live")
        validated[tool_name] = {
            "status": response["status"],
            "schema_version": response["meta"]["schema_version"],
            "reasoning_effort": response["model"]["reasoning_effort"],
        }
    return {"status": "ok", "mode": "live", "tools": validated}


def main() -> None:
    """输出可转录到验证记录的脱敏摘要。"""

    try:
        print(json.dumps(asyncio.run(verify_live()), ensure_ascii=False))
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
