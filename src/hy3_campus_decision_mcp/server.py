"""基于 MCP 公开 Server API 的 stdio 服务组装。"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from pydantic import TypeAdapter

from .config import Hy3Mode, Settings, load_settings
from .constants import PACKAGE_VERSION, SERVER_NAME, STATUS_TOOL_NAME
from .contracts import TOOL_CONTRACTS, ToolContract
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
    active_contracts = (
        TOOL_CONTRACTS if settings.mode is not Hy3Mode.DISABLED else {}
    )

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
        # Pydantic 在业务入口再次验证，确保无论传输层如何调用都遵守同一严格契约。
        request = contract.input_model.model_validate(arguments)
        raw_result = await contract.handler(runtime, request.model_dump(mode="json"))
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


def main() -> None:
    """加载配置并运行 MCP stdio 服务。"""

    settings = load_settings()
    configure_logging(settings.log_level)
    asyncio.run(serve(settings))
