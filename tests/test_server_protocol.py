"""官方 MCP SDK stdio 协议测试。"""

from __future__ import annotations

import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters, stdio_client
from starlette.testclient import TestClient

from sylulive_mcp.config import ServiceMode, Settings, TransportMode
from sylulive_mcp.constants import CORE_TOOL_NAMES
from sylulive_mcp.server import build_http_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]


async def test_stdio_initialize_list_and_call_tools() -> None:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "sylulive_mcp"],
        cwd=PROJECT_ROOT,
        env={"SYLULIVE_MCP_MODE": "demo", "SYLULIVE_DEMO_ROOT": "./examples"},
    )
    async with stdio_client(parameters, errlog=sys.stderr) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            initialized = await session.initialize()
            assert initialized.serverInfo.name == "SYLUlive MCP Tools"
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == {"system_status", *CORE_TOOL_NAMES}
            response = await session.call_tool(
                "academic_calculate_summary",
                {"snapshot_path": "academic/safe_snapshot.json"},
            )
            assert not response.isError
            assert response.structuredContent is not None
            assert response.structuredContent["status"] == "ok"
            assert "model" not in response.structuredContent


async def test_production_stdio_rejects_tool_call_without_grant() -> None:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "sylulive_mcp"],
        cwd=PROJECT_ROOT,
        env={"SYLULIVE_MCP_MODE": "production"},
    )
    async with stdio_client(parameters, errlog=sys.stderr) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            response = await session.call_tool(
                "academic_calculate_summary",
                {
                    "snapshot": {
                        "courses": [],
                        "earned_credits": 0,
                        "required_credits": 0,
                        "erke_earned": 0,
                        "erke_required": 0,
                    }
                },
            )
    assert not response.isError
    assert response.structuredContent == {
        "status": "error",
        "code": "grant_missing",
        "message": "Production tool calls require a short-lived SYLUlive MCP grant.",
    }


def test_streamable_http_initialize() -> None:
    settings = Settings(
        mode=ServiceMode.DEMO,
        transport=TransportMode.STREAMABLE_HTTP,
        demo_root=PROJECT_ROOT / "examples",
    )
    with TestClient(build_http_app(settings)) as client:
        response = client.post(
            "/mcp",
            headers={
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
        )
    assert response.status_code == 200
    assert response.json()["result"]["serverInfo"]["name"] == "SYLUlive MCP Tools"
