"""Recursive sensitive-field detection for academic snapshots."""

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
    """Normalize case, separators, and camel-case variants into one comparable form."""

    return re.sub(r"[^a-z0-9]", "", field_name.lower())


def find_sensitive_field(value: Any) -> str | None:
    """Return the first prohibited key without inspecting or returning any field value."""

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
    """Raise a value-free error when protected identity or credential fields are present."""

    if find_sensitive_field(value) is not None:
        raise SafetyViolationError(
            "sensitive_field_rejected",
            "Academic input contains a prohibited identity or credential field.",
        )
