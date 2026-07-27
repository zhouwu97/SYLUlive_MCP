"""版本化 MCP Schema 契约的回归测试。"""

from __future__ import annotations

import json

from hy3_campus_decision_mcp.config import Hy3Mode, Settings
from hy3_campus_decision_mcp.constants import MCP_CONTRACT_VERSION
from hy3_campus_decision_mcp.contracts import (
    TOOL_CONTRACTS,
    build_contract_manifest,
    committed_manifest_path,
    schema_digest,
)
from hy3_campus_decision_mcp.tools.status import build_status


def test_committed_contract_manifest_is_current() -> None:
    """模型变更后若忘记更新提交清单，测试必须直接失败。"""

    committed = json.loads(committed_manifest_path().read_text(encoding="utf-8"))
    assert build_contract_manifest() == committed


def test_core_contracts_publish_input_and_output_object_schemas() -> None:
    """所有核心工具都必须声明可供客户端校验的双向 Schema。"""

    assert set(TOOL_CONTRACTS) == {
        "answer_campus_question",
        "compare_competitions",
        "analyze_academic_snapshot",
        "plan_student_week",
    }
    for contract in TOOL_CONTRACTS.values():
        assert contract.input_schema["type"] == "object"
        assert contract.output_schema["type"] == "object"
        assert len(contract.schema_sha256) == 64


def test_schema_digest_ignores_presentation_and_preserves_validation_rules() -> None:
    """标题变化不应破坏兼容性，但范围变化必须改变契约摘要。"""

    base_input = {"type": "object", "properties": {"limit": {"maximum": 5}}}
    base_output = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    presentation_input = {
        **base_input,
        "title": "展示标题",
        "description": "展示说明",
    }
    changed_input = {"type": "object", "properties": {"limit": {"maximum": 6}}}

    assert schema_digest(base_input, base_output) == schema_digest(presentation_input, base_output)
    assert schema_digest(base_input, base_output) != schema_digest(changed_input, base_output)


def test_status_declares_current_core_contract_hashes(tmp_path) -> None:
    """状态工具仅返回摘要，但其值必须与 tools/list 的契约来源一致。"""

    settings = Settings(mode=Hy3Mode.FIXTURE, campus_root=tmp_path)
    status = build_status(settings)

    assert status["contract_version"] == MCP_CONTRACT_VERSION
    assert status["tool_contracts"] == {
        name: {"schema_sha256": contract.schema_sha256} for name, contract in TOOL_CONTRACTS.items()
    }
    assert status["policy_bundle_loaded"] is False
    assert status["policy_bundle_version"] is None
    assert status["policy_bundle_sha256"] is None
    assert status["intent_contract_loaded"] is False
