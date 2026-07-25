"""面向 OpenAI 兼容 Provider 的最小证据约束提示词。"""

from __future__ import annotations

import json
from typing import Any


def build_messages(tool_name: str, context: dict[str, Any]) -> list[dict[str, str]]:
    """构造仅允许 JSON 的提示词，阻止模型篡改本地事实归属。"""

    system = (
        "You are Hy3 assisting a campus decision MCP server. Return JSON only. "
        "Use only supplied evidence and deterministic findings. Do not invent policy, "
        "sources, grades, credits, schedules, or competition facts. "
        "Do not add fields outside the requested schema."
    )
    user = json.dumps(
        {"tool": tool_name, "context": context},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
