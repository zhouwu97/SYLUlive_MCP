"""v0.8 共享政策契约和章节级检索回归。"""

from __future__ import annotations

import hashlib
import json

from hy3_campus_decision_mcp.tools.runtime import ToolRuntime


def _types(runtime: ToolRuntime, query: str, category: str = "policy") -> set[str]:
    return {
        item.document_type
        for item in runtime.campus_documents.search(query, category=category, max_sources=6)
    }


def test_financial_aid_aliases_retrieve_specific_policies(fixture_runtime: ToolRuntime) -> None:
    assert "school_student_loan_policy" in _types(fixture_runtime, "交不起学费")
    assert {
        "school_national_grant_policy",
        "school_grant_and_temporary_aid_policy",
    } & _types(fixture_runtime, "没钱吃饭")
    assert "school_work_study_policy" in _types(fixture_runtime, "勤工俭学")


def test_scholarship_and_failed_course_use_scholarship_evidence(
    fixture_runtime: ToolRuntime,
) -> None:
    types = _types(fixture_runtime, "挂科影响奖学金吗")
    assert "school_undergraduate_scholarship_policy" in types
    assert "school_undergraduate_retake_policy" not in types


def test_competition_category_cannot_recall_failed_course_policy(
    fixture_runtime: ToolRuntime,
) -> None:
    documents = fixture_runtime.campus_documents.search(
        "学科竞赛怎么报名", category="competition", max_sources=5
    )
    assert documents
    assert {item.category for item in documents} == {"competition"}
    assert all("failed" not in item.document_type for item in documents)


def test_single_character_overlap_is_not_a_match(fixture_runtime: ToolRuntime) -> None:
    types = _types(fixture_runtime, "重修")
    assert "competition_participation_guide" not in types
    assert "school_undergraduate_retake_policy" in types


def test_bundle_and_contract_match_manifest(fixture_runtime: ToolRuntime) -> None:
    root = fixture_runtime.settings.campus_root_path / "policy_bundle"
    manifest = json.loads((root / "policy-bundle-manifest.json").read_text(encoding="utf-8"))
    assert (
        hashlib.sha256((root / "sylulive-policy-bundle-v0.8.jsonl").read_bytes()).hexdigest()
        == manifest["documents_sha256"]
    )
    assert (
        hashlib.sha256((root / "policy_query_contract_v0.8.json").read_bytes()).hexdigest()
        == manifest["intent_contract_sha256"]
    )
