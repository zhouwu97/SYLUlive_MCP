"""MCP 工具的公开输入、输出和版本化 Schema 契约。"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from .config import ServiceMode
from .constants import MCP_CONTRACT_VERSION
from .schemas.academic import AcademicAnalysisInput
from .schemas.tools import (
    AcademicGetSummaryInput,
    AcademicGetSummarySuccess,
    AcademicSummarySuccess,
    CompetitionCompareFactsInput,
    CompetitionCompareSuccess,
    CompetitionDetailsSuccess,
    CompetitionGetDetailsInput,
    CompetitionSearchInput,
    CompetitionSearchSuccess,
    DemoCompetitionCompareFactsInput,
    DemoFindFreeWindowsInput,
    DemoValidatePlanInput,
    FindFreeWindowsInput,
    FreeWindowsSuccess,
    PlanValidationSuccess,
    PolicyGetSourcesInput,
    PolicySearchInput,
    PolicySearchSuccess,
    PolicySourcesSuccess,
    ValidatePlanInput,
)
from .tools import (
    academic_calculate_summary,
    academic_get_summary,
    competition_compare_facts,
    competition_get_details,
    competition_search,
    policy_get_sources,
    policy_search,
    schedule_find_free_windows,
    schedule_validate_plan,
)
from .tools.runtime import ToolRuntime

RawToolHandler = Callable[[ToolRuntime, dict[str, Any]], Awaitable[dict[str, Any]]]


class ErrorEnvelope(BaseModel):
    """所有工具共享的稳定错误响应。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    status: Literal["error"]
    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=500)


def response_type(success_model: type[BaseModel]) -> Any:
    """为成功模型和统一错误信封创建带判别字段的响应类型。"""

    return Annotated[success_model | ErrorEnvelope, Field(discriminator="status")]


@dataclass(frozen=True)
class ToolContract:
    """工具名、公开 Schema 与业务处理器的唯一注册来源。"""

    name: str
    description: str
    input_model: type[BaseModel]
    output_model: Any
    handler: RawToolHandler

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.input_model.model_json_schema()

    @property
    def output_schema(self) -> dict[str, Any]:
        schema = TypeAdapter(self.output_model).json_schema()
        schema["type"] = "object"
        return schema

    @property
    def schema_sha256(self) -> str:
        return schema_digest(self.input_schema, self.output_schema)


_SHARED_TOOL_CONTRACTS: dict[str, ToolContract] = {
    "policy_search": ToolContract(
        "policy_search",
        "检索已发布政策片段；每次最多 4 个查询、20 条结果，不生成最终回答。",
        PolicySearchInput,
        response_type(PolicySearchSuccess),
        policy_search,
    ),
    "policy_get_sources": ToolContract(
        "policy_get_sources",
        "重新核验最多 8 个政策来源的发布、有效期与内容哈希。",
        PolicyGetSourcesInput,
        response_type(PolicySourcesSuccess),
        policy_get_sources,
    ),
    "competition_search": ToolContract(
        "competition_search",
        "按名称或类别检索赛事事实，不生成推荐。",
        CompetitionSearchInput,
        response_type(CompetitionSearchSuccess),
        competition_search,
    ),
    "competition_get_details": ToolContract(
        "competition_get_details",
        "按稳定标识读取最多 5 项赛事的事实详情。",
        CompetitionGetDetailsInput,
        response_type(CompetitionDetailsSuccess),
        competition_get_details,
    ),
}


PRODUCTION_TOOL_CONTRACTS: dict[str, ToolContract] = {
    **_SHARED_TOOL_CONTRACTS,
    "competition_compare_facts": ToolContract(
        "competition_compare_facts",
        "按稳定标识从 Go 服务读取并比较赛事事实，不接受调用方提交的事实字段。",
        CompetitionCompareFactsInput,
        response_type(CompetitionCompareSuccess),
        competition_compare_facts,
    ),
    "academic_get_summary": ToolContract(
        "academic_get_summary",
        "通过当前 Grant 获取最小化学业汇总，不接收课程或成绩明细。",
        AcademicGetSummaryInput,
        response_type(AcademicGetSummarySuccess),
        academic_get_summary,
    ),
    "schedule_find_free_windows": ToolContract(
        "schedule_find_free_windows",
        "通过当前 Grant 获取固定日程，再计算一周空闲窗口。",
        FindFreeWindowsInput,
        response_type(FreeWindowsSuccess),
        schedule_find_free_windows,
    ),
    "schedule_validate_plan": ToolContract(
        "schedule_validate_plan",
        "通过当前 Grant 获取固定日程，再校验候选计划硬约束。",
        ValidatePlanInput,
        response_type(PlanValidationSuccess),
        schedule_validate_plan,
    ),
}


