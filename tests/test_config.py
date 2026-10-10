"""Typed configuration tests (Requirement 2). Values are placeholders only."""
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from clover_v_sopra_steria_hackathon.config import ConfigError, Settings, get_settings

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "clover_v_sopra_steria_hackathon"

CONTRACT_VARS = [
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION", "GAMEDAY_BUCKET",
    "BEDROCK_MODEL_EXTRACT", "BEDROCK_MODEL_REPORT", "GUARDRAIL_ID", "GUARDRAIL_VERSION",
    "TRANSCRIBE_LANGUAGE", "NOTIFY_CHANNEL", "USE_CACHED_TRANSCRIPTS", "CHECKIN_TIME",
]
FAKE_SECRET = "placeholder-secret-value"


def build():
    return Settings(_env_file=None)


def assert_config_error(monkeypatch, var, value):
    """get_settings() must refuse the value and name the UPPERCASE variable."""
    monkeypatch.setenv(var, value)
    with pytest.raises(ConfigError, match=var):
        get_settings()
    get_settings.cache_clear()
    with pytest.raises(ValidationError, match=var.lower()):
        build()


def test_every_contract_variable_has_a_field():
    for var in CONTRACT_VARS:
        assert var.lower() in Settings.model_fields


def test_defaults_when_absent():
    s = build()
    assert s.aws_access_key_id is None
    assert s.aws_secret_access_key is None
    assert s.gameday_bucket is None
    assert s.guardrail_id is None
    assert s.guardrail_version is None
    assert s.aws_default_region == "us-east-1"
    assert s.transcribe_language == "fr-FR"
    assert s.notify_channel == "mock"
    assert s.use_cached_transcripts is False
    assert s.checkin_time == "20:00"
    assert "anthropic.claude-haiku-4-5" in s.bedrock_model_extract
    assert "anthropic.claude-sonnet-4" in s.bedrock_model_report
    assert s.api_host == "127.0.0.1"
    assert s.api_port == 8000
    assert s.cors_origins == ["http://localhost:3000"]


@pytest.mark.parametrize("var", CONTRACT_VARS + ["API_HOST", "API_PORT", "CORS_ORIGINS"])
def test_empty_value_falls_back_to_default(monkeypatch, var):
    monkeypatch.setenv(var, "")
    assert build() == Settings.model_construct()


def test_model_ids_used_unchanged(monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_EXTRACT", "custom.extract-model:1")
    monkeypatch.setenv("BEDROCK_MODEL_REPORT", "custom.report-model:2")
    s = build()
    assert s.bedrock_model_extract == "custom.extract-model:1"
    assert s.bedrock_model_report == "custom.report-model:2"


@pytest.mark.parametrize("channel", ["mock", "sns", "ses", "telegram"])
def test_valid_notify_channels(monkeypatch, channel):
    monkeypatch.setenv("NOTIFY_CHANNEL", channel)
    assert build().notify_channel == channel


@pytest.mark.parametrize("value", ["email", "MOCK", "sms"])
def test_invalid_notify_channel(monkeypatch, value):
    assert_config_error(monkeypatch, "NOTIFY_CHANNEL", value)


@pytest.mark.parametrize("value", ["00:00", "07:30", "20:00", "23:59"])
def test_valid_checkin_time(monkeypatch, value):
    monkeypatch.setenv("CHECKIN_TIME", value)
    assert build().checkin_time == value


@pytest.mark.parametrize("value", ["24:00", "7:5", "7:30", "20:60", "20h00"])
def test_invalid_checkin_time(monkeypatch, value):
    assert_config_error(monkeypatch, "CHECKIN_TIME", value)


@pytest.mark.parametrize("value", ["0", "65536", "abc", "-1"])
def test_invalid_api_port(monkeypatch, value):
    assert_config_error(monkeypatch, "API_PORT", value)


@pytest.mark.parametrize("value", ["1", "65535", "8080"])
def test_valid_api_port(monkeypatch, value):
    monkeypatch.setenv("API_PORT", value)
    assert build().api_port == int(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [("true", True), ("false", False), ("1", True), ("0", False), ("TRUE", True), ("False", False)],
)
def test_use_cached_transcripts_parsing(monkeypatch, value, expected):
    monkeypatch.setenv("USE_CACHED_TRANSCRIPTS", value)
    assert build().use_cached_transcripts is expected


@pytest.mark.parametrize("value", ["yes", "on", "no", "off", "2"])
def test_invalid_use_cached_transcripts(monkeypatch, value):
    assert_config_error(monkeypatch, "USE_CACHED_TRANSCRIPTS", value)


def test_cors_origins_comma_split(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", " http://localhost:3000 , ,https://app.example.com:8443,")
    assert build().cors_origins == ["http://localhost:3000", "https://app.example.com:8443"]


def test_cors_wildcard_rejected(monkeypatch):
    assert_config_error(monkeypatch, "CORS_ORIGINS", "*")


def test_env_file_loaded_and_process_env_wins(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("NOTIFY_CHANNEL=sns\nCHECKIN_TIME=07:30\nGAMEDAY_BUCKET=bucket-from-file\n")
    monkeypatch.setenv("NOTIFY_CHANNEL", "ses")
    s = Settings(_env_file=env_file)
    assert s.notify_channel == "ses"
    assert s.checkin_time == "07:30"
    assert s.gameday_bucket == "bucket-from-file"


def test_get_settings_reads_configured_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("NOTIFY_CHANNEL=telegram\n")
    monkeypatch.setitem(Settings.model_config, "env_file", env_file)
    assert get_settings().notify_channel == "telegram"


def test_missing_env_file_is_fine(tmp_path):
    s = Settings(_env_file=tmp_path / "does-not-exist.env")
    assert s.notify_channel == "mock"


def test_unknown_variables_ignored(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("BEDROCK_MODEL_ID=some.model\nAWS_PROFILE=demo\nUNRELATED=1\n")
    monkeypatch.setenv("AWS_PROFILE", "demo")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "some.model")
    s = Settings(_env_file=env_file)
    assert not hasattr(s, "bedrock_model_id")


def test_secret_is_masked(monkeypatch):
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", FAKE_SECRET)
    s = build()
    assert FAKE_SECRET not in str(s)
    assert FAKE_SECRET not in repr(s)
    assert FAKE_SECRET not in str(s.aws_secret_access_key)
    assert FAKE_SECRET not in repr(s.aws_secret_access_key)
    assert s.aws_secret_access_key.get_secret_value() == FAKE_SECRET


def test_get_settings_returns_same_instance(monkeypatch):
    first = get_settings()
    monkeypatch.setenv("NOTIFY_CHANNEL", "sns")
    second = get_settings()
    assert first is second
    assert second.notify_channel == "mock"


def test_only_config_reads_environment():
    pattern = re.compile(r"os\.environ|os\.getenv|getenv\(|environ\[")
    offenders = [
        path.relative_to(PACKAGE_DIR).as_posix()
        for path in PACKAGE_DIR.rglob("*.py")
        if path.name != "config.py" and pattern.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []
