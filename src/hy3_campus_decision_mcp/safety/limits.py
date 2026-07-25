"""Size limits applied before an input can reach a model provider."""

from __future__ import annotations

import json
from typing import Any

from ..errors import InputLimitError


def enforce_input_size(value: Any, max_chars: int) -> None:
    """Measure canonical JSON length without retaining or logging the input content."""

    serialized = json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))
    if len(serialized) > max_chars:
        raise InputLimitError("input_too_large", "Input exceeds the configured character limit.")
