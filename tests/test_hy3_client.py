"""Hy3 Live 请求契约测试。"""

from __future__ import annotations

import json

import httpx

from hy3_campus_decision_mcp.config import Hy3Mode, Settings
from hy3_campus_decision_mcp.hy3.client import Hy3Client
from hy3_campus_decision_mcp.hy3.models import CompetitionOutput


async def test_live_request_nests_reasoning_effort_in_chat_template_kwargs() -> None:
    """Hy3 推理强度必须使用官方嵌套请求字段。"""

    requests: list[dict[str, object]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert isinstance(payload, dict)
        requests.append(payload)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "recommendation": "优先选择与当前目标匹配的赛事。",
                                    "rationale": "该建议与输入的确定性比较结果一致。",
                                }
                            )
                        }
                    }
                ]
            },
        )

    client = Hy3Client(
        Settings(
            mode=Hy3Mode.LIVE,
            api_base="https://hy3.example/v1",
            api_key="test-key",
        ),
        http_transport=httpx.MockTransport(handler),
    )

    generated = await client.generate_structured(
        tool_name="compare_competitions",
        messages=[{"role": "user", "content": "请返回结构化建议。"}],
        output_model=CompetitionOutput,
        reasoning_effort="low",
    )

    assert generated.reasoning_effort == "low"
    assert len(requests) == 1
    assert "reasoning_effort" not in requests[0]
    assert requests[0]["chat_template_kwargs"] == {"reasoning_effort": "low"}
