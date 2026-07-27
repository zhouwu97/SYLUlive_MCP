"""本地政策检索展示入口，不调用模型，也不注册为 MCP 工具。"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from sylulive_mcp.config import ServiceMode, Settings
from sylulive_mcp.tools.policy_search import policy_search
from sylulive_mcp.tools.runtime import ToolRuntime

PROJECT_ROOT = Path(__file__).resolve().parents[1]


async def run_demo(question: str) -> dict[str, object]:
    """返回检索片段，明确不把拼接文本冒充正式回答。"""

    runtime = ToolRuntime(Settings(mode=ServiceMode.DEMO, demo_root=PROJECT_ROOT / "examples"))
    retrieval = await policy_search(
        runtime,
        {"queries": [question], "historical_mode": "forbid", "limit": 5},
    )
    if retrieval.get("status") != "ok":
        return retrieval
    return {
        "status": "demo_only",
        "question": question,
        "notice": "以下内容仅为本地检索片段，不是 Agent 生成的正式回答。",
        "sources": retrieval["results"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="演示本地校园政策资料检索")
    parser.add_argument("question", help="需要检索的校园问题")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run_demo(args.question)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
