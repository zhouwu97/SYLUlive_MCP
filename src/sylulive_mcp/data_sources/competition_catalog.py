"""本地演示赛事目录的只读加载。"""

from __future__ import annotations

import json
from typing import Any

from pydantic import TypeAdapter, ValidationError

from ..errors import CampusMcpError
from ..safety.path_policy import WorkspacePathPolicy
from .source_models import CompetitionCatalogEntry

_CATALOG_PATH = "competitions/catalog.json"
_CATALOG_SOURCE = {
    "source_id": "demo-competition-catalog",
    "title": "示例赛事目录",
    "path": _CATALOG_PATH,
    "source_type": "demonstration",
    "official": False,
    "effective_date": None,
}


class CompetitionCatalogRepository:
    """解析少量演示赛事，避免复制或依赖生产目录。"""

    def __init__(self, path_policy: WorkspacePathPolicy) -> None:
        self._path_policy = path_policy
        self._catalog_adapter = TypeAdapter(list[CompetitionCatalogEntry])

    def source_metadata(self) -> dict[str, object]:
        """提供固定、相对路径化的目录来源信息。"""

        return dict(_CATALOG_SOURCE)

    def resolve_names(self, names: list[str]) -> list[dict[str, Any]]:
        """按名称查找目录记录，未知名称不会被模型自行补全。"""

        catalog = self._load_catalog()
        by_name = {entry.name.casefold(): entry for entry in catalog}
        resolved: list[dict[str, Any]] = []
        for name in names:
            entry = by_name.get(name.strip().casefold())
            if entry is None:
                raise CampusMcpError(
                    "competition_not_found",
                    "A requested competition is not present in the local demonstration catalog.",
                )
            resolved.append(entry.model_dump(mode="json"))
        return resolved

    def list_entries(self) -> list[CompetitionCatalogEntry]:
        """返回已验证的完整演示目录。"""

        return self._load_catalog()

    def _load_catalog(self) -> list[CompetitionCatalogEntry]:
        """从路径策略授权的 JSON 文件读取并验证目录。"""

        file_path = self._path_policy.resolve_file(_CATALOG_PATH)
        try:
            raw = json.loads(file_path.read_text(encoding="utf-8"))
            payload = raw["competitions"] if isinstance(raw, dict) else raw
            return self._catalog_adapter.validate_python(payload)
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            KeyError,
            ValidationError,
        ) as error:
            raise CampusMcpError(
                "competition_catalog_invalid",
                "The local competition catalog is invalid.",
            ) from error
