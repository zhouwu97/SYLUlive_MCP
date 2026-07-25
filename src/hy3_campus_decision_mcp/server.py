"""FastMCP stdio server assembly."""

from __future__ import annotations

import logging
import sys

from mcp.server.fastmcp import FastMCP

from .config import Settings, load_settings
from .constants import SERVER_NAME
from .tools.status import build_status


def configure_logging(level: str) -> None:
    """Keep diagnostics on stderr because stdout belongs exclusively to JSON-RPC."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
        force=True,
    )


def build_server(settings: Settings) -> FastMCP:
    """Create a stdio-ready server with only safe process dependencies captured."""

    server = FastMCP(
        SERVER_NAME,
        instructions="校园数据仅来自本地示例或显式配置的 Hy3，不连接生产系统。",
    )

    @server.tool(name="hy3_campus_status", description="查看安全的 MCP 运行状态和可用能力。")
    def hy3_campus_status() -> dict[str, object]:
        return build_status(settings)

    return server


def main() -> None:
    """Start the MCP stdio loop without writing ordinary output to stdout."""

    settings = load_settings()
    configure_logging(settings.log_level)
    build_server(settings).run(transport="stdio")
