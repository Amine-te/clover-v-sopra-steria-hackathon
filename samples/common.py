"""Shared helpers for the game day sample scripts.

Loads credentials from a local .env (or the normal AWS credential chain) and
exposes convenience factories for the boto3 clients used by the samples.
"""

import os
import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError

try:
    from dotenv import load_dotenv
    # Load samples/.env regardless of the current working directory.
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:  # python-dotenv not installed — fall back to real env vars
    pass


def samples_dir() -> str:
    """Absolute path to the samples/ folder (where this file lives)."""
    return os.path.dirname(os.path.abspath(__file__))


def input_path(*parts: str) -> str:
    """Build a path relative to the samples/ folder."""
    return os.path.join(samples_dir(), *parts)


def output_dir() -> str:
    """Return (and create) the samples/output/ folder."""
    path = os.path.join(samples_dir(), "output")
    os.makedirs(path, exist_ok=True)
    return path


def write_output(filename: str, content: str) -> str:
    """Write text content to samples/output/<filename> and return its path."""
    path = os.path.join(output_dir(), filename)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def region() -> str:
    return os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


def bucket() -> str:
    """Return the configured game day bucket or exit with a clear message."""
    name = os.environ.get("GAMEDAY_BUCKET")
    if not name:
        fail(
            "GAMEDAY_BUCKET is not set. Copy samples/.env.example to "
            "samples/.env and set it (see docs/IAM_SETUP.md)."
        )
    return name


def client(service: str):
    """Create a boto3 client for the given service in the configured region."""
    return boto3.client(service, region_name=region())


def fail(message: str, code: int = 1):
    print(f"\n[ERROR] {message}", file=sys.stderr)
    sys.exit(code)


def handle_aws_error(err: Exception):
    """Print a friendly, actionable message for common AWS errors."""
    if isinstance(err, ClientError):
        aws_code = err.response.get("Error", {}).get("Code", "Unknown")
        aws_msg = err.response.get("Error", {}).get("Message", str(err))
        hint = ""
        if aws_code in ("AccessDeniedException", "AccessDenied"):
            hint = (
                "\n  Hint: check your IAM policy (docs/IAM_SETUP.md). For "
                "Bedrock, also enable model access in the Bedrock console."
            )
        elif aws_code in ("UnrecognizedClientException", "InvalidClientTokenId"):
            hint = "\n  Hint: your AWS_ACCESS_KEY_ID / SECRET looks invalid."
        elif aws_code == "ExpiredTokenException":
            hint = "\n  Hint: your credentials/session token has expired."
        fail(f"AWS error [{aws_code}]: {aws_msg}{hint}")
    elif isinstance(err, BotoCoreError):
        fail(f"AWS SDK error: {err}")
    else:
        raise err
