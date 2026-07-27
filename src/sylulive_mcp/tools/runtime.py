"""纯工具共享的受限运行时依赖。"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from ..auth import GrantContext
from ..clients import SyluliveApiClient
from ..config import ServiceMode, Settings
from ..data_sources import CampusDocumentRepository, CompetitionCatalogRepository
from ..errors import CampusMcpError, ServiceDisabledError
from ..result_envelope import error_envelope
from ..safety.limits import enforce_input_size
from ..safety.path_policy import WorkspacePathPolicy
from ..safety.sensitive_fields import reject_sensitive_fields

LOGGER = logging.getLogger(__name__)
InputModelT = TypeVar("InputModelT", bound=BaseModel)


class InternalApi(Protocol):
    async def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    async def aclose(self) -> None: ...


class ToolRuntime:
    """集中创建内部 API、路径策略和演示数据源依赖。"""

    def __init__(
        self,
        settings: Settings,
        *,
        api_client: InternalApi | None = None,
        api_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self.grants = GrantContext()
        self.api_client = api_client or SyluliveApiClient(
            settings,
            transport=api_transport,
            grant_provider=self.grants.current,
        )
        self.path_policy = WorkspacePathPolicy(
            settings.demo_root_path,
            max_file_bytes=settings.max_source_file_bytes,
        )
        self.campus_documents = CampusDocumentRepository(
            self.path_policy,
            max_files=settings.max_source_files,
        )
        self.competition_catalog = CompetitionCatalogRepository(self.path_policy)

    async def aclose(self) -> None:
        """释放内部 API 连接池。"""

        await self.api_client.aclose()

    async def run(self, operation: Callable[[], Awaitable[dict[str, Any]]]) -> dict[str, Any]:
        """统一处理禁用模式、领域错误和未预期内部错误。"""

        if self.settings.mode is ServiceMode.DISABLED:
            return error_envelope(ServiceDisabledError())
        try:
            return await operation()
        except CampusMcpError as error:
            return error_envelope(error)
        except Exception:
            LOGGER.exception("MCP 工具执行失败")
            return {
                "status": "error",
                "code": "internal_error",
                "message": "The tool could not complete the request.",
            }

    def validate_input(self, model: type[InputModelT], raw: dict[str, Any]) -> InputModelT:
        """先执行大小与敏感字段限制，再做严格 Schema 校验。"""

        enforce_input_size(raw, self.settings.max_input_chars)
        reject_sensitive_fields(raw)
        try:
            return model.model_validate(raw)
        except ValidationError as error:
            raise CampusMcpError(
                "invalid_input", "Input does not match the required tool schema."
            ) from error

    def load_json_source(self, relative_path: str) -> tuple[dict[str, Any], str]:
        """通过路径策略加载对象型 JSON，并只返回相对来源标识。"""

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
        reject_sensitive_fields(value)
        return value, self.path_policy.relative_identifier(file_path)
