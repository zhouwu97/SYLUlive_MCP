"""Anthropic Messages Provider 适配测试。"""

from __future__ import annotations

import json

import httpx
import pytest

from hy3_campus_decision_mcp.config import Hy3Mode, Hy3Protocol, Settings
from hy3_campus_decision_mcp.errors import Hy3ProviderError
from hy3_campus_decision_mcp.hy3.client import Hy3Client
from hy3_campus_decision_mcp.hy3.models import CompetitionOutput
from hy3_campus_decision_mcp.safety.endpoint_policy import (
    normalize_anthropic_messages_endpoint,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://host", "https://host/v1/messages"),
        ("https://host/v1", "https://host/v1/messages"),
        ("https://host/v1/messages", "https://host/v1/messages"),
        ("https://host/v1/chat/completions", "https://host/v1/messages"),
    ],
)
def test_anthropic_endpoint_normalization(raw: str, expected: str) -> None:
    """两种协议切换时必须去掉旧资源路径。"""

    assert normalize_anthropic_messages_endpoint(raw, allow_private_http=False) == expected


async def test_anthropic_messages_request_uses_shared_safety_limits() -> None:
    """Anthropic 请求应隔离 system 指令并只解析文本块。"""

    requests: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requests.append(payload)
        assert request.url == "https://hy3.example/v1/messages"
        assert request.headers["x-api-key"] == "test-key"
        assert request.headers["anthropic-version"] == "2023-06-01"
        return httpx.Response(
            200,
            json={
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "recommendation": "优先选择匹配当前目标的赛事。",
                                "rationale": "确定性比较支持该结论。",
                                "considerations": ["确认当年认定规则。"],
                            },
                            ensure_ascii=False,
                        ),
                    }
                ]
            },
        )

    client = Hy3Client(
        Settings(
            mode=Hy3Mode.LIVE,
            protocol=Hy3Protocol.ANTHROPIC_MESSAGES,
            api_base="https://hy3.example/v1",
            api_key="test-key",
        ),
        http_transport=httpx.MockTransport(handler),
    )
    generated = await client.generate_structured(
        tool_name="compare_competitions",
        messages=[
            {"role": "system", "content": "仅返回结构化结果。"},
            {"role": "user", "content": "请比较赛事。"},
        ],
        output_model=CompetitionOutput,
        reasoning_effort="low",
    )

    assert generated.data["recommendation"] == "优先选择匹配当前目标的赛事。"
    assert requests[0]["max_tokens"] == 2_048
    assert "chat_template_kwargs" not in requests[0]
    assert "仅返回结构化结果。" in requests[0]["system"]
    assert '"recommendation"' in requests[0]["system"]
    assert requests[0]["messages"] == [{"role": "user", "content": "请比较赛事。"}]


async def test_anthropic_uses_common_error_mapping() -> None:
    """Anthropic 路径不能退化为笼统的请求失败。"""

    client = Hy3Client(
        Settings(
            mode=Hy3Mode.LIVE,
            protocol=Hy3Protocol.ANTHROPIC_MESSAGES,
            api_base="https://hy3.example/v1",
            api_key="test-key",
        ),
        http_transport=httpx.MockTransport(lambda _request: httpx.Response(401)),
    )
    with pytest.raises(Hy3ProviderError) as captured:
        await client.generate_structured(
            tool_name="compare_competitions",
            messages=[{"role": "user", "content": "请比较赛事。"}],
            output_model=CompetitionOutput,
            reasoning_effort="low",
        )
    assert captured.value.code == "hy3_auth_failed"


async def test_anthropic_response_obeys_raw_byte_limit() -> None:
    """Anthropic 响应同样必须在 JSON 解析前执行字节上限。"""

    client = Hy3Client(
        Settings(
            mode=Hy3Mode.LIVE,
            protocol=Hy3Protocol.ANTHROPIC_MESSAGES,
            api_base="https://hy3.example/v1",
            api_key="test-key",
            max_output_bytes=1_024,
        ),
        http_transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, content=b"x" * 2_048)
        ),
    )
    with pytest.raises(Hy3ProviderError) as captured:
        await client.generate_structured(
            tool_name="compare_competitions",
            messages=[{"role": "user", "content": "请比较赛事。"}],
            output_model=CompetitionOutput,
            reasoning_effort="low",
        )
    assert captured.value.code == "hy3_output_too_large"
