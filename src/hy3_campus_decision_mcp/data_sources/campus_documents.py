"""带共享意图契约、元数据过滤和章节级排序的本地校园文档检索。"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ..constants import ALLOWED_SOURCE_EXTENSIONS
from ..safety.path_policy import WorkspacePathPolicy
from .source_models import CampusDocument


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str] | None:
    if not content.startswith("---\n"):
        return None
    closing_index = content.find("\n---", 4)
    if closing_index == -1:
        return None
    metadata: dict[str, str] = {}
    for line in content[4:closing_index].splitlines():
        if line and ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata, content[closing_index + 4 :].lstrip("\r\n")


def _terms(value: str) -> set[str]:
    """生成英文词和中文二/三元短语，禁止单汉字参与召回。"""

    result = {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 1}
    for sequence in re.findall(r"[\u4e00-\u9fff]+", value):
        for width in (2, 3):
            result.update(
                sequence[index : index + width] for index in range(len(sequence) - width + 1)
            )
    return result


def _sections(body: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    title, paragraphs = "正文", []
    for line in body.splitlines():
        heading = re.match(r"^#{1,6}\s+(.+)$", line.strip())
        if heading:
            if paragraphs:
                sections.extend(_bounded_sections(title, paragraphs))
            title, paragraphs = heading.group(1).strip(), []
        elif line.strip():
            paragraphs.append(line.strip())
    if paragraphs:
        sections.extend(_bounded_sections(title, paragraphs))
    return sections or [("正文", body.strip())]


def _bounded_sections(title: str, paragraphs: list[str]) -> list[tuple[str, str]]:
    chunks: list[tuple[str, str]] = []
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 1 > 700:
            chunks.append((title, current))
            current = ""
        current = f"{current}\n{paragraph}".strip()
    if current:
        chunks.append((title, current))
    return chunks


class CampusDocumentRepository:
    """检索审核过的 Bundle 与本地示例文档。"""

    def __init__(self, path_policy: WorkspacePathPolicy, *, max_files: int) -> None:
        self._path_policy = path_policy
        self._max_files = max_files
        self._contract = self._load_contract()

    def search(self, query: str, *, category: str | None, max_sources: int) -> list[CampusDocument]:
        plan = self._query_plan(query)
        query_terms = _terms(query + " " + " ".join(plan["terms"]))
        candidates: list[tuple[int, CampusDocument]] = []
        for document in self._load_documents():
            if category is not None and document.category != category:
                continue
            if (
                plan["preferred_types"]
                and document.category == "policy"
                and document.document_type not in plan["preferred_types"]
            ):
                continue
            score = self._score(document, query, query_terms, plan)
            if score > 0:
                candidates.append((score, document))
        candidates.sort(key=lambda item: (-item[0], item[1].source_id))
        selected: list[CampusDocument] = []
        used: set[str] = set()
        for group in plan["required_groups"]:
            match = next(
                (
                    doc
                    for _score, doc in candidates
                    if doc.document_type in group and doc.source_id not in used
                ),
                None,
            )
            if match:
                selected.append(match)
                used.add(match.source_id)
        for _score, document in candidates:
            if len(selected) >= max_sources:
                break
            if document.source_id not in used:
                selected.append(document)
                used.add(document.source_id)
        return selected[:max_sources]

    def _score(
        self, document: CampusDocument, query: str, query_terms: set[str], plan: dict[str, Any]
    ) -> int:
        title, section, body = (
            document.title.lower(),
            document.section_title.lower(),
            document.text.lower(),
        )
        phrases = {
            query.strip().lower(),
            *(term.lower() for term in plan["terms"] if len(term) >= 2),
        }
        score = sum(30 for term in phrases if term and term in title)
        score += sum(20 for term in phrases if term and term in section)
        score += sum(8 for term in phrases if term and term in body)
        score += len(query_terms & _terms(title + " " + section)) * 3
        score += len(query_terms & _terms(body))
        if document.document_type in plan["preferred_types"]:
            score += 25 - plan["preferred_types"].index(document.document_type)
        return score

    def _query_plan(self, query: str) -> dict[str, Any]:
        intent = self._detect_intent(query)
        profile = next(
            (item for item in self._contract.get("intents", []) if item["intent"] == intent), {}
        )
        terms = list(profile.get("canonical_terms", []))
        for alias in self._contract.get("aliases", []):
            if alias["trigger"] in query:
                terms.extend([alias["trigger"], *alias.get("terms", [])])
        return {
            "intent": intent,
            "terms": list(dict.fromkeys(terms)),
            "preferred_types": profile.get("preferred_document_types", []),
            "required_groups": profile.get("required_document_groups", []),
        }

    @staticmethod
    def _detect_intent(query: str) -> str:
        if "挂科" in query and (
            "怎么办" in query or "还是" in query or ("补考" in query and "重修" in query)
        ):
            return "failed_course_flow"
        if "奖学金" in query:
            return "scholarship_selection"
        if "勤工助学" in query or "勤工俭学" in query:
            return "work_study"
        if "助学贷款" in query:
            return "student_loan"
        if any(term in query for term in ("困难认定", "助学金", "临时困难补助")):
            return "hardship_aid"
        if any(term in query for term in ("没钱", "交不起学费", "生活费不够")):
            return "financial_difficulty_flow"
        if "补考" in query and any(term in query for term in ("没过", "不及格", "未通过")):
            return "retake_transition"
        if "重修" in query:
            return "retake"
        if "补考" in query or "二考" in query:
            return "second_exam"
        if any(term in query for term in ("挂科", "不及格", "没拿到学分")):
            return "failed_course_flow"
        return "general_policy"

    def _load_contract(self) -> dict[str, Any]:
        path = self._path_policy.root / "policy_bundle" / "policy_query_contract_v0.8.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return {"aliases": [], "intents": []}

    def _load_documents(self) -> list[CampusDocument]:
        return [*self._load_markdown_documents(), *self._load_bundle_documents()]

    def _load_markdown_documents(self) -> list[CampusDocument]:
        root = self._path_policy.root / "campus_documents"
        if not root.is_dir():
            return []
        documents: list[CampusDocument] = []
        file_count = 0
        for path in sorted(root.rglob("*")):
            if file_count >= self._max_files:
                break
            if not path.is_file() or path.suffix.lower() not in ALLOWED_SOURCE_EXTENSIONS:
                continue
            file_count += 1
            try:
                parsed = _parse_frontmatter(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                continue
            if parsed is not None:
                metadata, body = parsed
                documents.extend(self._documents_from_record(metadata, body, path))
        return documents

    def _load_bundle_documents(self) -> list[CampusDocument]:
        root = self._path_policy.root / "policy_bundle"
        bundle, manifest_path = (
            root / "sylulive-policy-bundle-v0.8.jsonl",
            root / "policy-bundle-manifest.json",
        )
        try:
            raw = bundle.read_bytes()
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            contract_raw = (root / "policy_query_contract_v0.8.json").read_bytes()
            if hashlib.sha256(raw).hexdigest() != manifest["documents_sha256"]:
                return []
            if hashlib.sha256(contract_raw).hexdigest() != manifest["intent_contract_sha256"]:
                return []
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError):
            return []
        documents: list[CampusDocument] = []
        for line_number, line in enumerate(raw.decode("utf-8").splitlines(), 1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            documents.extend(
                self._documents_from_record(record, record.get("content", ""), bundle, line_number)
            )
        return documents

    def _documents_from_record(
        self, metadata: dict[str, Any], body: str, path: Path, line_number: int = 0
    ) -> list[CampusDocument]:
        source_id, title = str(metadata.get("source_id", "")), str(metadata.get("title", ""))
        official_text = str(metadata.get("official", "true" if line_number else "")).lower()
        if not source_id or not title or official_text not in {"true", "false"}:
            return []
        sections = _sections(body)
        result: list[CampusDocument] = []
        for index, (section_title, text) in enumerate(sections):
            section_id = source_id if len(sections) == 1 else f"{source_id}:s{index + 1}"
            effective_from = metadata.get("effective_from", metadata.get("effective_date"))
            result.append(
                CampusDocument(
                    source_id=section_id,
                    title=title,
                    source_type=str(metadata.get("source_type", "demonstration")),
                    official=official_text == "true",
                    effective_date=None
                    if effective_from in {None, "", "null"}
                    else str(effective_from),
                    category=str(metadata.get("category", "general")),
                    document_type=str(metadata.get("document_type", "")),
                    department=str(metadata.get("department", "")),
                    effective_to=None
                    if metadata.get("effective_to") in {None, "", "null"}
                    else str(metadata["effective_to"]),
                    section_title=section_title,
                    path=self._path_policy.relative_identifier(path),
                    text=text,
                )
            )
        return result
