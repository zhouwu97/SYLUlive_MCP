"""面向 MCP 客户端的安全运行状态。"""

from __future__ import annotations

from ..config import ServiceMode, Settings
from ..constants import CORE_TOOL_NAMES, MCP_CONTRACT_VERSION, PACKAGE_VERSION, STATUS_TOOL_NAME
from ..contracts import TOOL_CONTRACTS
from ..data_sources import inspect_policy_bundle


def build_status(settings: Settings) -> dict[str, object]:
    """返回服务与契约事实，不暴露 Grant、身份或绝对路径。"""

    enabled = settings.mode is not ServiceMode.DISABLED
    available_tools = [STATUS_TOOL_NAME, *CORE_TOOL_NAMES] if enabled else [STATUS_TOOL_NAME]
    result: dict[str, object] = {
        "service_version": PACKAGE_VERSION,
        "contract_version": MCP_CONTRACT_VERSION,
        "mode": settings.mode.value,
        "transport": settings.transport.value,
        "workspace": settings.demo_root.name or "examples",
        "grant_configured": settings.has_grant,
        "available_tools": available_tools,
        "tool_contracts": {
            name: {"schema_sha256": TOOL_CONTRACTS[name].schema_sha256}
            for name in CORE_TOOL_NAMES
            if enabled
        },
        "architecture": {
            "model_calls": False,
            "final_answer_generation": False,
            "production_database_access": False,
            "production_data_via_go_api": True,
        },
        "security": {
            "grant_hidden_from_tool_arguments": True,
            "relative_paths_only": True,
            "sensitive_fields_rejected": True,
            "absolute_paths_returned": False,
        },
    }
    if settings.mode is ServiceMode.DEMO:
        result["demo_policy_bundle"] = inspect_policy_bundle(settings.demo_root_path)
    return result
