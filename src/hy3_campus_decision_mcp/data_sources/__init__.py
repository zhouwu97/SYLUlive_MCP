"""只读本地示例数据访问层。"""

from .campus_documents import CampusDocumentRepository
from .competition_catalog import CompetitionCatalogRepository

__all__ = ["CampusDocumentRepository", "CompetitionCatalogRepository"]
