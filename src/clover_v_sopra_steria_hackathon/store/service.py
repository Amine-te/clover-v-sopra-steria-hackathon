"""TimelineStore: write Observations to S3 as one JSON object each and read them back in time order.

Design decisions (see .kiro/specs/timeline-store/design.md):
- One object per Observation, keyed by subject and UTC day, so a period query narrows by date prefix.
- Query by listing then fetch-and-filter (no index); fine for the hackathon's data volume.
- A stored object that is not valid Observation JSON is skipped and logged, never fatal.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Optional

from botocore.exceptions import BotoCoreError, ClientError

from .. import aws
from ..config import ConfigError, Settings
from ..models import Observation
from .keys import day_prefixes, observation_key, subject_prefix

__all__ = ["Period", "StoreError", "TimelineStore"]

logger = logging.getLogger(__name__)

_AWS_ERRORS = (ClientError, BotoCoreError)


class StoreError(Exception):
    """A failed S3 operation. `aws_code` carries the underlying AWS error code when known."""

    def __init__(self, message: str, aws_code: Optional[str] = None) -> None:
        super().__init__(message)
        self.aws_code = aws_code


@dataclass(frozen=True)
class Period:
    """An inclusive time range; either bound may be open (None)."""

    start: Optional[datetime] = None
    end: Optional[datetime] = None


def _error_code(exc: Exception) -> str:
    if isinstance(exc, ClientError):
        return str(exc.response.get("Error", {}).get("Code", "ClientError"))
    return type(exc).__name__


class TimelineStore:
    """Holds the S3 client and settings; saves and queries Observations in `GAMEDAY_BUCKET`."""

    def __init__(self, settings: Settings, s3: Any = None) -> None:
        self.settings = settings
        self.s3 = s3 if s3 is not None else aws.client("s3", settings)

    # Writes

    def save(self, obs: Observation) -> str:
        """Write one Observation as a JSON object at its key; return the key written."""
        key = observation_key(obs)
        body = obs.model_dump_json().encode("utf-8")
        try:
            self.s3.put_object(
                Bucket=self._bucket(),
                Key=key,
                Body=body,
                ContentType="application/json",
            )
        except _AWS_ERRORS as exc:
            code = _error_code(exc)
            logger.error("S3 put_object failed for %s: %s", key, code)
            raise StoreError(f"S3 error: {code}", aws_code=code) from exc
        return key

    def save_many(self, observations: Iterable[Observation]) -> list[str]:
        """Write each Observation and return the keys written, in input order."""
        return [self.save(obs) for obs in observations]

    # Reads

    def query(
        self,
        subject_id: str,
        period: Optional[Period] = None,
        category: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> list[Observation]:
        """Return the subject's Observations matching the filters, sorted by `timestamp` ascending.

        Objects that fail to parse as an Observation are skipped (logged in English), so one bad
        write never breaks a query.
        """
        observations: list[Observation] = []
        for key in self._list_keys(subject_id, period):
            obs = self._load(key)
            if obs is None:
                continue
            if period is not None:
                if period.start is not None and obs.timestamp < period.start:
                    continue
                if period.end is not None and obs.timestamp > period.end:
                    continue
            if category is not None and obs.category != category:
                continue
            if severity is not None and obs.severity != severity:
                continue
            observations.append(obs)
        observations.sort(key=lambda item: item.timestamp)
        return observations

    # Internals

    def _bucket(self) -> str:
        bucket = self.settings.gameday_bucket
        if not bucket:
            raise ConfigError("Invalid configuration: GAMEDAY_BUCKET is not set")
        return bucket

    def _prefixes(self, subject_id: str, period: Optional[Period]) -> list[str]:
        """The S3 prefixes to list: the day prefixes in the period, else the whole subject."""
        if period is not None and period.start is not None and period.end is not None:
            return day_prefixes(subject_id, period.start, period.end)
        return [subject_prefix(subject_id)]

    def _list_keys(self, subject_id: str, period: Optional[Period]) -> list[str]:
        """List every object key under the resolved prefixes, following pagination."""
        bucket = self._bucket()
        keys: list[str] = []
        try:
            for prefix in self._prefixes(subject_id, period):
                token: Optional[str] = None
                while True:
                    kwargs: dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
                    if token is not None:
                        kwargs["ContinuationToken"] = token
                    response = self.s3.list_objects_v2(**kwargs)
                    for item in response.get("Contents", []):
                        key = item.get("Key")
                        if key:
                            keys.append(key)
                    if response.get("IsTruncated"):
                        token = response.get("NextContinuationToken")
                        if not token:
                            break
                    else:
                        break
        except _AWS_ERRORS as exc:
            code = _error_code(exc)
            logger.error("S3 list_objects_v2 failed for subject %s: %s", subject_id, code)
            raise StoreError(f"S3 error: {code}", aws_code=code) from exc
        return keys

    def _load(self, key: str) -> Optional[Observation]:
        """Fetch and parse one object; return None (and log) when it is not a valid Observation."""
        try:
            response = self.s3.get_object(Bucket=self._bucket(), Key=key)
            raw = response["Body"].read()
        except _AWS_ERRORS as exc:
            code = _error_code(exc)
            logger.error("S3 get_object failed for %s: %s", key, code)
            raise StoreError(f"S3 error: {code}", aws_code=code) from exc
        try:
            return Observation.model_validate_json(raw)
        except ValueError:
            logger.warning("Skipping object that is not a valid Observation: %s", key)
            return None
