"""基于本地证据的校园问答工具。"""

from __future__ import annotations

from typing import Any

from ..deterministic.evidence import demo_warning
from ..errors import CampusMcpError
from ..hy3.models import CampusQuestionOutput
from ..hy3.prompts import build_messages
from ..result_envelope import ok_envelope
from ..schemas.campus_question import CampusQuestionInput
from .runtime import ToolRuntime


async def answer_campus_question(
    runtime: ToolRuntime,
    raw: dict[str, Any],
) -> dict[str, Any]:
    """检索本地文档，并让 Hy3 仅在被提供的证据范围内归纳。"""

    async def operation() -> dict[str, Any]:
        request = runtime.validate_input(CampusQuestionInput, raw)
        documents = runtime.campus_documents.search(
            request.query,
            category=request.category,
            max_sources=request.max_sources,
        )
        if not documents:
            raise CampusMcpError(
                "no_reliable_source",
                "No reliable local source was found for this campus question.",
            )
        sources = [document.public_source() for document in documents]
        generated = await runtime.client.generate_structured(
            tool_name="answer_campus_question",
            messages=build_messages(
                "answer_campus_question",
                {
                    "query": request.query,
                    "category": request.category,
                    "evidence": [
                        {
                            "source_id": document.source_id,
                            "title": document.title,
                            "text": document.text,
                        }
                        for document in documents
                    ],
                },
            ),
            output_model=CampusQuestionOutput,
            reasoning_effort="medium",
            allowed_source_ids=[document.source_id for document in documents],
        )
        result = dict(generated.data)
        result.pop("source_ids", None)
        return ok_envelope(
            result=result,
            deterministic_findings={"retrieved_source_count": len(sources)},
            sources=sources,
            warnings=demo_warning(sources),
            settings=runtime.settings,
            reasoning_effort=generated.reasoning_effort,
        )

    return await runtime.run_core(operation)
