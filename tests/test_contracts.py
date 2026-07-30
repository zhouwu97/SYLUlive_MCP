"""版本化工具契约测试。"""

from __future__ import annotations

import json

from sylulive_mcp.constants import CORE_TOOL_NAMES, DEMO_TOOL_NAMES, MCP_CONTRACT_VERSION
from sylulive_mcp.contracts import (
    DEMO_TOOL_CONTRACTS,
    PRODUCTION_TOOL_CONTRACTS,
    build_contract_manifest,
    committed_manifest_path,
)


def test_tool_registries_separate_production_and_demo_inputs() -> None:
    assert MCP_CONTRACT_VERSION == "sylulive-mcp/4"
    assert tuple(PRODUCTION_TOOL_CONTRACTS) == CORE_TOOL_NAMES
    assert tuple(DEMO_TOOL_CONTRACTS) == DEMO_TOOL_NAMES
    assert "answer_campus_question" not in PRODUCTION_TOOL_CONTRACTS

    academic_properties = PRODUCTION_TOOL_CONTRACTS["academic_get_summary"].input_schema[
        "properties"
    ]
    schedule_properties = PRODUCTION_TOOL_CONTRACTS["schedule_find_free_windows"].input_schema[
        "properties"
    ]
    compare_properties = PRODUCTION_TOOL_CONTRACTS["competition_compare_facts"].input_schema[
        "properties"
    ]
    assert set(academic_properties) == {"semester"}
    assert "schedule" not in schedule_properties
    assert "schedule_path" not in schedule_properties
    assert set(compare_properties) == {"competition_ids", "available_weekly_hours"}
    assert set(
        PRODUCTION_TOOL_CONTRACTS["competition_get_candidate_context"].input_schema["properties"]
    ) == {"competition_ids"}
    assert set(
        PRODUCTION_TOOL_CONTRACTS["competition_verify_records"].input_schema["properties"]
    ) == {"records"}


def test_contracts_publish_strict_object_schemas() -> None:
    for contract in [*PRODUCTION_TOOL_CONTRACTS.values(), *DEMO_TOOL_CONTRACTS.values()]:
        assert contract.input_schema["type"] == "object"
        assert contract.input_schema["additionalProperties"] is False
        assert contract.output_schema["type"] == "object"
        assert len(contract.schema_sha256) == 64


def test_committed_contract_manifest_is_current() -> None:
    committed = json.loads(committed_manifest_path().read_text(encoding="utf-8"))
    assert committed == build_contract_manifest()
