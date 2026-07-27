"""SYLUlive MCP 进程配置。"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceMode(StrEnum):
    """服务运行模式。生产模式只通过 Go 内部 API 访问正式数据。"""

    PRODUCTION = "production"
    DEMO = "demo"
    DISABLED = "disabled"


class TransportMode(StrEnum):
    """MCP 对外传输方式。"""

    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable-http"


class Settings(BaseSettings):
    """单个隔离 MCP 进程的配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        populate_by_name=True,
    )

    mode: ServiceMode = Field(
        default=ServiceMode.DISABLED,
        validation_alias=AliasChoices("SYLULIVE_MCP_MODE", "mode"),
    )
    transport: TransportMode = Field(
        default=TransportMode.STDIO,
        validation_alias=AliasChoices("SYLULIVE_MCP_TRANSPORT", "transport"),
    )
    http_host: str = Field(
        default="127.0.0.1",
        min_length=1,
        max_length=255,
        validation_alias=AliasChoices("SYLULIVE_MCP_HOST", "http_host"),
    )
    http_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        validation_alias=AliasChoices("SYLULIVE_MCP_PORT", "http_port"),
    )
    http_path: str = Field(
        default="/mcp",
        pattern=r"^/[a-zA-Z0-9/_-]*$",
        validation_alias=AliasChoices("SYLULIVE_MCP_PATH", "http_path"),
    )
    api_base: str = Field(
        default="http://127.0.0.1:8080",
        validation_alias=AliasChoices("SYLULIVE_API_BASE", "api_base"),
    )
    grant_token: SecretStr = Field(
        default_factory=lambda: SecretStr(""),
        validation_alias=AliasChoices("SYLULIVE_MCP_GRANT", "grant_token"),
    )
    timeout_seconds: float = Field(
        default=30,
        gt=0,
        le=120,
        validation_alias=AliasChoices("SYLULIVE_API_TIMEOUT_SECONDS", "timeout_seconds"),
    )
    demo_root: Path = Field(
        default=Path("examples"),
        validation_alias=AliasChoices("SYLULIVE_DEMO_ROOT", "demo_root"),
    )
    max_input_chars: int = Field(
        default=30_000,
        ge=1,
        le=1_000_000,
        validation_alias=AliasChoices("SYLULIVE_MAX_INPUT_CHARS", "max_input_chars"),
    )
    max_source_files: int = Field(
        default=20,
        ge=1,
        le=200,
        validation_alias=AliasChoices("SYLULIVE_MAX_SOURCE_FILES", "max_source_files"),
    )
    max_source_file_bytes: int = Field(
        default=1_048_576,
        ge=1,
        le=20 * 1_048_576,
        validation_alias=AliasChoices("SYLULIVE_MAX_SOURCE_FILE_BYTES", "max_source_file_bytes"),
    )
    allow_private_http: bool = Field(
        default=False,
        validation_alias=AliasChoices("SYLULIVE_ALLOW_PRIVATE_HTTP", "allow_private_http"),
    )
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("SYLULIVE_LOG_LEVEL", "log_level"),
    )

    @property
    def demo_root_path(self) -> Path:
        """解析演示数据根目录，但不将绝对路径暴露给调用方。"""

        return self.demo_root.expanduser().resolve()

    @property
    def has_grant(self) -> bool:
        """仅报告短期 Grant 是否存在。"""

        return bool(self.grant_token.get_secret_value().strip())


def load_settings() -> Settings:
    """从环境加载服务设置。"""

    return Settings()
