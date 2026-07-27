"""内部 API 地址规范化与安全检查。"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit, urlunsplit

from ..errors import ServiceConfigurationError


def _is_allowed_http_host(host: str, allow_private_http: bool) -> bool:
    """仅允许回环 HTTP 或显式授权的私网 HTTP。"""

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


def normalize_internal_endpoint(raw_base: str, *, allow_private_http: bool) -> str:
    """校验内部 API 根地址，拒绝隐式凭据和可变 URL 组件。"""

    parsed = urlsplit(raw_base.strip())
    if parsed.scheme not in {"https", "http"} or not parsed.netloc or not parsed.hostname:
        raise ServiceConfigurationError(
            "internal_endpoint_invalid", "SYLULIVE_API_BASE must be an absolute HTTP(S) URL."
        )
    if parsed.username or parsed.password:
        raise ServiceConfigurationError(
            "internal_endpoint_userinfo_rejected", "SYLULIVE_API_BASE must not contain userinfo."
        )
    if parsed.query or parsed.fragment:
        raise ServiceConfigurationError(
            "internal_endpoint_components_rejected",
            "SYLULIVE_API_BASE must not contain a query or fragment.",
        )
    try:
        _ = parsed.port
    except ValueError as error:
        raise ServiceConfigurationError(
            "internal_endpoint_invalid", "SYLULIVE_API_BASE has an invalid port."
        ) from error
    if parsed.scheme == "http" and not _is_allowed_http_host(parsed.hostname, allow_private_http):
        raise ServiceConfigurationError(
            "public_http_rejected", "Public HTTP endpoints are not allowed."
        )
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))
