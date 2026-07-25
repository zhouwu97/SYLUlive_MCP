"""所有工具输入模型共用的严格配置。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictInputModel(BaseModel):
    """禁止未声明字段，避免输入悄悄改变工具语义。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
