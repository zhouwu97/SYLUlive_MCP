"""纯工具型 MCP 的通用结果辅助函数。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .constants import RESULT_SCHEMA_VERSION
from .errors import CampusMcpError


def result_meta(**values: Any) -> dict[str, Any]:
    """生成不含模型信息的结果元数据。"""

    return {
        **values,
        "schema_version": RESULT_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def error_envelope(error: CampusMcpError) -> dict[str, str]:
    """把已知领域错误转为稳定且脱敏的错误契约。"""

    return {"status": "error", "code": error.code, "message": error.message}
