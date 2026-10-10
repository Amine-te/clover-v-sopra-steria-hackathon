"""Typed application settings read once from environment variables (see specs/contracts/config.md).

This is the only module of the package allowed to read the process environment.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal, Optional

from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Repository root: src/clover_v_sopra_steria_hackathon/config.py -> parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

DEFAULT_MODEL_EXTRACT = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
DEFAULT_MODEL_REPORT = "us.anthropic.claude-sonnet-4-20250514-v1:0"

_TRUE_VALUES = {"true", "1"}
_FALSE_VALUES = {"false", "0"}


class ConfigError(ValueError):
    """Raised when environment variables do not form a valid configuration."""


class Settings(BaseSettings):
    """Application settings. Each field maps to the environment variable of the same name in uppercase."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
        case_sensitive=False,
    )

    # AWS access (credentials have no default)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[SecretStr] = None
    aws_default_region: str = "us-east-1"
    gameday_bucket: Optional[str] = None

    # Bedrock models (inference profile IDs) and guardrail
    bedrock_model_extract: str = DEFAULT_MODEL_EXTRACT
    bedrock_model_report: str = DEFAULT_MODEL_REPORT
    guardrail_id: Optional[str] = None
    guardrail_version: Optional[str] = None

    # Pipeline behaviour
    transcribe_language: str = "fr-FR"
    notify_channel: Literal["mock", "sns", "ses", "telegram"] = "mock"
    use_cached_transcripts: bool = False
    checkin_time: Annotated[str, Field(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")] = "20:00"

    # API server
    api_host: str = "127.0.0.1"
    api_port: Annotated[int, Field(ge=1, le=65535)] = 8000
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    @field_validator("use_cached_transcripts", mode="before")
    @classmethod
    def _parse_strict_bool(cls, value: Any) -> Any:
        """Accept only true/false/1/0 (case-insensitive), unlike pydantic's lenient bool parsing."""
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in _TRUE_VALUES:
            return True
        if text in _FALSE_VALUES:
            return False
        raise ValueError("must be one of true, false, 1, 0")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: Any) -> Any:
        """Parse a comma-separated origin list, trimming whitespace and dropping empty entries."""
        if isinstance(value, str):
            value = value.split(",")
        origins = [str(item).strip() for item in value]
        origins = [origin for origin in origins if origin]
        if "*" in origins:
            raise ValueError("wildcard origin '*' is not allowed; list exact origins")
        return origins


def _format_error(exc: ValidationError) -> str:
    """Describe each invalid field by its environment variable name, without echoing input values."""
    parts = []
    for error in exc.errors():
        field = str(error["loc"][0]) if error["loc"] else "unknown"
        parts.append(f"{field.upper()}: {error['msg']}")
    return "Invalid configuration: " + "; ".join(parts)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide Settings, built once from the environment and the root .env file."""
    try:
        return Settings()
    except ValidationError as exc:
        raise ConfigError(_format_error(exc)) from None
