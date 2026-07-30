"""候选解释与用户主动对比契约测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from hy3_campus_decision_mcp.config import Hy3Mode, Settings
from hy3_campus_decision_mcp.errors import Hy3ProviderError
from hy3_campus_decision_mcp.hy3.models import CompetitionCandidateExplanationOutput
from hy3_campus_decision_mcp.schemas.competition import ExplainCompetitionCandidatesInput
from hy3_campus_decision_mcp.tools.compare_selected_competitions import (
    compare_selected_competitions,
)
from hy3_campus_decision_mcp.tools.competition_output_guard import (
    validate_candidate_explanation,
)
from hy3_campus_decision_mcp.tools.explain_competition_candidates import (
    explain_competition_candidates,
)
from hy3_campus_decision_mcp.tools.runtime import ToolRuntime

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _user_context() -> dict[str, object]:
    return {
        "profile_version": "a" * 64,
        "grade": "本科三年级",
        "college": "信息学院",
        "major": "软件工程",
        "goals": ["能力提升"],
        "direction_tags": ["程序设计"],
        "skills": [],
        "roles": [],
        "preferred_roles": ["developer"],
        "weekly_hours": 7,
        "accept_long_term_training": False,
        "career_direction": "",
        "experience_level": "beginner",
    }


def _candidate(competition_id: str, order: int) -> dict[str, object]:
    return {
        "competition_id": competition_id,
        "record_hash": f"{order:x}" * 64,
        "group_key": "major_match",
        "rule_order": order,
        "facts": {
            "competition_rating": "A",
            "major_fit_summary_public": "适配软件相关专业",
            "risk_tags": ["long_term_training"],
        },
        "match_dimensions": {
            key: "matched" if key in {"eligibility", "major"} else "unknown"
            for key in (
                "eligibility",
                "major",
                "college",
                "grade",
                "goal",
                "direction",
                "skill",
                "role",
                "time",
                "training",
            )
        },
        "gates": {
            "candidate_pool_allowed": True,
            "personalized_ranking_allowed": False,
            "strong_recommendation_eligible": False,
            "recommendation_permission_level": "low",
            "ai_mode": "candidate_explanation",
        },
    }


async def test_fixture_candidate_explanation_and_selected_comparison_keep_order() -> None:
    runtime = ToolRuntime(
        Settings(
            mode=Hy3Mode.FIXTURE,
            campus_root=PROJECT_ROOT / "examples",
            fixture_root=PROJECT_ROOT / "tests" / "fixtures" / "hy3",
        )
    )
    candidates = [_candidate("NAT-001", 1), _candidate("NAT-002", 2)]
    explained = await explain_competition_candidates(
        runtime,
        {
            "mode": "candidate_explanation",
            "question": "我每周可以投入七小时",
            "user_context": _user_context(),
            "candidates": candidates,
        },
    )
    compared = await compare_selected_competitions(
        runtime,
        {
            "mode": "selected_comparison",
            "user_context": _user_context(),
            "competitions": candidates,
        },
    )
    assert explained["status"] == "ok"
    assert [item["competition_id"] for item in explained["result"]["items"]] == [
        "NAT-001",
        "NAT-002",
    ]
    assert compared["status"] == "ok"
    assert "score" not in str(compared)


def test_candidate_input_rejects_reordered_rule_order_and_closed_gate() -> None:
    candidates = [_candidate("NAT-001", 2), _candidate("NAT-002", 1)]
    with pytest.raises(ValueError):
        ExplainCompetitionCandidatesInput.model_validate(
            {
                "mode": "candidate_explanation",
                "user_context": _user_context(),
                "candidates": candidates,
            }
        )
    candidates = [_candidate("NAT-001", 1)]
    candidates[0]["gates"]["candidate_pool_allowed"] = False  # type: ignore[index]
    with pytest.raises(ValueError):
        ExplainCompetitionCandidatesInput.model_validate(
            {
                "mode": "candidate_explanation",
                "user_context": _user_context(),
                "candidates": candidates,
            }
        )


def test_candidate_output_guard_rejects_added_id_source_and_forbidden_language() -> None:
    output = CompetitionCandidateExplanationOutput.model_validate(
        {
            "summary": "候选解释",
            "items": [
                {
                    "competition_id": "FORGED",
                    "core_reason": "强烈推荐，获奖概率 82%",
                    "reasons": [
                        {
                            "text": "伪造依据",
                            "source_fields": ["internal_score"],
                        }
                    ],
                    "cautions": [],
                    "questions_to_confirm": [],
                }
            ],
        }
    )
    with pytest.raises(Hy3ProviderError):
        validate_candidate_explanation(["NAT-001"], output)
