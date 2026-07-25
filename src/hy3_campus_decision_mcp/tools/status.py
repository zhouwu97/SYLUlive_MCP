"""面向 MCP 客户端的安全运行时诊断。"""

from __future__ import annotations

from ..config import Hy3Mode, Settings
from ..constants import CORE_TOOL_NAMES, PACKAGE_VERSION, STATUS_TOOL_NAME


def build_status(settings: Settings) -> dict[str, object]:
    """返回有用配置事实，同时不暴露密钥或绝对路径。"""

    core_tools_available = settings.mode is not Hy3Mode.DISABLED
    available_tools = [STATUS_TOOL_NAME]
    if core_tools_available:
        available_tools.extend(CORE_TOOL_NAMES)
    workspace_identifier = settings.campus_root.name or "campus_root"

    return {
        "service_version": PACKAGE_VERSION,
        "mode": settings.mode.value,
        "model": settings.model_name,
        "api_key_configured": settings.has_api_key,
        "workspace": workspace_identifier,
        "available_tools": available_tools,
        "available_data_sources": {
            "campus_documents": "campus_documents",
            "competition_catalog": "competitions/catalog.json",
            "academic_examples": "academic",
            "schedule_examples": "schedules",
        },
        "security": {
            "relative_paths_only": True,
            "sensitive_fields_rejected": True,
            "public_http_allowed": False,
            "private_http_allowed": settings.allow_private_http,
            "absolute_paths_returned": False,
        },
    }
