"""MCP stdio Server 的命令行入口。"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence

from .constants import PACKAGE_VERSION
from .selfcheck import verify_stdio_protocol
from .server import main as serve_main


def build_parser() -> argparse.ArgumentParser:
    """创建不干扰 stdio 默认启动方式的命令行解析器。"""

    parser = argparse.ArgumentParser(prog="hy3-campus-decision-mcp")
    parser.add_argument("--version", action="store_true", help="输出版本后退出")
    parser.add_argument("--selfcheck", action="store_true", help="执行 Fixture stdio 自检后退出")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """按参数输出元数据、自检，或启动 MCP stdio Server。"""

    args = build_parser().parse_args(argv)
    if args.version:
        print(PACKAGE_VERSION)
        return
    if args.selfcheck:
        print(json.dumps(asyncio.run(verify_stdio_protocol()), ensure_ascii=False))
        return
    serve_main()


if __name__ == "__main__":
    main()
