"""官方 MCP SDK stdio 协议测试。"""

from __future__ import annotations

import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters, stdio_client

PROJECT_ROOT = Path(__file__).resolve().parents[1]


async def test_stdio_initialize_list_and_call_tools() -> None:
    """初始化、工具列表、工具调用和 stdio 正常退出均通过官方 SDK 验证。"""

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
    async with stdio_client(parameters, errlog=sys.stderr) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            initialized = await session.initialize()
            assert initialized.serverInfo.name == "Hy3 Campus Decision Copilot"
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == {
                "hy3_campus_status",
                "answer_campus_question",
                "compare_competitions",
                "analyze_academic_snapshot",
                "plan_student_week",
            }
            response = await session.call_tool(
                "analyze_academic_snapshot",
                {"snapshot_path": "academic/safe_snapshot.json"},
            )
            assert not response.isError
            assert response.structuredContent is not None
            assert response.structuredContent["status"] == "ok"
            policy_response = await session.call_tool(
                "answer_campus_question",
                {"query": "创新创业学分如何认定？", "category": "policy"},
            )
            assert not policy_response.isError
            assert policy_response.structuredContent is not None
            assert policy_response.structuredContent["sources"][0]["document_type"]
            invalid_response = await session.call_tool(
                "answer_campus_question",
                {"query": "创新创业学分如何认定？", "unexpected": True},
            )
            assert invalid_response.isError
