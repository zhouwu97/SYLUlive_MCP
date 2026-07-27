"""使用官方 MCP SDK 验证生产 Streamable HTTP 协议与 Grant 转发。"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from sylulive_mcp.config import ServiceMode, Settings, TransportMode
from sylulive_mcp.constants import CORE_TOOL_NAMES
from sylulive_mcp.server import build_http_app
from sylulive_mcp.tools.runtime import ToolRuntime


def _go_handler(request: httpx.Request) -> httpx.Response:
    """模拟 Go 授权数据源，并核验 Grant 没有进入 JSON 参数。"""

    if request.headers.get("Authorization") != "Bearer sdk-http-grant":
        return httpx.Response(403)
    payload = json.loads(request.content)
    if "grant" in json.dumps(payload).casefold():
        return httpx.Response(400)
    if request.url.path == "/internal/mcp/academic/summary":
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "result": {
                    "earned_credits": 86,
                    "required_credits": 160,
                    "failed_course_count": 2,
                    "failed_credits": 5,
                    "gpa": 2.84,
                    "data_completeness": "complete",
                },
            },
        )
    return httpx.Response(404)


async def _call_with_grant(app: Any) -> tuple[str, set[str]]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
        headers={"Authorization": "Bearer sdk-http-grant"},
    ) as http_client:
        async with streamable_http_client(
            "http://testserver/mcp",
            http_client=http_client,
            terminate_on_close=False,
        ) as (read_stream, write_stream, _session_id):
            async with ClientSession(read_stream, write_stream) as session:
                initialized = await session.initialize()
                listed = await session.list_tools()
                response = await session.call_tool("academic_get_summary", {})
                if response.isError or response.structuredContent is None:
                    raise RuntimeError("Streamable HTTP 生产工具调用失败")
                if response.structuredContent.get("status") != "ok":
                    raise RuntimeError("Streamable HTTP 生产工具返回错误")
                return initialized.serverInfo.name, {tool.name for tool in listed.tools}


async def _call_without_grant(app: Any) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as http_client:
        async with streamable_http_client(
            "http://testserver/mcp",
            http_client=http_client,
            terminate_on_close=False,
        ) as (read_stream, write_stream, _session_id):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                response = await session.call_tool("academic_get_summary", {})
                if response.structuredContent is None:
                    raise RuntimeError("无 Grant 调用没有返回结构化错误")
                if response.structuredContent.get("code") != "grant_missing":
                    raise RuntimeError("无 Grant 调用未被拒绝")


async def verify_streamable_http_protocol() -> dict[str, Any]:
    """执行初始化、工具枚举、带 Grant 调用和无 Grant 拒绝。"""

    settings = Settings(
        mode=ServiceMode.PRODUCTION,
        transport=TransportMode.STREAMABLE_HTTP,
        api_base="https://internal.example",
    )
    runtime = ToolRuntime(settings, api_transport=httpx.MockTransport(_go_handler))
    app = build_http_app(settings, runtime)
    async with app.router.lifespan_context(app):
        server_name, tool_names = await _call_with_grant(app)
        await _call_without_grant(app)

    expected = {"system_status", *CORE_TOOL_NAMES}
    if tool_names != expected:
        raise RuntimeError("Streamable HTTP 工具注册表与生产契约不一致")
    return {"status": "ok", "server": server_name, "tools": sorted(tool_names)}


def main() -> None:
    print(json.dumps(asyncio.run(verify_streamable_http_protocol()), ensure_ascii=False))


if __name__ == "__main__":
    main()
