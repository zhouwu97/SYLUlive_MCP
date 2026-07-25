"""具备明确 Live、Fixture 与 Disabled 模式的 OpenAI 兼容 Hy3 客户端。"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal, TypeVar

import httpx
from pydantic import BaseModel

from ..config import Hy3Mode, Settings
from ..errors import Hy3ConfigurationError, Hy3DisabledError, Hy3ProviderError
from ..safety.endpoint_policy import normalize_hy3_endpoint
from .fixture_provider import FixtureProvider
from .output_validation import validate_provider_output

OutputModelT = TypeVar("OutputModelT", bound=BaseModel)
ReasoningEffort = Literal["no_think", "low", "high"]


@dataclass(frozen=True)
class GeneratedOutput:
    """经过校验的 Provider 负载及工具策略指定的推理强度。"""

    data: dict[str, Any]
    reasoning_effort: ReasoningEffort


class Hy3Client:
    """绝不从 Live 静默降级为 Fixture 的 Provider 适配器。"""

    def __init__(
        self,
        settings: Settings,
        *,
        http_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._fixture_provider = FixtureProvider(settings.fixture_root_path)
        self._http_transport = http_transport

    async def generate_structured(
        self,
        *,
        tool_name: str,
        messages: list[dict[str, str]],
        output_model: type[OutputModelT],
        reasoning_effort: ReasoningEffort,
        allowed_source_ids: Iterable[str] = (),
    ) -> GeneratedOutput:
        """根据当前模式生成并校验由工具拥有的叙事内容。"""

        if self._settings.mode is Hy3Mode.DISABLED:
            raise Hy3DisabledError()

        if self._settings.mode is Hy3Mode.FIXTURE:
            parsed = validate_provider_output(
                self._fixture_provider.load(tool_name),
                output_model,
                allowed_source_ids=allowed_source_ids,
            )
        else:
            parsed = await self._request_live(
                messages=messages,
                reasoning_effort=reasoning_effort,
                output_model=output_model,
                allowed_source_ids=allowed_source_ids,
            )
        return GeneratedOutput(
            data=parsed.model_dump(mode="json"),
            reasoning_effort=reasoning_effort,
        )

    async def _request_live(
        self,
        *,
        messages: list[dict[str, str]],
        reasoning_effort: ReasoningEffort,
        output_model: type[OutputModelT],
        allowed_source_ids: Iterable[str],
    ) -> OutputModelT:
        """调用端点，并在结构化返回不合格时仅重试一次。"""

        if not self._settings.has_api_key:
            raise Hy3ConfigurationError(
                "hy3_api_key_missing",
                "HY3_API_KEY is required when HY3_MODE=live.",
            )
        endpoint = normalize_hy3_endpoint(
            self._settings.api_base,
            allow_private_http=self._settings.allow_private_http,
        )
        request_messages = list(messages)
        for attempt in range(2):
            raw_content = await self._post_completion(
                endpoint=endpoint,
                messages=request_messages,
                reasoning_effort=reasoning_effort,
            )
            try:
                raw_output = json.loads(raw_content)
                return validate_provider_output(
                    raw_output,
                    output_model,
                    allowed_source_ids=allowed_source_ids,
                )
            except Hy3ProviderError as error:
                if error.code == "hy3_source_reference_invalid":
                    raise
                if attempt == 1:
                    raise
                request_messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous response did not match the required JSON schema. "
                            "Return only a valid object with the requested fields."
                        ),
                    }
                )
            except (TypeError, json.JSONDecodeError) as error:
                if attempt == 1:
                    raise Hy3ProviderError(
                        "hy3_output_invalid",
                        "Hy3 did not return a valid structured response.",
                    ) from error
                request_messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous response was not valid JSON. "
                            "Return only the required JSON object."
                        ),
                    }
                )
        raise AssertionError("The bounded retry loop must return or raise.")

    async def _post_completion(
        self,
        *,
        endpoint: str,
        messages: list[dict[str, str]],
        reasoning_effort: ReasoningEffort,
    ) -> str:
        """发起禁止重定向的 chat-completions 请求，并提取单个文本内容字段。"""

        payload = {
            "model": self._settings.model_name,
            "messages": messages,
            "temperature": self._settings.default_temperature,
            "top_p": self._settings.default_top_p,
            "chat_template_kwargs": {"reasoning_effort": reasoning_effort},
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self._settings.api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._settings.timeout_seconds,
                follow_redirects=False,
                transport=self._http_transport,
            ) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
            if response.is_redirect:
                raise Hy3ProviderError(
                    "hy3_redirect_rejected",
                    "Hy3 endpoint returned a redirect, which is not allowed.",
                )
            response.raise_for_status()
            decoded = response.json()
            content = decoded["choices"][0]["message"]["content"]
        except Hy3ProviderError:
            raise
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
            raise Hy3ProviderError(
                "hy3_request_failed",
                "Hy3 request failed or returned an unsupported response.",
            ) from error

        if not isinstance(content, str):
            raise Hy3ProviderError(
                "hy3_output_invalid",
                "Hy3 did not return text JSON content.",
            )
        return content
