"""具备明确 Live、Fixture 与 Disabled 模式的 OpenAI 兼容 Hy3 客户端。"""

from __future__ import annotations

import asyncio
import json
import re
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
_THINK_WRAPPER_SUFFIX = re.compile(
    r"^[ \t\r\n]*(?:</?think:[^<>\s]+>)*\{?[ \t\r\n]*$",
)


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

        allowed_ids = tuple(allowed_source_ids)
        if self._settings.mode is Hy3Mode.DISABLED:
            raise Hy3DisabledError()

        if self._settings.mode is Hy3Mode.FIXTURE:
            fixture_output = self._fixture_provider.load(tool_name)
            if isinstance(fixture_output, dict) and "source_ids" in fixture_output:
                # Fixture 只模拟叙事内容，来源引用必须绑定到本次真实检索结果。
                fixture_output = {**fixture_output, "source_ids": list(allowed_ids)}
            parsed = validate_provider_output(
                fixture_output,
                output_model,
                allowed_source_ids=allowed_ids,
            )
        else:
            parsed = await self._request_live(
                messages=messages,
                reasoning_effort=reasoning_effort,
                output_model=output_model,
                allowed_source_ids=allowed_ids,
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
        """调用端点，并按传输错误或输出错误的类型最多重试一次。"""

        if not self._settings.has_api_key:
            raise Hy3ConfigurationError(
                "hy3_api_key_missing",
                "HY3_API_KEY is required when HY3_MODE=live.",
            )
        endpoint = normalize_hy3_endpoint(
            self._settings.api_base,
            allow_private_http=self._settings.allow_private_http,
        )
        request_messages = _messages_with_output_schema(messages, output_model)
        for attempt in range(2):
            try:
                raw_content = await self._post_completion(
                    endpoint=endpoint,
                    messages=request_messages,
                    reasoning_effort=reasoning_effort,
                )
            except Hy3ProviderError as error:
                if attempt == 1 or error.code not in {
                    "hy3_rate_limited",
                    "hy3_upstream_unavailable",
                    "hy3_connection_failed",
                }:
                    raise
                await asyncio.sleep(0.05 * (attempt + 1))
                continue
            try:
                raw_output = _decode_provider_output(raw_content)
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
                async with client.stream(
                    "POST", endpoint, json=payload, headers=headers
                ) as response:
                    content_length = response.headers.get("content-length")
                    if content_length and content_length.isdigit():
                        if int(content_length) > self._settings.max_output_bytes:
                            raise Hy3ProviderError(
                                "hy3_output_too_large",
                                "Hy3 response exceeded the configured size limit.",
                            )
                    if response.is_redirect:
                        raise Hy3ProviderError(
                            "hy3_redirect_rejected",
                            "Hy3 endpoint returned a redirect, which is not allowed.",
                        )
                    if response.status_code in {401, 403}:
                        raise Hy3ProviderError(
                            "hy3_auth_failed",
                            "Hy3 rejected the configured credentials.",
                        )
                    if response.status_code == 429:
                        raise Hy3ProviderError(
                            "hy3_rate_limited",
                            "Hy3 rate limited the request.",
                        )
                    if response.status_code >= 500:
                        raise Hy3ProviderError(
                            "hy3_upstream_unavailable",
                            "Hy3 returned a server error.",
                        )
                    response.raise_for_status()

                    chunks: list[bytes] = []
                    received = 0
                    async for chunk in response.aiter_bytes():
                        received += len(chunk)
                        if received > self._settings.max_output_bytes:
                            raise Hy3ProviderError(
                                "hy3_output_too_large",
                                "Hy3 response exceeded the configured size limit.",
                            )
                        chunks.append(chunk)
            try:
                decoded = json.loads(b"".join(chunks))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise Hy3ProviderError(
                    "hy3_output_invalid",
                    "Hy3 returned an unsupported response envelope.",
                ) from error
            try:
                content = decoded["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as error:
                raise Hy3ProviderError(
                    "hy3_output_invalid",
                    "Hy3 returned an unsupported response envelope.",
                ) from error
        except Hy3ProviderError:
            raise
        except httpx.TimeoutException as error:
            raise Hy3ProviderError(
                "hy3_timeout",
                "Hy3 request timed out.",
            ) from error
        except httpx.NetworkError as error:
            raise Hy3ProviderError(
                "hy3_connection_failed",
                "Hy3 connection failed.",
            ) from error
        except httpx.HTTPStatusError as error:
            raise Hy3ProviderError(
                "hy3_request_failed",
                "Hy3 rejected the request.",
            ) from error
        if not isinstance(content, str):
            raise Hy3ProviderError(
                "hy3_output_invalid",
                "Hy3 did not return text JSON content.",
            )
        return content


def _messages_with_output_schema(
    messages: list[dict[str, str]],
    output_model: type[BaseModel],
) -> list[dict[str, str]]:
    """将本次调用的严格输出契约发送给 Provider，避免只返回任意 JSON。"""

    schema = json.dumps(
        output_model.model_json_schema(),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    schema_instruction = {
        "role": "system",
        "content": (
            "Return only a JSON object that validates exactly against this JSON Schema. "
            "Include every required field and do not use Markdown. JSON Schema: "
            f"{schema}"
        ),
    }
    return [schema_instruction, *messages]


def _decode_provider_output(raw_content: str) -> Any:
    """解析 JSON，并恢复 Hy3 已知的内部推理标签拼接缺陷。

    恢复仅接受生产中观测到的单键对象形状；恢复结果仍须经过严格输出模型和
    来源白名单校验，不能借此接受任意额外字段或未知来源。
    """

    decoded = json.loads(raw_content)
    if not isinstance(decoded, dict) or len(decoded) != 1:
        return decoded

    malformed_key, malformed_value = next(iter(decoded.items()))
    if not isinstance(malformed_key, str) or not isinstance(malformed_value, str):
        return decoded

    try:
        recovered, end_index = json.JSONDecoder().raw_decode('{"' + malformed_key)
    except json.JSONDecodeError:
        return decoded

    suffix = ('{"' + malformed_key)[end_index:]
    if not isinstance(recovered, dict) or _THINK_WRAPPER_SUFFIX.fullmatch(suffix) is None:
        return decoded
    return recovered
