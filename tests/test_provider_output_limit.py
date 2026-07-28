"""Hy3 原始响应大小限制测试。"""

from __future__ import annotations

import httpx
import pytest

from hy3_campus_decision_mcp.config import Hy3Mode, Settings
from hy3_campus_decision_mcp.errors import Hy3ProviderError
from hy3_campus_decision_mcp.hy3.client import Hy3Client
from hy3_campus_decision_mcp.hy3.models import CampusQuestionOutput


async def test_oversized_provider_response_is_rejected_before_json_decode() -> None:
    """超限响应必须先拒绝，不能进入 JSON 解析或重试。"""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 2048)

    client = Hy3Client(
        Settings(
            mode=Hy3Mode.LIVE,
            api_base="https://hy3.example/v1",
            api_key="test-key",
            max_output_bytes=1_024,
        ),
        http_transport=httpx.MockTransport(handler),
    )
    with pytest.raises(Hy3ProviderError) as captured:
        await client.generate_structured(
            tool_name="answer_campus_question",
            messages=[{"role": "user", "content": "回答"}],
            output_model=CampusQuestionOutput,
            reasoning_effort="low",
        )
    assert captured.value.code == "hy3_output_too_large"
