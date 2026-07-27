"""使用官方 MCP Python SDK 验证 stdio 协议。"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters, stdio_client

PROJECT_ROOT = Path(__file__).resolve().parents[1]


async def verify_stdio_protocol() -> dict[str, Any]:
    """通过子进程完成 initialize、tools/list 与四个核心 tools/call。"""

    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "hy3_campus_decision_mcp"],
        cwd=PROJECT_ROOT,
        env={
            "HY3_MODE": "fixture",
            "HY3_CAMPUS_ROOT": "./examples",
            "HY3_FIXTURE_ROOT": "./tests/fixtures/hy3",
        },
    )
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
    async with stdio_client(parameters, errlog=sys.stderr) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            initialized = await session.initialize()
            tools = await session.list_tools()
            tool_names = {tool.name for tool in tools.tools}
            if len(tool_names) != 5:
                raise RuntimeError("Fixture 模式应注册五个工具")
            results: dict[str, str] = {}
            for tool_name, arguments in calls.items():
                response = await session.call_tool(tool_name, arguments)
                if response.isError or response.structuredContent is None:
                    raise RuntimeError(
                        f"stdio 工具调用失败：{tool_name}; "
                        f"isError={response.isError}; "
                        f"structuredContent={response.structuredContent!r}; "
                        f"content={response.content!r}"
                    )
                if response.structuredContent.get("status") != "ok":
                    raise RuntimeError(f"stdio 工具返回错误：{tool_name}")
                results[tool_name] = "ok"
    return {
        "status": "ok",
        "server": initialized.serverInfo.name,
        "tools": results,
    }


def main() -> None:
    """执行 SDK 协议验证并输出不含敏感信息的摘要。"""

    print(json.dumps(asyncio.run(verify_stdio_protocol()), ensure_ascii=False))


if __name__ == "__main__":
    main()
