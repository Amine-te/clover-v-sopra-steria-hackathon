"""M1 — settings load with safe defaults (no AWS required)."""

from clover_v_sopra_steria_hackathon.core.config import Settings, get_settings


def test_settings_load_successfully():
    settings = Settings()
    assert settings.app_env == "development"
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.frontend_origin.startswith("http")


def test_default_providers_are_all_mock():
    settings = Settings()
    assert settings.llm_provider == "mock"
    assert settings.stt_provider == "mock"
    assert settings.ser_provider == "mock"
    assert settings.wearable_provider == "mock"
    assert settings.object_storage_provider == "mock"
    assert settings.messaging_provider == "mock"


def test_aws_settings_optional_and_empty_by_default():
    settings = Settings()
    assert settings.aws_default_region == ""
    assert settings.gameday_bucket == ""
    assert settings.aws_bedrock_model_id == ""


def test_get_settings_is_cached():
    assert get_settings() is get_settings()
