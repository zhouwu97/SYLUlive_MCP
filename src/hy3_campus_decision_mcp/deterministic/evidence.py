"""证据元数据的本地不变量。"""

from __future__ import annotations

from typing import Any


def demo_warning(sources: list[dict[str, Any]]) -> list[str]:
    """只要证据包含演示资料，就附加不可省略的政策提示。"""

    if any(source.get("official") is False for source in sources):
        return ["这是演示文档，不代表学校现行正式政策。"]
    return []
