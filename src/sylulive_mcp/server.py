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
from starlette.middleware import Middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.routing import Route

from .auth import GrantContext, parse_bearer_authorization
from .config import ServiceMode, Settings, TransportMode, load_settings
from .constants import PACKAGE_VERSION, SERVER_NAME, STATUS_TOOL_NAME
from .contracts import ToolContract, contracts_for_mode
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


def build_server(settings: Settings, runtime: ToolRuntime | None = None) -> Server:
    """创建显式列举和调用工具的 MCP Server。"""

    server = Server(SERVER_NAME, version=PACKAGE_VERSION)
    runtime = runtime or ToolRuntime(settings)
    active_contracts = contracts_for_mode(settings.mode)

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
        if settings.transport is TransportMode.STREAMABLE_HTTP:
            active_grant = runtime.grants.current()
        else:
            active_grant = (
                runtime.grants.current() or settings.grant_token.get_secret_value().strip() or None
            )
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

    runtime = ToolRuntime(settings)
    server = build_server(settings, runtime)
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )
    finally:
        await runtime.aclose()


class _StreamableHttpAsgiApp:
    """在 ASGI 请求边界绑定 Grant，再把请求交给 SDK SessionManager。"""

    def __init__(
        self,
        manager: StreamableHTTPSessionManager,
        grants: GrantContext,
        max_request_bytes: int,
    ) -> None:
        self._manager = manager
        self._grants = grants
        self._max_request_bytes = max_request_bytes

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self._manager.handle_request(scope, receive, send)
            return

        headers = {
            key.decode("latin1").casefold(): value.decode("latin1")
            for key, value in scope.get("headers", [])
        }
        content_length = headers.get("content-length")
        if content_length and content_length.isdigit():
            if int(content_length) > self._max_request_bytes:
                await self._reject_too_large(send)
                return

        received = 0

        async def limited_receive() -> Any:
            nonlocal received
            message = await receive()
            if message.get("type") == "http.request":
                received += len(message.get("body", b""))
                if received > self._max_request_bytes:
                    raise _HttpRequestTooLarge
            return message

        grant = parse_bearer_authorization(headers.get("authorization", ""))
        try:
            with self._grants.bind(grant):
                await self._manager.handle_request(scope, limited_receive, send)
        except _HttpRequestTooLarge:
            await self._reject_too_large(send)

    @staticmethod
    async def _reject_too_large(send: Any) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [(b"content-type", b"text/plain; charset=utf-8")],
            }
        )
        await send({"type": "http.response.body", "body": b"Request body too large"})


class _HttpRequestTooLarge(Exception):
    """ASGI 请求体超过配置上限。"""


def build_http_app(settings: Settings, runtime: ToolRuntime | None = None) -> Starlette:
    """构造无服务器状态的 Streamable HTTP `/mcp` 应用。"""

    runtime = runtime or ToolRuntime(settings)
    server = build_server(settings, runtime)
    manager = StreamableHTTPSessionManager(
        app=server,
        json_response=True,
        stateless=True,
    )

    @asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        try:
            async with manager.run():
                yield
        finally:
            await runtime.aclose()

    allowed_hosts = list(settings.http_allowed_hosts)
    if settings.http_host not in {"0.0.0.0", "::"} and settings.http_host not in allowed_hosts:
        allowed_hosts.append(settings.http_host)

    return Starlette(
        routes=[
            Route(
                settings.http_path,
                endpoint=_StreamableHttpAsgiApp(
                    manager,
                    runtime.grants,
                    settings.max_http_request_bytes,
                ),
            )
        ],
        middleware=[Middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)],
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
