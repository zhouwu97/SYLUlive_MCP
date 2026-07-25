"""可转换为安全工具信封的类型化错误。"""

from __future__ import annotations


class CampusMcpError(Exception):
    """可安全返回给 MCP 客户端的预期领域错误。"""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class Hy3DisabledError(CampusMcpError):
    """模型提供方禁用时调用核心工具所抛出的错误。"""

    def __init__(self) -> None:
        super().__init__("hy3_disabled", "Hy3 provider is disabled; only status is available.")


class SafetyViolationError(CampusMcpError):
    """输入违反本地安全策略时抛出的错误。"""


class InputLimitError(CampusMcpError):
    """输入或来源超过资源限制时抛出的错误。"""


class Hy3ConfigurationError(CampusMcpError):
    """实时模式缺少安全且完整配置时抛出的错误。"""


class Hy3ProviderError(CampusMcpError):
    """外部 Provider 无法返回可用结果时抛出的错误。"""
