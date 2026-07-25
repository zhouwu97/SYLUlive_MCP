"""Stable package constants."""

from __future__ import annotations

PACKAGE_VERSION = "0.1.0"
SCHEMA_VERSION = "1"
SERVER_NAME = "Hy3 Campus Decision Copilot"
ALLOWED_SOURCE_EXTENSIONS = frozenset({".md", ".txt", ".json", ".jsonl", ".csv"})
CORE_TOOL_NAMES = (
    "answer_campus_question",
    "compare_competitions",
    "analyze_academic_snapshot",
    "plan_student_week",
)
STATUS_TOOL_NAME = "hy3_campus_status"
