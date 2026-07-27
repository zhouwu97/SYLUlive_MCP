"""基于 MCP 公开 API 的 stdio 与 Streamable HTTP 服务组装。"""

from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from pydantic import TypeAdapter, ValidationError
from starlette.applications import Starlette
from starlette.routing import Route

from .auth import bearer_token
from .config import ServiceMode, Settings, TransportMode, load_settings
from .constants import PACKAGE_VERSION, SERVER_NAME, STATUS_TOOL_NAME
from .contracts import TOOL_CONTRACTS, ToolContract
from .errors import CampusMcpError
from .result_envelope import error_envelope
from .tools.runtime import ToolRuntime
from .tools.status import build_status


def configure_logging(level: str) -> None:
    """诊断日志只能写入 stderr，stdout 专供 JSON-RPC 使用。"""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
        force=True,
    )


def _status_tool() -> types.Tool:
    """构造没有输入且具备显式对象 Schema 的状态工具定义。"""

    return types.Tool(
        name=STATUS_TOOL_NAME,
        description="查看安全的 MCP 运行状态和可用能力。",
        inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
        outputSchema={"type": "object"},
    )


def _tool_definition(contract: ToolContract) -> types.Tool:
    """从唯一注册表投影 MCP tools/list 定义，避免 SDK 私有字段改写。"""

    return types.Tool(
        name=contract.name,
        description=contract.description,
        inputSchema=contract.input_schema,
        outputSchema=contract.output_schema,
    )


def build_server(settings: Settings) -> Server:
    """创建显式列举和调用工具的 MCP Server。"""

    server = Server(SERVER_NAME, version=PACKAGE_VERSION)
    runtime = ToolRuntime(settings)
    active_contracts = TOOL_CONTRACTS if settings.mode is not ServiceMode.DISABLED else {}

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        definitions = [_status_tool()]
        definitions.extend(_tool_definition(contract) for contract in active_contracts.values())
        return definitions

    @server.call_tool(validate_input=True)
    async def call_registered_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == STATUS_TOOL_NAME:
            return build_status(settings)
        contract = active_contracts.get(name)
        if contract is None:
            raise ValueError(f"未知或当前模式不可用的工具：{name}")
        transport_request = server.request_context.request
        request_grant = bearer_token(transport_request)
        configured_grant = settings.grant_token.get_secret_value().strip()
        active_grant = request_grant or configured_grant or None
        if settings.mode is ServiceMode.PRODUCTION and active_grant is None:
            return error_envelope(
                CampusMcpError(
                    "grant_missing",
                    "Production tool calls require a short-lived SYLUlive MCP grant.",
                )
            )
        # Pydantic 在业务入口再次验证，确保无论传输层如何调用都遵守同一严格契约。
        request = contract.input_model.model_validate(arguments)
        with runtime.grants.bind(active_grant):
            raw_result = await contract.handler(runtime, request.model_dump(mode="json"))
        try:
            validated = TypeAdapter(contract.output_model).validate_python(raw_result)
        except ValidationError:
            raw_result = error_envelope(
                CampusMcpError(
                    "output_validation_failed",
                    "The tool produced a response that does not match its contract.",
                )
            )
            validated = TypeAdapter(contract.output_model).validate_python(raw_result)
        return TypeAdapter(contract.output_model).dump_python(validated, mode="json")

    return server


async def serve(settings: Settings) -> None:
    """启动 stdio 事件循环，普通日志绝不写入协议输出。"""

    server = build_server(settings)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


class _StreamableHttpAsgiApp:
    """把 SDK SessionManager 适配为 Starlette ASGI 端点。"""

    def __init__(self, manager: StreamableHTTPSessionManager) -> None:
        self._manager = manager

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        await self._manager.handle_request(scope, receive, send)


def build_http_app(settings: Settings) -> Starlette:
    """构造无服务器状态的 Streamable HTTP `/mcp` 应用。"""

    server = build_server(settings)
    manager = StreamableHTTPSessionManager(
        app=server,
        json_response=True,
        stateless=True,
    )

    @asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        async with manager.run():
            yield

    return Starlette(
        routes=[Route(settings.http_path, endpoint=_StreamableHttpAsgiApp(manager))],
        lifespan=lifespan,
    )


async def serve_http(settings: Settings) -> None:
    """运行供容器化 LangChain Agent 使用的 Streamable HTTP 服务。"""

    config = uvicorn.Config(
        build_http_app(settings),
        host=settings.http_host,
        port=settings.http_port,
        log_level=settings.log_level.lower(),
    )
    await uvicorn.Server(config).serve()


def main() -> None:
    """加载配置并按所选传输方式运行 MCP 服务。"""

    settings = load_settings()
    configure_logging(settings.log_level)
    if settings.transport is TransportMode.STREAMABLE_HTTP:
        asyncio.run(serve_http(settings))
    else:
        asyncio.run(serve(settings))
