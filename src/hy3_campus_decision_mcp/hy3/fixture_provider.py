"""读取固定本地 Provider 响应，用于确定性测试和演示。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..errors import Hy3ProviderError


class FixtureProvider:
    """仅从可信 Fixture 目录公开已知工具名称对应的 JSON Fixture。"""

    def __init__(self, fixture_root: Path) -> None:
        self._fixture_root = fixture_root.resolve()

    def load(self, tool_name: str) -> Any:
        """加载单个 Fixture，失败时不返回其绝对文件系统位置。"""

        file_path = (self._fixture_root / f"{tool_name}.json").resolve()
        if not file_path.is_relative_to(self._fixture_root) or not file_path.is_file():
            raise Hy3ProviderError(
                "hy3_fixture_missing", "No fixture response is available for this tool."
            )
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise Hy3ProviderError(
                "hy3_fixture_invalid",
                "The configured Hy3 fixture response is invalid.",
            ) from error
