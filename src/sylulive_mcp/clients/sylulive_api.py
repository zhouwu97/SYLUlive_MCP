"""通过短期 Grant 调用 SYLUlive Go 内部 API。"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx

from ..config import Settings
from ..errors import InternalApiError, ServiceConfigurationError
from ..safety.endpoint_policy import normalize_internal_endpoint


class SyluliveApiClient:
    """复用连接池，并只转发当前请求上下文中的短期 Grant。"""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        grant_provider: Callable[[], str | None],
    ) -> None:
        self._settings = settings
        self._grant_provider = grant_provider
        self._client = httpx.AsyncClient(
            timeout=settings.timeout_seconds,
            follow_redirects=False,
            transport=transport,
        )

    async def aclose(self) -> None:
        """关闭共享连接池。"""

        await self._client.aclose()

    async def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """调用一个固定内部端点，并把故障归一为脱敏领域错误。"""

        grant = self._grant_provider()
        if not grant:
            raise ServiceConfigurationError(
                "grant_missing",
                "Production mode requires a short-lived SYLUlive MCP grant.",
            )
        base = normalize_internal_endpoint(
            self._settings.api_base,
            allow_private_http=self._settings.allow_private_http,
        )
        url = f"{base.rstrip('/')}/{path.lstrip('/')}"
        try:
            async with self._client.stream(
                "POST",
                url,
                json=payload,
                headers={"Authorization": f"Bearer {grant}"},
            ) as response:
                if response.status_code in {401, 403}:
                    raise InternalApiError(
                        "grant_rejected", "The short-lived MCP grant was rejected."
                    )
                if response.status_code == 429:
                    raise InternalApiError("quota_exceeded", "The internal API quota was exceeded.")
                if response.status_code >= 400:
                    raise InternalApiError(
                        "internal_api_error", "The internal API rejected the request."
                    )
                chunks: list[bytes] = []
                received = 0
                async for chunk in response.aiter_bytes():
                    received += len(chunk)
                    if received > self._settings.max_api_response_bytes:
                        raise InternalApiError(
                            "internal_api_response_too_large",
                            "The internal API response exceeded the configured size limit.",
                        )
                    chunks.append(chunk)
        except httpx.TimeoutException as error:
            raise InternalApiError(
                "internal_api_timeout", "The internal API request timed out."
            ) from error
        except httpx.RequestError as error:
            raise InternalApiError(
                "internal_api_unavailable", "The internal API is unavailable."
            ) from error

        try:
            body = json.loads(b"".join(chunks))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise InternalApiError(
                "internal_api_invalid_json", "The internal API returned invalid JSON."
            ) from error
        if not isinstance(body, dict):
            raise InternalApiError(
                "internal_api_invalid_response", "The internal API returned an invalid response."
            )
        if body.get("status") == "error":
            raise InternalApiError(
                "internal_api_rejected", "The internal API could not complete the request."
            )
        return body
