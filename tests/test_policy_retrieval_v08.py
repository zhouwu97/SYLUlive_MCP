"""v0.8 共享政策契约和章节级检索回归。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from hy3_campus_decision_mcp.config import Hy3Mode, Settings
from hy3_campus_decision_mcp.data_sources.policy_bundle import canonical_policy_sha256
from hy3_campus_decision_mcp.errors import CampusMcpError
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


@pytest.mark.parametrize(
    ("query", "required_types"),
    [
        (
            "挂科了怎么办，奖学金还能评吗",
            {"school_undergraduate_scholarship_policy"},
        ),
        ("有两科不及格还能勤工助学吗", {"school_work_study_policy"}),
        (
            "国家助学金和国家奖学金冲突吗",
            {"school_national_scholarship_policy"},
        ),
    ],
)
def test_contract_priority_controls_mixed_intents(
    fixture_runtime: ToolRuntime, query: str, required_types: set[str]
) -> None:
    assert required_types <= _types(fixture_runtime, query)


def test_retake_fee_difficulty_combines_retake_and_aid_evidence(
    fixture_runtime: ToolRuntime,
) -> None:
    types = _types(fixture_runtime, "重修费交不起怎么办")
    assert "school_undergraduate_retake_policy" in types
    assert types & {
        "school_student_loan_policy",
        "school_grant_and_temporary_aid_policy",
        "school_financial_hardship_recognition_policy",
    }


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
    assert manifest["sha256_canonicalization"] == "newline-lf-v1"
    assert (
        canonical_policy_sha256((root / "sylulive-policy-bundle-v0.8.jsonl").read_bytes())
        == manifest["documents_sha256"]
    )
    assert (
        canonical_policy_sha256((root / "policy_query_contract_v0.8.json").read_bytes())
        == manifest["intent_contract_sha256"]
    )


def test_policy_digest_is_stable_across_line_endings() -> None:
    payload_lf = b'{"version":"v0.8"}\n{"source_id":"one"}\n'
    payload_crlf = payload_lf.replace(b"\n", b"\r\n")

    assert canonical_policy_sha256(payload_lf) == canonical_policy_sha256(payload_crlf)


def test_corrupted_policy_bundle_returns_explicit_integrity_error(
    tmp_path: Path,
) -> None:
    source_root = Path(__file__).resolve().parents[1] / "examples"
    shutil.copytree(source_root, tmp_path / "examples")
    bundle = tmp_path / "examples" / "policy_bundle" / "sylulive-policy-bundle-v0.8.jsonl"
    bundle.write_text(bundle.read_text(encoding="utf-8") + " ", encoding="utf-8")
    runtime = ToolRuntime(
        Settings(
            mode=Hy3Mode.FIXTURE,
            campus_root=tmp_path / "examples",
            fixture_root=Path(__file__).resolve().parent / "fixtures" / "hy3",
        )
    )

    with pytest.raises(CampusMcpError) as captured:
        runtime.campus_documents.search("奖学金怎么评", category="policy", max_sources=5)

    assert captured.value.code == "policy_bundle_integrity_failed"
