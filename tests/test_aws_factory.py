"""AWS client factory tests (Requirement 1). Offline: credentials are inspected, never used."""
import re
from pathlib import Path

import pytest

from clover_v_sopra_steria_hackathon import aws
from clover_v_sopra_steria_hackathon.config import Settings

MODULE = Path(aws.__file__)
FAKE_KEY_ID = "fake-key-id-from-settings"
FAKE_SECRET = "fake-secret-for-tests"


@pytest.fixture
def no_ambient_credentials(monkeypatch, tmp_path):
    # Hide the developer's credentials so the default chain finds nothing predictable.
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "credentials"))
    monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "config"))
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")


def test_region_from_settings(no_ambient_credentials):
    settings = Settings(_env_file=None, aws_default_region="eu-west-3")
    assert aws.client("s3", settings).meta.region_name == "eu-west-3"


def test_explicit_keys_when_both_set(no_ambient_credentials):
    settings = Settings(
        _env_file=None, aws_access_key_id=FAKE_KEY_ID, aws_secret_access_key=FAKE_SECRET
    )
    creds = aws.client("transcribe", settings)._request_signer._credentials
    assert creds.access_key == FAKE_KEY_ID
    assert creds.secret_key == FAKE_SECRET


@pytest.mark.parametrize(
    "fields",
    [{}, {"aws_access_key_id": FAKE_KEY_ID}, {"aws_secret_access_key": FAKE_SECRET}],
)
def test_default_chain_when_a_key_is_missing(no_ambient_credentials, monkeypatch, fields):
    # Settings is built before the env vars exist, so only `fields` are set on it.
    settings = Settings(_env_file=None, **fields)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "fake-key-id-from-env-chain")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "chain-secret")
    creds = aws.client("s3", settings)._request_signer._credentials
    assert creds.access_key == "fake-key-id-from-env-chain"
    assert creds.method == "env"


def test_factory_does_not_read_environment():
    source = MODULE.read_text(encoding="utf-8")
    assert not re.search(r"os\.environ|os\.getenv|getenv\(|environ\[", source)
