"""Hy3 Live 请求契约测试。"""

from __future__ import annotations

import json

import httpx
import pytest

from hy3_campus_decision_mcp.config import Hy3Mode, Settings
from hy3_campus_decision_mcp.errors import Hy3ProviderError
from hy3_campus_decision_mcp.hy3.client import Hy3Client
from hy3_campus_decision_mcp.hy3.models import CampusQuestionOutput, CompetitionOutput


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
    schema_instruction = requests[0]["messages"][0]["content"]
    assert '"recommendation"' in schema_instruction
    assert '"rationale"' in schema_instruction


async def test_live_request_recovers_hy3_think_tag_wrapped_json() -> None:
    """Hy3 将内部推理标签拼入对象键时，仍应恢复唯一的受约束 JSON 对象。"""

    request_count = 0
    expected = {
        "answer": "同一学年内不能同时获得这两类奖学金。",
        "rationale": "两份政策均明确规定两类奖学金互斥。",
        "source_ids": ["policy-inspirational", "policy-national"],
        "missing_information": [],
    }
    encoded = json.dumps(expected, ensure_ascii=False, separators=(",", ":"))
    malformed = json.dumps(
        {f"{encoded[2:]}</think:trace123><think:trace123></think:trace123>{{": ("answer")},
        ensure_ascii=False,
    )

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": malformed}}]},
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
        tool_name="answer_campus_question",
        messages=[{"role": "user", "content": "请回答奖学金互斥问题。"}],
        output_model=CampusQuestionOutput,
        reasoning_effort="low",
        allowed_source_ids=["policy-inspirational", "policy-national"],
    )

    assert generated.data == expected
    assert request_count == 1


@pytest.mark.parametrize(
    ("suffix", "outer_value"),
    [
        ("", "answer"),
        (" ", "answer"),
        ("</think:trace123>", "answer"),
        ("</think:trace123><think:trace123></think:trace123>{", "模型残留文本"),
    ],
)
async def test_live_request_recovers_observed_think_wrapper_variants(
    suffix: str,
    outer_value: str,
) -> None:
    """已观测变体可缺少尾随左花括号，外层值也不稳定。"""

    expected = {
        "answer": "不能同时获得。",
        "rationale": "两份政策均说明互斥。",
        "source_ids": ["policy-national"],
        "missing_information": [],
    }
    encoded = json.dumps(expected, ensure_ascii=False, separators=(",", ":"))
    malformed = json.dumps(
        {f"{encoded[2:]}{suffix}": outer_value},
        ensure_ascii=False,
    )

    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": malformed}}]},
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
        tool_name="answer_campus_question",
        messages=[{"role": "user", "content": "请回答。"}],
        output_model=CampusQuestionOutput,
        reasoning_effort="low",
        allowed_source_ids=["policy-national"],
    )

    assert generated.data == expected


async def test_live_request_rejects_unknown_single_key_wrapper() -> None:
    """相似单键对象不满足已知包装形状时仍应严格拒绝。"""

    request_count = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {'answer":"伪造回答"}<think>': "answer"},
                                ensure_ascii=False,
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

    with pytest.raises(Hy3ProviderError, match="invalid structured response"):
        await client.generate_structured(
            tool_name="answer_campus_question",
            messages=[{"role": "user", "content": "请回答。"}],
            output_model=CampusQuestionOutput,
            reasoning_effort="low",
            allowed_source_ids=[],
        )

    assert request_count == 2
