"""可转换为安全工具信封的类型化错误。"""

from __future__ import annotations


class CampusMcpError(Exception):
    """可安全返回给 MCP 客户端的预期领域错误。"""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class ServiceDisabledError(CampusMcpError):
    """MCP 核心工具被显式禁用。"""

    def __init__(self) -> None:
        super().__init__("service_disabled", "MCP tools are disabled in the current mode.")


class SafetyViolationError(CampusMcpError):
    """输入违反本地安全策略时抛出的错误。"""


class InputLimitError(CampusMcpError):
    """输入或来源超过资源限制时抛出的错误。"""


class ServiceConfigurationError(CampusMcpError):
    """生产模式缺少安全且完整配置时抛出的错误。"""


class InternalApiError(CampusMcpError):
    """Go 内部 API 无法返回可用结果时抛出的错误。"""
