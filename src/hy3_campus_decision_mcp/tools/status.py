"""Safe runtime diagnostics for MCP clients."""

from __future__ import annotations

from ..config import Hy3Mode, Settings
from ..constants import CORE_TOOL_NAMES, PACKAGE_VERSION, STATUS_TOOL_NAME


def build_status(settings: Settings) -> dict[str, object]:
    """Return configuration facts that are useful without exposing secrets or absolute paths."""

    core_tools_available = settings.mode is not Hy3Mode.DISABLED
    available_tools = [STATUS_TOOL_NAME]
    if core_tools_available:
        available_tools.extend(CORE_TOOL_NAMES)

    return {
        "service_version": PACKAGE_VERSION,
        "mode": settings.mode.value,
        "model": settings.model_name,
        "api_key_configured": settings.has_api_key,
        "workspace": settings.campus_root.as_posix(),
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
