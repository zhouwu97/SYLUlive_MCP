"""内部 API、路径和运行模式的安全测试。"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from sylulive_mcp.clients import SyluliveApiClient
from sylulive_mcp.config import ServiceMode, Settings
from sylulive_mcp.errors import SafetyViolationError, ServiceConfigurationError
from sylulive_mcp.safety.endpoint_policy import normalize_internal_endpoint
from sylulive_mcp.safety.path_policy import WorkspacePathPolicy
from sylulive_mcp.tools.academic_calculate_summary import academic_calculate_summary
from sylulive_mcp.tools.runtime import ToolRuntime
from sylulive_mcp.tools.status import build_status


def test_internal_endpoint_rejects_public_http_and_url_credentials() -> None:
    with pytest.raises(ServiceConfigurationError):
        normalize_internal_endpoint("http://example.com", allow_private_http=False)
    with pytest.raises(ServiceConfigurationError):
        normalize_internal_endpoint("https://user:pass@example.com", allow_private_http=False)
    assert (
        normalize_internal_endpoint("http://127.0.0.1:8080", allow_private_http=False)
        == "http://127.0.0.1:8080"
    )


async def test_internal_api_injects_grant_only_in_authorization_header() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["Authorization"]
        captured["path"] = request.url.path
        return httpx.Response(200, json={"status": "ok", "results": []})

    settings = Settings(
        mode=ServiceMode.PRODUCTION,
        api_base="https://internal.example",
    )
    client = SyluliveApiClient(
        settings,
        transport=httpx.MockTransport(handler),
        grant_provider=lambda: "opaque-grant",
    )
    result = await client.post("/internal/mcp/policy/search", {"queries": ["政策"]})
    assert result["status"] == "ok"
    assert captured == {
        "authorization": "Bearer opaque-grant",
        "path": "/internal/mcp/policy/search",
    }
    assert "opaque-grant" not in str(result)


def test_path_policy_rejects_traversal(tmp_path: Path) -> None:
    policy = WorkspacePathPolicy(tmp_path, max_file_bytes=1024)
    with pytest.raises(SafetyViolationError):
        policy.resolve_file("../secret.json")


async def test_disabled_runtime_returns_stable_error() -> None:
    runtime = ToolRuntime(Settings(mode=ServiceMode.DISABLED))
    result = await academic_calculate_summary(
        runtime,
        {
            "snapshot": {
                "courses": [],
                "earned_credits": 0,
                "required_credits": 0,
                "erke_earned": 0,
                "erke_required": 0,
            }
        },
    )
    assert result["code"] == "service_disabled"


def test_status_exposes_no_model_or_grant_value(demo_settings) -> None:
    status = build_status(demo_settings)
    assert status["architecture"]["model_calls"] is False
    assert "model" not in status
    assert "grant_token" not in str(status)
