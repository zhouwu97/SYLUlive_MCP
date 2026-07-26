"""针对“挂科了怎么办”这类流程型问题的演示级检索测试。

生产环境的政策问答走服务端 RAG，不走本仓库的演示 Markdown；这里只保证
演示语料在同一个问题下能同时给出补考与重修两条分支，不会只召回其中一段。
"""

from __future__ import annotations

from hy3_campus_decision_mcp.tools.answer_campus_question import answer_campus_question
from hy3_campus_decision_mcp.tools.runtime import ToolRuntime

FAILED_COURSE_QUERY = "挂科了怎么办，需要补考还是重修"


def test_failed_course_flow_retrieves_both_branches(fixture_runtime: ToolRuntime) -> None:
    """演示语料必须同时命中二次考试和课程重修两份材料。"""

    documents = fixture_runtime.campus_documents.search(
        FAILED_COURSE_QUERY,
        category="policy",
        max_sources=5,
    )

    source_ids = {document.source_id for document in documents}
    assert "demo-policy-010" in source_ids, "缺少二次考试分支的演示材料"
    assert "demo-policy-011" in source_ids, "缺少课程重修分支的演示材料"


def test_failed_course_flow_envelope_keeps_both_sources(
    fixture_runtime: ToolRuntime,
) -> None:
    """工具信封要把两条分支的来源都带出去，并保留演示警告。"""

    result = await_result(fixture_runtime)

    assert result["status"] == "ok"
    source_ids = {source["source_id"] for source in result["sources"]}
    assert {"demo-policy-010", "demo-policy-011"} <= source_ids
    assert result["deterministic_findings"]["retrieved_source_count"] >= 2
    assert result["warnings"], "演示语料必须带出非官方警告"


def await_result(runtime: ToolRuntime) -> dict:
    """在同步测试中执行一次异步工具调用。"""

    import asyncio

    return asyncio.run(
        answer_campus_question(
            runtime,
            {"query": FAILED_COURSE_QUERY, "category": "policy", "max_sources": 5},
        )
    )
