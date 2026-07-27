"""短期不透明 Grant 的请求级上下文。"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar


def parse_bearer_authorization(authorization: str) -> str | None:
    """解析标准 Authorization 值，不依赖具体 HTTP 框架的请求对象。"""

    scheme, separator, value = authorization.partition(" ")
    if separator and scheme.casefold() == "bearer" and value.strip():
        return value.strip()
    return None


class GrantContext:
    """使用 ContextVar 隔离并发 HTTP 请求的短期 Grant。"""

    def __init__(self) -> None:
        self._value: ContextVar[str | None] = ContextVar("sylulive_mcp_request_grant", default=None)

    def current(self) -> str | None:
        """返回当前异步请求绑定的 Grant。"""

        return self._value.get()

    @contextmanager
    def bind(self, grant: str | None) -> Iterator[None]:
        """在上下文内绑定 Grant，并在退出时恢复原值。"""

        token = self._value.set(grant)
        try:
            yield
        finally:
            self._value.reset(token)
