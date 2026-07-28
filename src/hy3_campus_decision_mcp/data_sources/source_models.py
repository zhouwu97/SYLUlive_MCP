"""本地示例数据的结构化表示。"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import ConfigDict, Field

from ..schemas.common import StrictInputModel


@dataclass(frozen=True)
class CampusDocument:
    """已通过元数据和路径检查的本地校园文档。"""

    source_id: str
    title: str
    source_type: str
    official: bool
    effective_date: str | None
    category: str
    document_type: str
    department: str
    effective_to: str | None
    section_title: str
    path: str
    text: str

    def public_source(self) -> dict[str, object]:
        """生成不含绝对路径和全文的客户端证据元数据。"""

        return {
            "source_id": self.source_id,
            "title": self.title,
            "path": self.path,
            "source_type": self.source_type,
            "official": self.official,
            "effective_date": self.effective_date,
            "category": self.category,
            "document_type": self.document_type,
            "department": self.department,
            "effective_to": self.effective_to,
            "section_title": self.section_title,
        }


class CompetitionCatalogEntry(StrictInputModel):
    """示例赛事目录的可验证单项记录。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    categories: list[str] = Field(default_factory=list, max_length=10)
    recognized: bool = False
    recognition_level: str = Field(default="not_provided", max_length=100)
    recognition_note: str = Field(default="未提供学校认定说明", max_length=500)
    difficulty: str = Field(default="not_provided", max_length=30)
    teamwork: str = Field(default="not_provided", max_length=100)
    portfolio_value: str = Field(default="not_provided", max_length=100)
    human_evaluation_note: str = Field(default="示例人工评价，仅供比较参考。", max_length=500)
    recommended_weekly_hours: int = Field(default=6, ge=1, le=40)
    evidence_quality: str = Field(default="demonstration", max_length=50)
    source_type: str = Field(default="demonstration", max_length=50)
    official: bool = False
