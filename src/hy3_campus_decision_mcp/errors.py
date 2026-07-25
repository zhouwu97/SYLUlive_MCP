"""Typed errors converted into safe tool envelopes."""

from __future__ import annotations


class CampusMcpError(Exception):
    """Expected domain error that is safe to return to an MCP client."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class Hy3DisabledError(CampusMcpError):
    """Raised when a core tool is requested with the provider disabled."""

    def __init__(self) -> None:
        super().__init__("hy3_disabled", "Hy3 provider is disabled; only status is available.")
