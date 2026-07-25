"""确保诊断数据结构不含密钥的小型辅助函数。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .sensitive_fields import normalize_field_name

_REDACTED = "[REDACTED]"
_SECRET_KEYS = frozenset(
    {
        "apikey",
        "authorization",
        "password",
        "passwd",
        "cookie",
        "cookies",
        "session",
        "accesstoken",
        "refreshtoken",
    }
)


def redact_for_log(value: Any) -> Any:
    """在诊断日志前递归脱敏形似凭据的映射值。"""

    if isinstance(value, Mapping):
        return {
            str(key): _REDACTED
            if normalize_field_name(str(key)) in _SECRET_KEYS
            else redact_for_log(nested)
            for key, nested in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact_for_log(nested) for nested in value]
    return value
