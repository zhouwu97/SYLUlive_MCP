"""只读本地示例数据访问层。"""

from .campus_documents import CampusDocumentRepository
from .competition_catalog import CompetitionCatalogRepository
from .policy_bundle import inspect_policy_bundle

__all__ = [
    "CampusDocumentRepository",
    "CompetitionCatalogRepository",
    "inspect_policy_bundle",
]
