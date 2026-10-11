"""Amazon S3 object storage provider for uploaded audio."""

from uuid import uuid4

import boto3

from ...core.config import get_settings
from ..base import ObjectStorageProvider


class S3ObjectStorageProvider:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gameday_bucket:
            raise ValueError("GAMEDAY_BUCKET is required for S3 object storage.")
        self.bucket = settings.gameday_bucket
        self.client = boto3.client("s3", region_name=settings.aws_default_region or None)

    def put_audio(self, *, data: bytes, content_type: str) -> str:
        key = f"karis-audio/{uuid4().hex}"
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
        return key

    def get_bytes(self, *, object_key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=object_key)
        return response["Body"].read()


_: ObjectStorageProvider = S3ObjectStorageProvider.__new__(S3ObjectStorageProvider)
