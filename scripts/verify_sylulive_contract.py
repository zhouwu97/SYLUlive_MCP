"""通过真实 stdio 子进程校验 diaofenyuan 的 Hy3 MCP 契约。"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters, stdio_client

from hy3_campus_decision_mcp.constants import STATUS_TOOL_NAME
from hy3_campus_decision_mcp.contracts import (
    PINNED_TOOL_CONTRACTS,
    SYLULIVE_RUNTIME_TOOL_NAMES,
    TOOL_CONTRACTS,
    schema_digest,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _schema_digest(tool: Any) -> str:
    """从 SDK tools/list 定义计算与 Go 相同的输入/输出摘要。"""

    return schema_digest(tool.inputSchema, tool.outputSchema)


async def verify_contract() -> dict[str, Any]:
    """启动 Fixture MCP，执行 initialize、tools/list 和状态工具调用。"""

    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "hy3_campus_decision_mcp"],
        cwd=PROJECT_ROOT,
        env={
            "HY3_MODE": "fixture",
            "HY3_TOOL_PROFILE": "sylulive_runtime",
            "HY3_CAMPUS_ROOT": "./examples",
            "HY3_FIXTURE_ROOT": "./tests/fixtures/hy3",
        },
    )
    async with stdio_client(parameters, errlog=sys.stderr) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            listed = await session.list_tools()
            tools = {tool.name: tool for tool in listed.tools}
            expected_names = {STATUS_TOOL_NAME, *SYLULIVE_RUNTIME_TOOL_NAMES}
            if set(tools) != expected_names:
                raise RuntimeError(f"tools/list 与 sylulive_runtime 配置不一致: {sorted(tools)}")

            status_response = await session.call_tool(STATUS_TOOL_NAME, {})
            if status_response.isError or status_response.structuredContent is None:
                raise RuntimeError("状态工具返回错误或缺少结构化内容")
            status = status_response.structuredContent
            if status.get("contract_version") != "sylulive-hy3/1":
                raise RuntimeError("状态工具契约版本不匹配")
            if status.get("available_tools") != [STATUS_TOOL_NAME, *SYLULIVE_RUNTIME_TOOL_NAMES]:
                raise RuntimeError("状态工具的 available_tools 与 tools/list 不一致")

            actual: dict[str, str] = {}
            for name in SYLULIVE_RUNTIME_TOOL_NAMES:
                actual[name] = _schema_digest(tools[name])
                fixed = PINNED_TOOL_CONTRACTS[name]["schema_sha256"]
                implementation = TOOL_CONTRACTS[name].schema_sha256
                reported = status["tool_contracts"][name]["schema_sha256"]
                if actual[name] != fixed or implementation != fixed or reported != fixed:
                    raise RuntimeError(
                        f"{name} Schema 摘要不一致: actual={actual[name]}, "
                        f"implementation={implementation}, fixed={fixed}, reported={reported}"
                    )

            calls = {
                "compare_competitions": {
                    "student_profile": {
                        "major": "测试专业",
                        "grade": "测试年级",
                        "weekly_hours": 8,
                    },
                    "competitions": [
                        {"name": "测试赛事一", "difficulty": "low"},
                        {"name": "测试赛事二", "difficulty": "medium"},
                    ],
                },
                "analyze_academic_snapshot": {
                    "snapshot_path": "academic/safe_snapshot.json",
                },
                "plan_student_week": {
                    "schedule_path": "schedules/sample_week.json",
                    "goals": [{"name": "准备蓝桥杯", "weekly_minutes": 60, "priority": "high"}],
                    "constraints": {},
                },
            }
            for name, arguments in calls.items():
                response = await session.call_tool(name, arguments)
                if response.isError or response.structuredContent is None:
                    raise RuntimeError(f"Fixture 工具调用失败: {name}")
                if response.structuredContent.get("status") != "ok":
                    raise RuntimeError(f"Fixture 工具返回错误: {name}")
    return {
        "status": "ok",
        "contract_version": "sylulive-hy3/1",
        "digests": actual,
        "fixture_calls": sorted(calls),
    }


def main() -> None:
    """输出机器可读的契约校验结果。"""

    print(json.dumps(asyncio.run(verify_contract()), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
