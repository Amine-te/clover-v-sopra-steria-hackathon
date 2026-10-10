"""Shared configuration for live AWS integration tests."""
import os
from pathlib import Path

import boto3
import pytest

ROOT = Path(__file__).resolve().parents[1]


def pytest_addoption(parser):
    parser.addoption(
        "--aws-live", action="store_true", default=False,
        help="Run tests that make real, potentially billable AWS requests.",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--aws-live"):
        return
    skip = pytest.mark.skip(reason="Requires --aws-live (real AWS calls)")
    for item in items:
        if "aws_live" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _isolated_settings(request, monkeypatch):
    """Unit-test isolation: hide the developer's .env and config env vars, reset the settings cache.

    Live tests (marked aws_live) keep the real environment untouched.
    """
    if request.node.get_closest_marker("aws_live"):
        yield
        return
    from clover_v_sopra_steria_hackathon.config import Settings, get_settings

    field_names = set(Settings.model_fields)
    for name in list(os.environ):
        if name.lower() in field_names:
            monkeypatch.delenv(name)
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _live_settings():
    """Settings read from the process env and the root .env (live tests only)."""
    from clover_v_sopra_steria_hackathon.config import Settings

    return Settings()


def _profile_exists(name: str) -> bool:
    import botocore.session

    return name in botocore.session.Session(profile=None).available_profiles


@pytest.fixture(scope="session")
def aws_session():
    """AWS session for live tests.

    Resolution order:
    1. AWS_PROFILE exported in the shell (must exist in ~/.aws).
    2. The "hackathon" CLI profile, if it exists.
    3. AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY from the process env or the root .env.
    """
    settings = _live_settings()
    region = os.getenv("AWS_REGION") or settings.aws_default_region

    exported_profile = os.getenv("AWS_PROFILE")
    if exported_profile:
        if not _profile_exists(exported_profile):
            pytest.fail(
                f"AWS_PROFILE={exported_profile} is exported but not configured in ~/.aws. "
                "Unset it to use the keys from .env instead."
            )
        return boto3.Session(profile_name=exported_profile, region_name=region)

    if _profile_exists("hackathon"):
        return boto3.Session(profile_name="hackathon", region_name=region)

    if settings.aws_access_key_id and settings.aws_secret_access_key:
        return boto3.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key.get_secret_value(),
            region_name=region,
        )

    pytest.fail(
        "No AWS credentials: set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env, "
        "or configure the 'hackathon' AWS CLI profile."
    )


@pytest.fixture(scope="session")
def bucket():
    value = (os.getenv("GAMEDAY_BUCKET") or _live_settings().gameday_bucket or "").strip()
    if not value:
        pytest.skip("Set GAMEDAY_BUCKET (in .env or the shell) to an existing S3 bucket you can use")
    return value


@pytest.fixture(scope="session")
def audio_path():
    path = Path(os.getenv("TEST_AUDIO_PATH", str(ROOT / "samples/audio/Enregistrement.mp3")))
    if not path.exists():
        pytest.skip(f"Audio sample not found: {path}")
    return path


@pytest.fixture(scope="session")
def document_path():
    path = Path(os.getenv("TEST_DOCUMENT_PATH", str(ROOT / "samples/OCR/ordonnance.png")))
    if not path.exists():
        pytest.skip(f"Document sample not found: {path}")
    return path
