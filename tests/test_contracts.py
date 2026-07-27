"""版本化工具契约测试。"""

from __future__ import annotations

import json

from sylulive_mcp.constants import CORE_TOOL_NAMES, MCP_CONTRACT_VERSION
from sylulive_mcp.contracts import TOOL_CONTRACTS, build_contract_manifest, committed_manifest_path


def test_tool_registry_matches_v2_architecture() -> None:
    assert MCP_CONTRACT_VERSION == "sylulive-mcp/2"
    assert tuple(TOOL_CONTRACTS) == CORE_TOOL_NAMES
    assert "answer_campus_question" not in TOOL_CONTRACTS


def test_contracts_publish_strict_object_schemas() -> None:
    for contract in TOOL_CONTRACTS.values():
        assert contract.input_schema["type"] == "object"
        assert contract.input_schema["additionalProperties"] is False
        assert contract.output_schema["type"] == "object"
        assert len(contract.schema_sha256) == 64


def test_committed_contract_manifest_is_current() -> None:
    committed = json.loads(committed_manifest_path().read_text(encoding="utf-8"))
    assert committed == build_contract_manifest()
