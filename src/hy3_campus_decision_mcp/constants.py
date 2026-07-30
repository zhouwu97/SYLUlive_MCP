"""包内稳定常量。"""

from __future__ import annotations

PACKAGE_VERSION = "0.2.0"
RESULT_SCHEMA_VERSION = "2"
MCP_CONTRACT_VERSION = "sylulive-hy3/2"
SERVER_NAME = "Hy3 Campus Decision Copilot"
ALLOWED_SOURCE_EXTENSIONS = frozenset({".md", ".txt", ".json", ".jsonl", ".csv"})
CORE_TOOL_NAMES = (
    "answer_campus_question",
    "compare_competitions",
    "explain_competition_candidates",
    "compare_selected_competitions",
    "analyze_academic_snapshot",
    "plan_student_week",
)
STATUS_TOOL_NAME = "hy3_campus_status"
