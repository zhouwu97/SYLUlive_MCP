"""校园问答工具的输入模型。"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .common import StrictInputModel


class CampusQuestionInput(StrictInputModel):
    """限定检索范围和可返回的本地证据数量。"""

    query: str = Field(min_length=1, max_length=6_000)
    category: Literal["policy", "academic", "competition", "general"] | None = None
    max_sources: int = Field(default=5, ge=1, le=20)
