"""核心工具统一结果信封。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .config import Settings
from .constants import SCHEMA_VERSION
from .errors import CampusMcpError


def ok_envelope(
    *,
    result: dict[str, Any],
    deterministic_findings: dict[str, Any],
    sources: list[dict[str, Any]],
    warnings: list[str],
    settings: Settings,
    reasoning_effort: str,
) -> dict[str, Any]:
    """把模型叙事和本地事实放入明确的独立所有权区域。"""

    return {
        "status": "ok",
        "result": result,
        "deterministic_findings": deterministic_findings,
        "sources": sources,
        "warnings": warnings,
        "model": {
            "provider": "hy3",
            "model": settings.model_name,
            "mode": settings.mode.value,
            "reasoning_effort": reasoning_effort,
        },
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        },
    }


def error_envelope(error: CampusMcpError) -> dict[str, str]:
    """把已知领域错误转为不含内部上下文的稳定错误契约。"""

    return {"status": "error", "code": error.code, "message": error.message}
