"""针对学业快照的递归敏感字段检测。"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from ..errors import SafetyViolationError

_SENSITIVE_NORMALIZED_FIELDS = frozenset(
    {
        "studentid",
        "studentnumber",
        "name",
        "realname",
        "password",
        "passwd",
        "cookie",
        "cookies",
        "session",
        "accesstoken",
        "refreshtoken",
        "authorization",
        "idcard",
        "identitynumber",
        "phone",
        "mobile",
        "email",
    }
)


def normalize_field_name(field_name: str) -> str:
    """将大小写、分隔符和驼峰变体归一为可比较形式。"""

    return re.sub(r"[^a-z0-9]", "", field_name.lower())


def find_sensitive_field(value: Any) -> str | None:
    """返回首个禁用键名，不检查或返回任何字段值。"""

    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            key_text = str(key)
            if normalize_field_name(key_text) in _SENSITIVE_NORMALIZED_FIELDS:
                return key_text
            found = find_sensitive_field(nested_value)
            if found is not None:
                return found
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested_value in value:
            found = find_sensitive_field(nested_value)
            if found is not None:
                return found
    return None


def reject_sensitive_fields(value: Any) -> None:
    """发现受保护的身份或凭据字段时抛出不包含字段值的错误。"""

    if find_sensitive_field(value) is not None:
        raise SafetyViolationError(
            "sensitive_field_rejected",
            "Academic input contains a prohibited identity or credential field.",
        )
