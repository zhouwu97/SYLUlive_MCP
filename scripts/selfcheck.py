"""不依赖真实 Hy3 的本地 Fixture 自检。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from hy3_campus_decision_mcp.config import Hy3Mode, Settings
from hy3_campus_decision_mcp.server import build_server

PROJECT_ROOT = Path(__file__).resolve().parents[1]


async def run_selfcheck() -> dict[str, Any]:
    """调用所有已注册工具，并断言统一输出和 Fixture 模式标记。"""

    settings = Settings(
        mode=Hy3Mode.FIXTURE,
        campus_root=PROJECT_ROOT / "examples",
        fixture_root=PROJECT_ROOT / "tests" / "fixtures" / "hy3",
    )
    server = build_server(settings)
    listed_tools = await server.list_tools()
    expected_tools = {
        "hy3_campus_status",
        "answer_campus_question",
        "compare_competitions",
        "analyze_academic_snapshot",
        "plan_student_week",
    }
    actual_tools = {tool.name for tool in listed_tools}
    if actual_tools != expected_tools:
        raise RuntimeError("工具注册结果不符合预期")

    calls = {
        "answer_campus_question": {
            "query": "创新创业学分如何认定？",
            "category": "policy",
            "max_sources": 5,
        },
        "compare_competitions": {
            "competition_names": ["蓝桥杯", "中国国际大学生创新大赛"],
            "student_profile": {
                "major": "计算机科学与技术",
                "grade": "大三",
                "weekly_hours": 8,
            },
        },
        "analyze_academic_snapshot": {"snapshot_path": "academic/safe_snapshot.json"},
        "plan_student_week": {
            "schedule_path": "schedules/sample_week.json",
            "goals": [{"name": "准备蓝桥杯", "weekly_minutes": 360, "priority": "high"}],
            "constraints": {},
        },
    }
    results: dict[str, str] = {}
    for tool_name, arguments in calls.items():
        _content, structured = await server.call_tool(tool_name, arguments)
        if structured.get("status") != "ok" or structured["model"]["mode"] != "fixture":
            raise RuntimeError(f"工具自检失败：{tool_name}")
        results[tool_name] = "ok"
    return {"status": "ok", "tools": results}


def main() -> None:
    """执行异步自检并输出精简结果。"""

    print(json.dumps(asyncio.run(run_selfcheck()), ensure_ascii=False))


if __name__ == "__main__":
    main()
