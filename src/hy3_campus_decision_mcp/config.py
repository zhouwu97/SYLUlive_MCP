"""从进程环境加载的运行配置。"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Hy3Mode(StrEnum):
    """支持的模型提供方运行模式。"""

    LIVE = "live"
    FIXTURE = "fixture"
    DISABLED = "disabled"


class ToolProfile(StrEnum):
    """决定是否向独立 SYLUlive Runtime 暴露便携问答工具。"""

    PORTABLE = "portable"
    SYLULIVE_RUNTIME = "sylulive_runtime"


class Settings(BaseSettings):
    """单个隔离 MCP 进程的配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        populate_by_name=True,
    )

    mode: Hy3Mode = Field(
        default=Hy3Mode.DISABLED,
        validation_alias=AliasChoices("HY3_MODE", "mode"),
    )
    tool_profile: ToolProfile = Field(
        default=ToolProfile.PORTABLE,
        validation_alias=AliasChoices("HY3_TOOL_PROFILE", "tool_profile"),
    )
    api_base: str = Field(
        default="https://example.com/v1",
        validation_alias=AliasChoices("HY3_API_BASE", "api_base"),
    )
    api_key: SecretStr = Field(
        default_factory=lambda: SecretStr(""),
        validation_alias=AliasChoices("HY3_API_KEY", "api_key"),
    )
    model_name: str = Field(
        default="hy3",
        validation_alias=AliasChoices("HY3_MODEL", "model_name"),
    )
    timeout_seconds: float = Field(
        default=60,
        gt=0,
        le=300,
        validation_alias=AliasChoices("HY3_TIMEOUT_SECONDS", "timeout_seconds"),
    )
    campus_root: Path = Field(
        default=Path("examples"),
        validation_alias=AliasChoices("HY3_CAMPUS_ROOT", "campus_root"),
    )
    fixture_root: Path = Field(
        default=Path("tests/fixtures/hy3"),
        validation_alias=AliasChoices("HY3_FIXTURE_ROOT", "fixture_root"),
    )
    max_input_chars: int = Field(
        default=30_000,
        ge=1,
        le=1_000_000,
        validation_alias=AliasChoices("HY3_MAX_INPUT_CHARS", "max_input_chars"),
    )
    max_source_files: int = Field(
        default=20,
        ge=1,
        le=200,
        validation_alias=AliasChoices("HY3_MAX_SOURCE_FILES", "max_source_files"),
    )
    max_source_file_bytes: int = Field(
        default=1_048_576,
        ge=1,
        le=20 * 1_048_576,
        validation_alias=AliasChoices("HY3_MAX_SOURCE_FILE_BYTES", "max_source_file_bytes"),
    )
    max_output_bytes: int = Field(
        default=131_072,
        ge=1_024,
        le=1_048_576,
        validation_alias=AliasChoices("HY3_MAX_OUTPUT_BYTES", "max_output_bytes"),
    )
    allow_private_http: bool = Field(
        default=False,
        validation_alias=AliasChoices("HY3_ALLOW_PRIVATE_HTTP", "allow_private_http"),
    )
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("HY3_LOG_LEVEL", "log_level"),
    )
    default_temperature: float = Field(
        default=0.2,
        ge=0,
        le=2,
        validation_alias=AliasChoices("HY3_DEFAULT_TEMPERATURE", "default_temperature"),
    )
    default_top_p: float = Field(
        default=1.0,
        gt=0,
        le=1,
        validation_alias=AliasChoices("HY3_DEFAULT_TOP_P", "default_top_p"),
    )

    @property
    def campus_root_path(self) -> Path:
        """解析配置的工作区根目录，但不将绝对路径暴露给调用方。"""

        return self.campus_root.expanduser().resolve()

    @property
    def fixture_root_path(self) -> Path:
        """解析仅供本地 Provider 响应使用的 Fixture 存储目录。"""

        return self.fixture_root.expanduser().resolve()

    @property
    def has_api_key(self) -> bool:
        """仅报告密钥是否存在，不返回密钥内容。"""

        return bool(self.api_key.get_secret_value().strip())


def load_settings() -> Settings:
    """为 MCP 进程加载一份通过校验的配置对象。"""

    return Settings()
