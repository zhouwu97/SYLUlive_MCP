"""Hy3 Provider 错误码映射测试。"""

from __future__ import annotations

import httpx
import pytest

from hy3_campus_decision_mcp.config import Hy3Mode, Settings
from hy3_campus_decision_mcp.errors import Hy3ProviderError
from hy3_campus_decision_mcp.hy3.client import Hy3Client
from hy3_campus_decision_mcp.hy3.models import CampusQuestionOutput


def _client(handler) -> Hy3Client:
    return Hy3Client(
        Settings(mode=Hy3Mode.LIVE, api_base="https://hy3.example/v1", api_key="test-key"),
        http_transport=httpx.MockTransport(handler),
    )


@pytest.mark.parametrize(
    ("status_code", "code"),
    [
        (401, "hy3_auth_failed"),
        (403, "hy3_auth_failed"),
        (429, "hy3_rate_limited"),
        (500, "hy3_upstream_unavailable"),
    ],
)
async def test_http_failures_have_stable_codes(status_code: int, code: str) -> None:
    """认证、限流和上游故障不能混成一个通用错误。"""

    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code)

    with pytest.raises(Hy3ProviderError) as captured:
        await _client(handler).generate_structured(
            tool_name="answer_campus_question",
            messages=[{"role": "user", "content": "回答"}],
            output_model=CampusQuestionOutput,
            reasoning_effort="low",
        )
    assert captured.value.code == code


async def test_timeout_is_classified_without_leaking_transport_details() -> None:
    """超时错误消息不得回显请求或密钥细节。"""

    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(Hy3ProviderError) as captured:
        await _client(handler).generate_structured(
            tool_name="answer_campus_question",
            messages=[{"role": "user", "content": "回答"}],
            output_model=CampusQuestionOutput,
            reasoning_effort="low",
        )
    assert captured.value.code == "hy3_timeout"
    assert "test-key" not in str(captured.value)
