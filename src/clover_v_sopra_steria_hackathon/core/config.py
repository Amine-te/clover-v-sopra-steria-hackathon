"""Application settings loaded from environment / .env via pydantic-settings.

All providers default to deterministic mocks so the full demo runs with zero
 AWS credentials. Live providers are optional and initialized on invocation.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    demo_reset_enabled: bool = True

    # Database (PostgreSQL 16, source of truth — docker compose maps host 5433)
    database_url: str = "postgresql+psycopg://karis:karis@localhost:5433/karis"

    # CORS
    frontend_origin: str = "http://localhost:3000"

    # Providers — ALL default to mock (deterministic, no external credentials)
    llm_provider: str = "mock"
    llm_fallback_to_mock: bool = True
    stt_provider: str = "mock"
    ser_provider: str = "mock"
    wearable_provider: str = "mock"
    object_storage_provider: str = "mock"
    messaging_provider: str = "mock"

    # AWS (optional live providers — never required to boot)
    aws_default_region: str = ""
    gameday_bucket: str = ""
    transcription_timeout_seconds: int = 240
    aws_bedrock_model_id: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
