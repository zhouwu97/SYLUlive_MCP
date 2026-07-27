"""官方 MCP SDK stdio 协议测试。"""

from __future__ import annotations

import asyncio
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest
from mcp import ClientSession, StdioServerParameters, stdio_client
from starlette.testclient import TestClient

from sylulive_mcp.config import ServiceMode, Settings, TransportMode
from sylulive_mcp.constants import DEMO_TOOL_NAMES
from sylulive_mcp.server import build_http_app
from sylulive_mcp.tools.runtime import ToolRuntime

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
            assert {tool.name for tool in tools.tools} == {"system_status", *DEMO_TOOL_NAMES}
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
                "academic_get_summary",
                {},
            )
    assert not response.isError
    assert response.structuredContent == {
        "status": "error",
        "code": "grant_missing",
        "message": "Production tool calls require a short-lived SYLUlive MCP grant.",
    }


async def test_production_stdio_forwards_process_grant_to_go_api() -> None:
    captured: list[str] = []

    class GoHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            captured.append(self.headers["Authorization"])
            content_length = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(content_length)
            body = json.dumps(
                {
                    "status": "ok",
                    "result": {
                        "earned_credits": 86,
                        "required_credits": 160,
                        "failed_course_count": 2,
                        "failed_credits": 5,
                        "gpa": 2.84,
                        "data_completeness": "complete",
                    },
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *_args: object) -> None:
            return

    go_server = ThreadingHTTPServer(("127.0.0.1", 0), GoHandler)
    go_thread = threading.Thread(target=go_server.serve_forever, daemon=True)
    go_thread.start()
    try:
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "sylulive_mcp"],
            cwd=PROJECT_ROOT,
            env={
                "SYLULIVE_MCP_MODE": "production",
                "SYLULIVE_MCP_GRANT": "stdio-run-grant",
                "SYLULIVE_API_BASE": f"http://127.0.0.1:{go_server.server_port}",
            },
        )
        async with stdio_client(parameters, errlog=sys.stderr) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                response = await session.call_tool("academic_get_summary", {})
    finally:
        go_server.shutdown()
        go_server.server_close()
        go_thread.join(timeout=5)

    assert not response.isError
    assert response.structuredContent is not None
    assert response.structuredContent["status"] == "ok"
    assert captured == ["Bearer stdio-run-grant"]


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


def _tool_call(name: str, arguments: dict[str, object], request_id: int = 1) -> dict[str, object]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }


def _http_headers(grant: str | None = None) -> dict[str, str]:
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if grant is not None:
        headers["Authorization"] = f"Bearer {grant}"
    return headers


async def test_http_tool_call_forwards_request_grant_to_go_api() -> None:
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.headers["Authorization"])
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

    settings = Settings(
        mode=ServiceMode.PRODUCTION,
        transport=TransportMode.STREAMABLE_HTTP,
        api_base="https://internal.example",
    )
    runtime = ToolRuntime(settings, api_transport=httpx.MockTransport(handler))
    app = build_http_app(settings, runtime)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.post(
                "/mcp",
                headers=_http_headers("request-grant"),
                json=_tool_call("academic_get_summary", {}),
            )

    assert response.status_code == 200
    assert response.json()["result"]["structuredContent"]["status"] == "ok"
    assert captured == ["Bearer request-grant"]


async def test_http_tool_call_without_grant_is_rejected_before_go_api() -> None:
    called = False

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(500)

    settings = Settings(
        mode=ServiceMode.PRODUCTION,
        transport=TransportMode.STREAMABLE_HTTP,
        api_base="https://internal.example",
    )
    runtime = ToolRuntime(settings, api_transport=httpx.MockTransport(handler))
    app = build_http_app(settings, runtime)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.post(
                "/mcp",
                headers=_http_headers(),
                json=_tool_call("academic_get_summary", {}),
            )

    assert response.json()["result"]["structuredContent"]["code"] == "grant_missing"
    assert called is False


async def test_concurrent_http_requests_keep_grants_isolated() -> None:
    captured: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        authorization = request.headers["Authorization"]
        captured.append(authorization)
        gpa = 1.0 if authorization == "Bearer grant-a" else 2.0
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "result": {
                    "earned_credits": 80,
                    "required_credits": 160,
                    "failed_course_count": 0,
                    "failed_credits": 0,
                    "gpa": gpa,
                    "data_completeness": "complete",
                },
            },
        )

    settings = Settings(
        mode=ServiceMode.PRODUCTION,
        transport=TransportMode.STREAMABLE_HTTP,
        api_base="https://internal.example",
    )
    runtime = ToolRuntime(settings, api_transport=httpx.MockTransport(handler))
    app = build_http_app(settings, runtime)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:

            async def call(grant: str, request_id: int) -> float:
                response = await client.post(
                    "/mcp",
                    headers=_http_headers(grant),
                    json=_tool_call("academic_get_summary", {}, request_id),
                )
                return response.json()["result"]["structuredContent"]["result"]["gpa"]

            first, second = await asyncio.gather(call("grant-a", 1), call("grant-b", 2))

    assert (first, second) == (1.0, 2.0)
    assert sorted(captured) == ["Bearer grant-a", "Bearer grant-b"]


async def test_invalid_go_payload_becomes_output_validation_error() -> None:
    settings = Settings(
        mode=ServiceMode.PRODUCTION,
        transport=TransportMode.STREAMABLE_HTTP,
        api_base="https://internal.example",
    )
    runtime = ToolRuntime(
        settings,
        api_transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, json={"status": "ok", "result": {}})
        ),
    )
    app = build_http_app(settings, runtime)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.post(
                "/mcp",
                headers=_http_headers("grant"),
                json=_tool_call("academic_get_summary", {}),
            )

    assert response.json()["result"]["structuredContent"]["code"] == ("output_validation_failed")


def test_http_transport_rejects_process_wide_grant() -> None:
    with pytest.raises(ValueError, match="only valid for stdio"):
        Settings(
            mode=ServiceMode.PRODUCTION,
            transport=TransportMode.STREAMABLE_HTTP,
            grant_token="shared-grant",
        )


def test_stdio_transport_accepts_process_wide_grant() -> None:
    settings = Settings(
        mode=ServiceMode.PRODUCTION,
        transport=TransportMode.STDIO,
        grant_token="run-scoped-grant",
    )
    assert settings.has_grant is True


def test_http_rejects_untrusted_host_and_oversized_body() -> None:
    settings = Settings(
        mode=ServiceMode.DEMO,
        transport=TransportMode.STREAMABLE_HTTP,
        demo_root=PROJECT_ROOT / "examples",
        max_http_request_bytes=1024,
    )
    with TestClient(build_http_app(settings)) as client:
        untrusted = client.post(
            "/mcp",
            headers={**_http_headers(), "Host": "public.example"},
            json=_tool_call("system_status", {}),
        )
        oversized = client.post(
            "/mcp",
            headers={"Content-Type": "application/json"},
            content=b"x" * 2048,
        )
    assert untrusted.status_code == 400
    assert oversized.status_code == 413
