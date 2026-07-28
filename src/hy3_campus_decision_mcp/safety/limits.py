"""输入到达模型 Provider 前应用的大小限制。"""

from __future__ import annotations

import json
from typing import Any

from ..errors import InputLimitError


def enforce_input_size(value: Any, max_chars: int) -> None:
    """测量规范 JSON 长度，不保留或记录输入内容。"""

    serialized = json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))
    if len(serialized) > max_chars:
        raise InputLimitError("input_too_large", "Input exceeds the configured character limit.")
