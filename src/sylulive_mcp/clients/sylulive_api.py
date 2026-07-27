"""通过短期 Grant 调用 SYLUlive Go 内部 API。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

from ..config import Settings
from ..errors import InternalApiError, ServiceConfigurationError
from ..safety.endpoint_policy import normalize_internal_endpoint


class SyluliveApiClient:
    """不持有用户身份信息，只转发进程级短期 Grant。"""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        grant_provider: Callable[[], str | None] | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport
        self._grant_provider = grant_provider

    async def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """调用一个固定内部端点，并把故障归一为脱敏领域错误。"""

        contextual_grant = self._grant_provider() if self._grant_provider is not None else None
        grant = contextual_grant or self._settings.grant_token.get_secret_value().strip()
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
            async with httpx.AsyncClient(
                timeout=self._settings.timeout_seconds,
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Authorization": f"Bearer {grant}"},
                )
        except httpx.TimeoutException as error:
            raise InternalApiError(
                "internal_api_timeout", "The internal API request timed out."
            ) from error
        except httpx.RequestError as error:
            raise InternalApiError(
                "internal_api_unavailable", "The internal API is unavailable."
            ) from error

        if response.status_code in {401, 403}:
            raise InternalApiError("grant_rejected", "The short-lived MCP grant was rejected.")
        if response.status_code == 429:
            raise InternalApiError("quota_exceeded", "The internal API quota was exceeded.")
        if response.status_code >= 400:
            raise InternalApiError("internal_api_error", "The internal API rejected the request.")
        try:
            body = response.json()
        except ValueError as error:
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
