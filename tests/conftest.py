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


@pytest.fixture(scope="session")
def aws_session():
    profile = os.getenv("AWS_PROFILE", "hackathon")
    region = os.getenv("AWS_REGION", "us-east-1")
    return boto3.Session(profile_name=profile, region_name=region)


@pytest.fixture(scope="session")
def bucket():
    value = os.getenv("GAMEDAY_BUCKET", "").strip()
    if not value:
        pytest.skip("Set GAMEDAY_BUCKET to an existing S3 bucket you can use")
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
