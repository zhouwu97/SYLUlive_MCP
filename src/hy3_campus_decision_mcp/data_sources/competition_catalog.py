"""本地演示赛事目录的只读加载。"""

from __future__ import annotations

import json
from typing import Any

from pydantic import TypeAdapter, ValidationError

from ..errors import CampusMcpError
from ..safety.path_policy import WorkspacePathPolicy
from ..schemas.competition import CompetitionCandidate
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

    def from_custom(self, candidates: list[CompetitionCandidate]) -> list[dict[str, Any]]:
        """把用户自定义对象标记为较低证据质量的本地比较输入。"""

        return [
            {
                "name": candidate.name,
                "categories": [candidate.category] if candidate.category else [],
                "recognized": False,
                "recognition_level": "not_provided",
                "recognition_note": candidate.recognition_note or "未提供学校认定说明",
                "difficulty": candidate.difficulty or "not_provided",
                "teamwork": "not_provided",
                "portfolio_value": "not_provided",
                "recommended_weekly_hours": candidate.recommended_weekly_hours or 6,
                "evidence_quality": "custom_input",
                "source_type": "user_supplied",
                "official": False,
            }
            for candidate in candidates
        ]

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
