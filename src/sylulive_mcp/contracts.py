"""MCP 工具的公开输入、输出和版本化 Schema 契约。"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from .constants import MCP_CONTRACT_VERSION
from .schemas.academic import AcademicAnalysisInput
from .schemas.tools import (
    AcademicSummarySuccess,
    CompetitionCompareFactsInput,
    CompetitionCompareSuccess,
    CompetitionDetailsSuccess,
    CompetitionGetDetailsInput,
    CompetitionSearchInput,
    CompetitionSearchSuccess,
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


TOOL_CONTRACTS: dict[str, ToolContract] = {
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
    "competition_compare_facts": ToolContract(
        "competition_compare_facts",
        "并列比较学校认定、人工评价、画像匹配、时间和证据质量，不计算总分。",
        CompetitionCompareFactsInput,
        response_type(CompetitionCompareSuccess),
        competition_compare_facts,
    ),
    "academic_calculate_summary": ToolContract(
        "academic_calculate_summary",
        "确定性计算学分、挂科、GPA 透传和数据完整度，不生成风险叙事。",
        AcademicAnalysisInput,
        response_type(AcademicSummarySuccess),
        academic_calculate_summary,
    ),
    "schedule_find_free_windows": ToolContract(
        "schedule_find_free_windows",
        "扣除固定事件和睡眠后计算一周空闲窗口。",
        FindFreeWindowsInput,
        response_type(FreeWindowsSuccess),
        schedule_find_free_windows,
    ),
    "schedule_validate_plan": ToolContract(
        "schedule_validate_plan",
        "确定性校验候选计划的冲突、单日超限和未安排时长。",
        ValidatePlanInput,
        response_type(PlanValidationSuccess),
        schedule_validate_plan,
    ),
}

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
        "tools": {
            name: {
                "schema_sha256": contract.schema_sha256,
                "input_schema": contract.input_schema,
                "output_schema": contract.output_schema,
            }
            for name, contract in sorted(TOOL_CONTRACTS.items())
        },
    }


def committed_manifest_path() -> Path:
    """返回版本化清单在仓库中的固定位置。"""

    return Path(__file__).resolve().parents[2] / "assets" / "contracts" / "sylulive-mcp-v2.json"
