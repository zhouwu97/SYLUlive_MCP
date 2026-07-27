"""使用官方 MCP Python SDK 运行五个完整 stdio 协议评测案例。"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters, stdio_client

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_FILE = PROJECT_ROOT / "evaluation" / "mcp-results.json"
EXPECTED_TOOLS = {
    "hy3_campus_status",
    "answer_campus_question",
    "compare_competitions",
    "analyze_academic_snapshot",
    "plan_student_week",
}


def _require_ok(response: Any, tool_name: str) -> dict[str, Any]:
    """确认 SDK 返回了成功的结构化工具结果。"""

    if response.isError or response.structuredContent is None:
        raise AssertionError(
            f"{tool_name} 调用失败：isError={response.isError}; "
            f"structuredContent={response.structuredContent!r}"
        )
    result = response.structuredContent
    if result.get("status") != "ok":
        raise AssertionError(f"{tool_name} 返回非成功状态：{result!r}")
    return result


def _assert_tool_list(tool_names: set[str]) -> None:
    """确认 Fixture 模式精确注册五个公开工具。"""

    if tool_names != EXPECTED_TOOLS:
        raise AssertionError(f"工具集合不一致：{sorted(tool_names)}")


def _record_case(
    details: list[dict[str, str]],
    case_id: str,
    assertion: str,
    operation: Callable[[], Any],
) -> None:
    """执行一个同步断言，并把结果归一成稳定的机器可读记录。"""

    try:
        operation()
    except Exception as error:
        details.append(
            {"id": case_id, "status": "failed", "assertion": assertion, "reason": str(error)}
        )
    else:
        details.append({"id": case_id, "status": "passed", "assertion": assertion})


async def verify_stdio_protocol() -> dict[str, Any]:
    """通过子进程完成 initialize、tools/list 与四个 tools/call 案例。"""

    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "hy3_campus_decision_mcp"],
        cwd=PROJECT_ROOT,
        env={
            "HY3_MODE": "fixture",
            "HY3_CAMPUS_ROOT": "./examples",
            "HY3_FIXTURE_ROOT": "./tests/fixtures/hy3",
        },
    )
    details: list[dict[str, str]] = []
    async with stdio_client(parameters, errlog=sys.stderr) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            initialized = await session.initialize()
            tools = await session.list_tools()
            tool_names = {tool.name for tool in tools.tools}
            _record_case(
                details,
                "e2e-01",
                "tools/list 精确返回五个公开工具",
                lambda: _assert_tool_list(tool_names),
            )

            academic_response = await session.call_tool(
                "analyze_academic_snapshot",
                {"snapshot_path": "academic/safe_snapshot.json"},
            )
            _record_case(
                details,
                "e2e-02",
                "学业分析通过 MCP 返回结构化成功结果",
                lambda: _require_ok(academic_response, "analyze_academic_snapshot"),
            )

            competition_response = await session.call_tool(
                "compare_competitions",
                {
                    "competition_names": ["蓝桥杯", "中国国际大学生创新大赛"],
                    "student_profile": {
                        "major": "计算机科学与技术",
                        "grade": "大三",
                        "weekly_hours": 8,
                    },
                },
            )
            _record_case(
                details,
                "e2e-03",
                "竞赛比较通过 MCP 保持四维结果分离",
                lambda: _assert_competition_result(
                    _require_ok(competition_response, "compare_competitions")
                ),
            )

            plan_response = await session.call_tool(
                "plan_student_week",
                {
                    "schedule_path": "schedules/sample_week.json",
                    "goals": [{"name": "准备蓝桥杯", "weekly_minutes": 360, "priority": "high"}],
                    "constraints": {},
                },
            )
            _record_case(
                details,
                "e2e-04",
                "周计划通过 MCP 返回经硬约束复核的结果",
                lambda: _assert_plan_result(_require_ok(plan_response, "plan_student_week")),
            )

            rejected_response = await session.call_tool(
                "analyze_academic_snapshot",
                {"snapshot_path": "../secret.env"},
            )
            _record_case(
                details,
                "e2e-05",
                "路径越界通过 MCP 返回 path_traversal_rejected",
                lambda: _assert_path_rejection(rejected_response),
            )

    passed = sum(case["status"] == "passed" for case in details)
    total = len(details)
    return {
        "benchmark_version": "mcp-protocol-v1",
        "case_count": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate_percent": round(passed / total * 100, 2),
        "server": initialized.serverInfo.name,
        "cases": details,
    }


def _assert_competition_result(result: dict[str, Any]) -> None:
    """确认完整协议结果没有把四个赛事维度压缩成综合分。"""

    comparisons = result.get("deterministic_findings", {}).get("comparisons", [])
    required = {"school_recognition", "human_evaluation", "student_fit", "evidence_quality"}
    if len(comparisons) != 2:
        raise AssertionError("竞赛比较没有返回两个候选项")
    if any(not required.issubset(item) or "score" in item for item in comparisons):
        raise AssertionError("竞赛维度缺失或被压缩为综合分")


def _assert_plan_result(result: dict[str, Any]) -> None:
    """确认服务端硬约束复核通过后返回了完整计划。"""

    findings = result.get("deterministic_findings", {})
    if not findings.get("plan") or findings.get("total_scheduled_minutes") != 360:
        raise AssertionError("周计划未完整安排 360 分钟目标")


def _assert_path_rejection(response: Any) -> None:
    """确认危险路径以业务错误信封安全失败。"""

    result = response.structuredContent
    if response.isError or result is None:
        raise AssertionError("路径拒绝没有返回结构化业务错误")
    if result.get("status") != "error" or result.get("code") != "path_traversal_rejected":
        raise AssertionError(f"路径拒绝错误码不稳定：{result!r}")


def main() -> None:
    """执行协议评测，写入或核对不含敏感信息的稳定结果。"""

    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="更新提交的机器可读结果")
    mode.add_argument("--check", action="store_true", help="核对提交结果与当前实现一致")
    args = parser.parse_args()

    result = asyncio.run(verify_stdio_protocol())
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        RESULTS_FILE.write_text(encoded, encoding="utf-8", newline="\n")
    elif args.check:
        if not RESULTS_FILE.is_file() or RESULTS_FILE.read_text(encoding="utf-8") != encoded:
            raise SystemExit("evaluation/mcp-results.json 与当前 MCP 协议实现不一致")

    summary = {key: result[key] for key in ("case_count", "passed", "failed", "pass_rate_percent")}
    print(json.dumps(summary, ensure_ascii=False))
    if result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
