"""针对 Hy3 端点规范化与网络策略的测试。"""

from __future__ import annotations

import pytest

from hy3_campus_decision_mcp.errors import Hy3ConfigurationError
from hy3_campus_decision_mcp.safety.endpoint_policy import normalize_hy3_endpoint


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://host", "https://host/v1/chat/completions"),
        ("https://host/v1", "https://host/v1/chat/completions"),
        ("https://host/v1/chat/completions", "https://host/v1/chat/completions"),
    ],
)
def test_endpoint_normalization(raw: str, expected: str) -> None:
    """多种合法基址都归并为唯一 chat-completions URL。"""

    assert normalize_hy3_endpoint(raw, allow_private_http=False) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "http://example.com",
        "https://user:password@example.com",
        "https://example.com/v1?api_key=secret",
        "https://example.com/v1#fragment",
        "http://192.168.1.10",
    ],
)
def test_unsafe_endpoints_are_rejected(raw: str) -> None:
    """公网 HTTP、凭据、query、fragment 和未授权私网 HTTP 都应失败。"""

    with pytest.raises(Hy3ConfigurationError):
        normalize_hy3_endpoint(raw, allow_private_http=False)


def test_loopback_and_explicit_private_http_are_allowed() -> None:
    """仅 loopback 或明确授权的私网地址可以使用 HTTP。"""

    assert normalize_hy3_endpoint("http://127.0.0.1:8000", allow_private_http=False).endswith(
        "/v1/chat/completions"
    )
    assert normalize_hy3_endpoint("http://192.168.1.10", allow_private_http=True).endswith(
        "/v1/chat/completions"
    )
