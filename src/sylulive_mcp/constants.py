"""包内稳定常量。"""

PACKAGE_VERSION = "0.2.0"
RESULT_SCHEMA_VERSION = "2"
MCP_CONTRACT_VERSION = "sylulive-mcp/2"
SERVER_NAME = "SYLUlive MCP Tools"
ALLOWED_SOURCE_EXTENSIONS = frozenset({".md", ".txt", ".json", ".jsonl", ".csv"})
CORE_TOOL_NAMES = (
    "policy_search",
    "policy_get_sources",
    "competition_search",
    "competition_get_details",
    "competition_compare_facts",
    "academic_calculate_summary",
    "schedule_find_free_windows",
    "schedule_validate_plan",
)
STATUS_TOOL_NAME = "system_status"
