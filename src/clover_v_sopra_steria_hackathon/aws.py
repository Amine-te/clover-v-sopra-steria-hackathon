"""Single factory for boto3 clients, configured from Settings (region and optional explicit keys)."""

from __future__ import annotations

from typing import Any

import boto3

from .config import Settings


def client(service: str, settings: Settings) -> Any:
    """Return a boto3 client for `service` in `AWS_DEFAULT_REGION`.

    Explicit keys are used only when both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set;
    otherwise boto3's default credential chain (environment, profiles, instance role) applies.
    """
    kwargs: dict[str, Any] = {"region_name": settings.aws_default_region}
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key.get_secret_value()
    return boto3.client(service, **kwargs)
