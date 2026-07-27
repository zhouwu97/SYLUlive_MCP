"""内部 API、路径和运行模式的安全测试。"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from sylulive_mcp.clients import SyluliveApiClient
from sylulive_mcp.config import ServiceMode, Settings
from sylulive_mcp.errors import InternalApiError, SafetyViolationError, ServiceConfigurationError
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
    with pytest.raises(ServiceConfigurationError):
        normalize_internal_endpoint("http://0.0.0.0:8080", allow_private_http=True)
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
    await client.aclose()
    assert result["status"] == "ok"
    assert captured == {
        "authorization": "Bearer opaque-grant",
        "path": "/internal/mcp/policy/search",
    }
    assert "opaque-grant" not in str(result)


@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [
        (401, "grant_rejected"),
        (403, "grant_rejected"),
        (429, "quota_exceeded"),
        (500, "internal_api_error"),
    ],
)
async def test_internal_api_classifies_http_failures(status_code: int, expected_code: str) -> None:
    client = SyluliveApiClient(
        Settings(mode=ServiceMode.PRODUCTION, api_base="https://internal.example"),
        transport=httpx.MockTransport(lambda _request: httpx.Response(status_code)),
        grant_provider=lambda: "grant",
    )
    try:
        with pytest.raises(InternalApiError) as captured:
            await client.post("/internal/mcp/test", {})
        assert captured.value.code == expected_code
    finally:
        await client.aclose()


async def test_internal_api_rejects_oversized_response_before_json_decode() -> None:
    settings = Settings(
        mode=ServiceMode.PRODUCTION,
        api_base="https://internal.example",
        max_api_response_bytes=1024,
    )
    client = SyluliveApiClient(
        settings,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, content=b"{" + b"x" * 2048 + b"}")
        ),
        grant_provider=lambda: "grant",
    )
    try:
        with pytest.raises(InternalApiError) as captured:
            await client.post("/internal/mcp/test", {})
        assert captured.value.code == "internal_api_response_too_large"
    finally:
        await client.aclose()


@pytest.mark.parametrize(
    ("exception_type", "expected_code"),
    [
        (httpx.ReadTimeout, "internal_api_timeout"),
        (httpx.ConnectError, "internal_api_unavailable"),
    ],
)
async def test_internal_api_classifies_transport_failures(
    exception_type: type[httpx.RequestError], expected_code: str
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exception_type("request failed", request=request)

    client = SyluliveApiClient(
        Settings(mode=ServiceMode.PRODUCTION, api_base="https://internal.example"),
        transport=httpx.MockTransport(handler),
        grant_provider=lambda: "grant",
    )
    try:
        with pytest.raises(InternalApiError) as captured:
            await client.post("/internal/mcp/test", {})
        assert captured.value.code == expected_code
    finally:
        await client.aclose()


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