DEMO_TOOL_CONTRACTS: dict[str, ToolContract] = {
    **_SHARED_TOOL_CONTRACTS,
    "competition_compare_facts": ToolContract(
        "competition_compare_facts",
        "使用本地演示事实并列计算画像匹配，不生成推荐。",
        DemoCompetitionCompareFactsInput,
        response_type(CompetitionCompareSuccess),
        competition_compare_facts,
    ),
    "academic_calculate_summary": ToolContract(
        "academic_calculate_summary",
        "使用本地演示快照确定性计算学业汇总。",
        AcademicAnalysisInput,
        response_type(AcademicSummarySuccess),
        academic_calculate_summary,
    ),
    "schedule_find_free_windows": ToolContract(
        "schedule_find_free_windows",
        "使用本地演示课表计算一周空闲窗口。",
        DemoFindFreeWindowsInput,
        response_type(FreeWindowsSuccess),
        schedule_find_free_windows,
    ),
    "schedule_validate_plan": ToolContract(
        "schedule_validate_plan",
        "使用本地演示课表校验候选计划硬约束。",
        DemoValidatePlanInput,
        response_type(PlanValidationSuccess),
        schedule_validate_plan,
    ),
}

# 默认导出生产契约，避免下游误用仅供演示的原始数据输入。
TOOL_CONTRACTS = PRODUCTION_TOOL_CONTRACTS


def contracts_for_mode(mode: ServiceMode) -> dict[str, ToolContract]:
    """按运行模式选择公开工具，禁用模式只保留状态工具。"""

    if mode is ServiceMode.PRODUCTION:
        return PRODUCTION_TOOL_CONTRACTS
    if mode is ServiceMode.DEMO:
        return DEMO_TOOL_CONTRACTS
    return {}


NON_CONTRACT_KEYS = frozenset({"title", "description", "examples"})


def normalize_schema(value: Any) -> Any:
    """移除展示性字段，保留所有影响传输语义的 Schema 约束。"""

    if isinstance(value, dict):
        return {
            key: normalize_schema(child)
            for key, child in sorted(value.items())
            if key not in NON_CONTRACT_KEYS
        }
    if isinstance(value, list):
        return [normalize_schema(child) for child in value]
    return value


def schema_digest(input_schema: dict[str, Any], output_schema: dict[str, Any]) -> str:
    """使用可复现 JSON 编码生成单个工具的输入/输出契约摘要。"""

    normalized = normalize_schema({"input_schema": input_schema, "output_schema": output_schema})
    encoded = json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_contract_manifest() -> dict[str, Any]:
    """生成应提交到仓库的工具契约清单。"""

    return {
        "contract_version": MCP_CONTRACT_VERSION,
        "production_tools": {
            name: {
                "schema_sha256": contract.schema_sha256,
                "input_schema": contract.input_schema,
                "output_schema": contract.output_schema,
            }
            for name, contract in sorted(PRODUCTION_TOOL_CONTRACTS.items())
        },
        "demo_tools": {
            name: {
                "schema_sha256": contract.schema_sha256,
                "input_schema": contract.input_schema,
                "output_schema": contract.output_schema,
            }
            for name, contract in sorted(DEMO_TOOL_CONTRACTS.items())
        },
    }


def committed_manifest_path() -> Path:
    """返回版本化清单在仓库中的固定位置。"""

    return Path(__file__).resolve().parents[2] / "assets" / "contracts" / "sylulive-mcp-v3.json"
