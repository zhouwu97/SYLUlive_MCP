"""四个核心工具共享的受限运行时依赖。"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from ..config import Hy3Mode, Settings
from ..data_sources import CampusDocumentRepository, CompetitionCatalogRepository
from ..errors import CampusMcpError, Hy3DisabledError
from ..hy3 import Hy3Client
from ..result_envelope import error_envelope
from ..safety.limits import enforce_input_size
from ..safety.path_policy import WorkspacePathPolicy

InputModelT = TypeVar("InputModelT", bound=BaseModel)


class ToolRuntime:
    """集中创建路径、Provider 和只读数据源依赖。"""

    def __init__(self, settings: Settings, *, client: Hy3Client | None = None) -> None:
        self.settings = settings
        self.path_policy = WorkspacePathPolicy(
            settings.campus_root_path,
            max_file_bytes=settings.max_source_file_bytes,
        )
        self.client = client or Hy3Client(settings)
        self.campus_documents = CampusDocumentRepository(
            self.path_policy,
            max_files=settings.max_source_files,
        )
        self.competition_catalog = CompetitionCatalogRepository(self.path_policy)

    async def run_core(self, operation: Callable[[], Awaitable[dict[str, Any]]]) -> dict[str, Any]:
        """统一处理禁用模式、已知错误和未预期内部错误。"""

        if self.settings.mode is Hy3Mode.DISABLED:
            return error_envelope(Hy3DisabledError())
        try:
            return await operation()
        except CampusMcpError as error:
            return error_envelope(error)
        except Exception:
            return {
                "status": "error",
                "code": "internal_error",
                "message": "The tool could not complete the requested analysis.",
            }

    def validate_input(self, model: type[InputModelT], raw: dict[str, Any]) -> InputModelT:
        """先执行统一大小限制，再把验证错误归一成安全错误。"""

        enforce_input_size(raw, self.settings.max_input_chars)
        try:
            return model.model_validate(raw)
        except ValidationError as error:
            message = "Input does not match the required tool schema."
            errors = error.errors(include_url=False)
            if any("competition_count_invalid" in str(item.get("msg", "")) for item in errors):
                raise CampusMcpError(
                    "competition_count_invalid",
                    "比较工具至少需要两项赛事。",
                ) from error
            raise CampusMcpError("invalid_input", message) from error

    def load_json_source(self, relative_path: str) -> tuple[dict[str, Any], str]:
        """通过路径策略加载对象型 JSON，同时只返回相对来源标识。"""

        file_path = self.path_policy.resolve_file(relative_path)
        try:
            value = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise CampusMcpError(
                "source_json_invalid", "The requested JSON source is invalid."
            ) from error
        if not isinstance(value, dict):
            raise CampusMcpError(
                "source_json_invalid", "The requested JSON source must contain an object."
            )
        enforce_input_size(value, self.settings.max_input_chars)
        return value, self.path_policy.relative_identifier(file_path)
