"""统一输出信封测试。"""

from __future__ import annotations

from hy3_campus_decision_mcp.result_envelope import ok_envelope


def test_envelope_keeps_local_and_model_owned_fields_separate(fixture_settings) -> None:
    """工具结果必须携带模式、schema 版本和独立确定性区域。"""

    envelope = ok_envelope(
        result={"advice": "演示"},
        deterministic_findings={"credit_gap": 12},
        sources=[{"path": "academic/safe_snapshot.json"}],
        warnings=[],
        settings=fixture_settings,
        reasoning_effort="high",
    )
    assert envelope["status"] == "ok"
    assert envelope["model"]["mode"] == "fixture"
    assert envelope["meta"]["schema_version"] == "1"
    assert envelope["deterministic_findings"]["credit_gap"] == 12
