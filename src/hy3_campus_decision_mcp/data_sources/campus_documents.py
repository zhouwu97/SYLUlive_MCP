"""本地 Markdown 校园文档的只读检索。"""

from __future__ import annotations

import re

from ..constants import ALLOWED_SOURCE_EXTENSIONS
from ..safety.path_policy import WorkspacePathPolicy
from .source_models import CampusDocument


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str] | None:
    """解析受限 YAML frontmatter，避免为示例数据引入不必要的解析器。"""

    if not content.startswith("---\n"):
        return None
    closing_index = content.find("\n---", 4)
    if closing_index == -1:
        return None
    metadata: dict[str, str] = {}
    for line in content[4:closing_index].splitlines():
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata, content[closing_index + 4 :].lstrip("\r\n")


def _query_terms(value: str) -> set[str]:
    """为中英文示例检索生成简单、可解释的词元集合。"""

    return set(re.findall(r"[\u4e00-\u9fff]|[a-z0-9]+", value.lower()))


class CampusDocumentRepository:
    """在受限工作区中检索带元数据的校园示例文档。"""

    def __init__(self, path_policy: WorkspacePathPolicy, *, max_files: int) -> None:
        self._path_policy = path_policy
        self._max_files = max_files

    def search(self, query: str, *, category: str | None, max_sources: int) -> list[CampusDocument]:
        """按词元重叠排序，绝不在没有本地证据时补造文档。"""

        documents_root = self._path_policy.root / "campus_documents"
        if not documents_root.is_dir():
            return []
        query_terms = _query_terms(query)
        candidates: list[tuple[int, CampusDocument]] = []
        seen_source_ids: set[str] = set()
        file_count = 0
        for candidate in sorted(documents_root.rglob("*")):
            if file_count >= self._max_files:
                break
            if not candidate.is_file() or candidate.suffix.lower() not in ALLOWED_SOURCE_EXTENSIONS:
                continue
            file_count += 1
            try:
                resolved = candidate.resolve()
                if not resolved.is_relative_to(self._path_policy.root):
                    continue
                if resolved.stat().st_size > self._path_policy.max_file_bytes:
                    continue
                content = resolved.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            parsed = _parse_frontmatter(content)
            if parsed is None:
                continue
            metadata, body = parsed
            source_id = metadata.get("source_id", "")
            title = metadata.get("title", "")
            source_type = metadata.get("source_type", "")
            official_text = metadata.get("official", "").lower()
            if not source_id or not title or official_text not in {"true", "false"}:
                continue
            if source_id in seen_source_ids:
                continue
            document = CampusDocument(
                source_id=source_id,
                title=title,
                source_type=source_type or "demonstration",
                official=official_text == "true",
                effective_date=None
                if metadata.get("effective_date") in {None, "", "null"}
                else metadata["effective_date"],
                path=self._path_policy.relative_identifier(resolved),
                text=body,
            )
            title_terms = _query_terms(title)
            body_terms = _query_terms(body)
            score = len(query_terms & title_terms) * 3 + len(query_terms & body_terms)
            if score:
                candidates.append((score, document))
                seen_source_ids.add(source_id)
        candidates.sort(key=lambda item: (-item[0], item[1].source_id))
        return [document for _score, document in candidates[:max_sources]]
