"""Hy3 Live Provider 端点规范化与安全检查。"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit, urlunsplit

from ..errors import Hy3ConfigurationError


def _is_allowed_http_host(host: str, allow_private_http: bool) -> bool:
    """仅允许回环 HTTP 或显式授权的私网 HTTP，永不允许公网 HTTP。"""

    if host.lower() == "localhost":
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    if address.is_loopback:
        return True
    return allow_private_http and (
        address.is_private or address.is_link_local or address.is_unspecified
    )


def _normalize_hy3_endpoint(
    raw_base: str,
    *,
    allow_private_http: bool,
    resource_path: str,
) -> str:
    """从安全基址生成唯一的 `/v1` Provider 资源端点。"""

    raw_base = raw_base.strip()
    parsed = urlsplit(raw_base)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc or not parsed.hostname:
        raise Hy3ConfigurationError(
            "hy3_endpoint_invalid", "HY3_API_BASE must be an absolute HTTP(S) URL."
        )
    if parsed.username or parsed.password:
        raise Hy3ConfigurationError(
            "hy3_endpoint_userinfo_rejected", "HY3_API_BASE must not contain userinfo."
        )
    if parsed.query:
        raise Hy3ConfigurationError(
            "hy3_endpoint_query_rejected", "HY3_API_BASE must not contain a query."
        )
    if parsed.fragment:
        raise Hy3ConfigurationError(
            "hy3_endpoint_fragment_rejected", "HY3_API_BASE must not contain a fragment."
        )
    try:
        _ = parsed.port
    except ValueError as error:
        raise Hy3ConfigurationError(
            "hy3_endpoint_invalid", "HY3_API_BASE has an invalid port."
        ) from error

    if parsed.scheme == "http" and not _is_allowed_http_host(
        parsed.hostname,
        allow_private_http,
    ):
        raise Hy3ConfigurationError(
            "hy3_public_http_rejected",
            "Public HTTP endpoints are not allowed for Hy3.",
        )

    path = parsed.path.rstrip("/")
    for known_resource in ("/chat/completions", "/messages"):
        if path.endswith(known_resource):
            path = path[: -len(known_resource)].rstrip("/")
            break
    if not path.endswith("/v1"):
        path = f"{path}/v1" if path else "/v1"
    final_path = f"{path}{resource_path}"
    return urlunsplit((parsed.scheme, parsed.netloc, final_path, "", ""))


def normalize_hy3_endpoint(raw_base: str, *, allow_private_http: bool) -> str:
    """从安全基址生成唯一的 OpenAI chat-completions 端点。"""

    return _normalize_hy3_endpoint(
        raw_base,
        allow_private_http=allow_private_http,
        resource_path="/chat/completions",
    )


def normalize_anthropic_messages_endpoint(raw_base: str, *, allow_private_http: bool) -> str:
    """从安全基址生成唯一的 Anthropic Messages 端点。"""

    return _normalize_hy3_endpoint(
        raw_base,
        allow_private_http=allow_private_http,
        resource_path="/messages",
    )
