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
    """通过子进程完成初始化、工具枚举与八个事实工具调用。"""

    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "sylulive_mcp"],
        cwd=PROJECT_ROOT,
        env={
            "SYLULIVE_MCP_MODE": "demo",
            "SYLULIVE_DEMO_ROOT": "./examples",
        },
    )

    async with stdio_client(parameters, errlog=sys.stderr) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            initialized = await session.initialize()
            listed = await session.list_tools()
            tool_names = {tool.name for tool in listed.tools}
            if len(tool_names) != 9:
                raise RuntimeError("demo 模式应注册 system_status 和八个事实工具")

            async def call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
                response = await session.call_tool(name, arguments)
                if response.isError or response.structuredContent is None:
                    raise RuntimeError(f"stdio 工具调用失败：{name}")
                if response.structuredContent.get("status") != "ok":
                    raise RuntimeError(f"stdio 工具返回错误：{name}")
                return response.structuredContent

            policy = await call(
                "policy_search",
                {"queries": ["交不起学费怎么办"], "historical_mode": "forbid", "limit": 5},
            )
            await call(
                "policy_get_sources",
                {"source_ids": [policy["results"][0]["source_id"]]},
            )
            competitions = await call("competition_search", {"categories": ["计算机"], "limit": 2})
            details = await call(
                "competition_get_details",
                {
                    "competition_ids": [
                        item["competition_id"] for item in competitions["competitions"]
                    ]
                },
            )
            await call(
                "competition_compare_facts",
                {
                    "competitions": details["competitions"],
                    "student_profile": {
                        "major": "计算机科学与技术",
                        "grade": "大三",
                        "weekly_hours": 8,
                    },
                },
            )
            await call(
                "academic_calculate_summary",
                {"snapshot_path": "academic/safe_snapshot.json"},
            )
            await call(
                "schedule_find_free_windows",
                {"schedule_path": "schedules/sample_week.json", "minimum_window_minutes": 30},
            )
            await call(
                "schedule_validate_plan",
                {
                    "schedule_path": "schedules/sample_week.json",
                    "plan": [
                        {
                            "item": "准备蓝桥杯",
                            "weekday": 1,
                            "start": "12:00",
                            "end": "13:00",
                            "minutes": 60,
                        }
                    ],
                    "requested_minutes": 60,
                },
            )
    return {"status": "ok", "server": initialized.serverInfo.name, "tools": sorted(tool_names)}


def main() -> None:
    print(json.dumps(asyncio.run(verify_stdio_protocol()), ensure_ascii=False))


if __name__ == "__main__":
    main()
