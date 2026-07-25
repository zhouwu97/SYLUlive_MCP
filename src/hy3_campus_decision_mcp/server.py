"""基于 FastMCP 的 stdio Server 组装。"""

from __future__ import annotations

import logging
import sys
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import ConfigDict

from .config import Hy3Mode, Settings, load_settings
from .constants import SERVER_NAME
from .tools.analyze_academic_snapshot import analyze_academic_snapshot
from .tools.answer_campus_question import answer_campus_question
from .tools.compare_competitions import compare_competitions
from .tools.plan_student_week import plan_student_week
from .tools.runtime import ToolRuntime
from .tools.status import build_status


def configure_logging(level: str) -> None:
    """诊断日志只能写入 stderr，stdout 专供 JSON-RPC 使用。"""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
        force=True,
    )


def _forbid_extra_tool_arguments(server: FastMCP, tool_name: str) -> None:
    """收紧 FastMCP 生成的参数模型，避免协议层静默丢弃额外字段。"""

    # FastMCP 暂无覆写自动参数模型配置的公共接口；注册后必须收紧该模型，
    # 否则协议层会忽略未知字段，破坏工具输入的 `extra="forbid"` 契约。
    tool_manager = getattr(server, "_tool_manager", None)
    if tool_manager is None:
        raise RuntimeError("当前 FastMCP 版本未提供工具管理器")
    tool = tool_manager.get_tool(tool_name)
    if tool is None:
        raise RuntimeError(f"工具未注册：{tool_name}")
    argument_model = tool.fn_metadata.arg_model
    model_config = dict(argument_model.model_config)
    model_config["extra"] = "forbid"
    argument_model.model_config = ConfigDict(**model_config)
    argument_model.model_rebuild(force=True)
    tool.parameters = argument_model.model_json_schema(by_alias=True)


def build_server(settings: Settings) -> FastMCP:
    """创建仅捕获安全进程依赖、可通过 stdio 运行的 Server。"""

    server = FastMCP(
        SERVER_NAME,
        instructions="校园数据仅来自本地示例或显式配置的 Hy3，不连接生产系统。",
    )
    runtime = ToolRuntime(settings)

    @server.tool(name="hy3_campus_status", description="查看安全的 MCP 运行状态和可用能力。")
    def hy3_campus_status() -> dict[str, object]:
        return build_status(settings)

    _forbid_extra_tool_arguments(server, "hy3_campus_status")

    if settings.mode is Hy3Mode.DISABLED:
        return server

    @server.tool(
        name="answer_campus_question",
        description="基于本地校园文档回答问题，并返回可核验来源。",
    )
    async def campus_question_tool(
        query: str,
        category: Literal["policy", "academic", "competition", "general"] | None = None,
        max_sources: int = 5,
    ) -> dict[str, Any]:
        return await answer_campus_question(
            runtime,
            {"query": query, "category": category, "max_sources": max_sources},
        )

    _forbid_extra_tool_arguments(server, "answer_campus_question")

    @server.tool(
        name="compare_competitions",
        description="在学校认定、人工评价、学生适配和证据质量四维比较 2 至 5 项赛事。",
    )
    async def competition_comparison_tool(
        student_profile: dict[str, Any],
        competition_names: list[str] | None = None,
        competitions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return await compare_competitions(
            runtime,
            {
                "competition_names": competition_names,
                "competitions": competitions,
                "student_profile": student_profile,
            },
        )

    _forbid_extra_tool_arguments(server, "compare_competitions")

    @server.tool(
        name="analyze_academic_snapshot",
        description="分析非身份化学业快照，计算学分、挂科和数据完整度。",
    )
    async def academic_snapshot_tool(
        snapshot: dict[str, Any] | None = None,
        snapshot_path: str | None = None,
    ) -> dict[str, Any]:
        return await analyze_academic_snapshot(
            runtime,
            {"snapshot": snapshot, "snapshot_path": snapshot_path},
        )

    _forbid_extra_tool_arguments(server, "analyze_academic_snapshot")

    @server.tool(
        name="plan_student_week",
        description="在固定事件、睡眠、最小时间块和每日上限内安排一周目标。",
    )
    async def student_week_plan_tool(
        schedule: dict[str, Any] | None = None,
        schedule_path: str | None = None,
        goals: list[dict[str, Any]] | None = None,
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await plan_student_week(
            runtime,
            {
                "schedule": schedule,
                "schedule_path": schedule_path,
                "goals": goals if goals is not None else [],
                "constraints": constraints if constraints is not None else {},
            },
        )

    _forbid_extra_tool_arguments(server, "plan_student_week")

    return server


def main() -> None:
    """启动 MCP stdio 循环，禁止向 stdout 写入普通文本。"""

    settings = load_settings()
    configure_logging(settings.log_level)
    build_server(settings).run(transport="stdio")
