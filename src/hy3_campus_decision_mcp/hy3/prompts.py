"""Minimal evidence-bound prompts for the OpenAI-compatible provider."""

from __future__ import annotations

import json
from typing import Any


def build_messages(tool_name: str, context: dict[str, Any]) -> list[dict[str, str]]:
    """Build a JSON-only prompt that prevents the model from owning local facts."""

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
