"""Voice report pipeline: store the audio in S3, transcribe it with AWS Transcribe, or serve a fixture."""

from __future__ import annotations

import json
import logging
import secrets
import time
from dataclasses import dataclass
from typing import Any, Callable, Literal, Optional

from botocore.exceptions import BotoCoreError, ClientError

from ..config import ConfigError, Settings
from .fixtures import FixtureNotFoundError, load_fixture
from .formats import ALLOWED_FORMATS, media_format, normalize_ext

__all__ = [
    "AudioNotFoundError",
    "FixtureNotFoundError",
    "TranscriptResult",
    "TranscriptionError",
    "UploadError",
    "VoiceService",
    "audio_key",
    "new_report_id",
    "transcript_key",
]

logger = logging.getLogger(__name__)

_AWS_ERRORS = (ClientError, BotoCoreError)
_PENDING_STATUSES = {"QUEUED", "IN_PROGRESS"}


class TranscriptionError(Exception):
    """Transcription failed after the audio was stored; the recording can be retried."""

    def __init__(self, report_id: str, audio_s3_key: Optional[str], reason: str) -> None:
        super().__init__(reason)
        self.report_id = report_id
        self.audio_s3_key = audio_s3_key


class UploadError(Exception):
    """The audio could not be stored in S3 (live mode); nothing to retry."""

    def __init__(self, report_id: str, reason: str) -> None:
        super().__init__(reason)
        self.report_id = report_id


class AudioNotFoundError(Exception):
    """No stored audio exists for the requested report."""

    def __init__(self, report_id: str) -> None:
        super().__init__(f"no stored audio for report {report_id}")
        self.report_id = report_id


@dataclass(frozen=True)
class TranscriptResult:
    report_id: str
    audio_s3_key: Optional[str]
    transcript: str
    source: Literal["transcribe", "cache"]


def new_report_id() -> str:
    """Return a fresh Report_Id, `rep-<32 hex>`."""
    return f"rep-{secrets.token_hex(16)}"


def audio_key(report_id: str, ext: str) -> str:
    return f"audio/{report_id}.{normalize_ext(ext)}"


def transcript_key(report_id: str) -> str:
    return f"transcripts/{report_id}.json"


def _error_code(exc: Exception) -> str:
    if isinstance(exc, ClientError):
        return str(exc.response.get("Error", {}).get("Code", "ClientError"))
    return type(exc).__name__


class VoiceService:
    """Uploads recordings, runs batch Transcribe jobs and applies the cached-transcript fallback."""

    def __init__(
        self,
        settings: Settings,
        s3: Any,
        transcribe: Any,
        *,
        poll_interval: float = 3.0,
        timeout: float = 180.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings
        self.s3 = s3
        self.transcribe = transcribe
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.sleep = sleep

    @property
    def bucket(self) -> Optional[str]:
        value = (self.settings.gameday_bucket or "").strip()
        return value or None

    @property
    def cached(self) -> bool:
        return self.settings.use_cached_transcripts

    def _require_bucket(self) -> str:
        bucket = self.bucket
        if bucket is None:
            raise ConfigError("GAMEDAY_BUCKET is not set; it is required to store and transcribe audio")
        return bucket

    def submit(
        self,
        data: bytes,
        ext: str,
        content_type: Optional[str],
        fixture: Optional[str] = None,
    ) -> TranscriptResult:
        """Store and transcribe one recording (or return a fixture transcript in cached mode)."""
        ext = normalize_ext(ext)
        media_format(ext)  # rejects unsupported extensions with ValueError
        report_id = new_report_id()

        if self.cached:
            # Load the fixture first so an unknown name is rejected before anything is stored.
            transcript = load_fixture(fixture)
            key = self._upload_best_effort(report_id, data, ext, content_type)
            return TranscriptResult(report_id, key, transcript, "cache")

        bucket = self._require_bucket()
        key = audio_key(report_id, ext)
        try:
            self._upload(bucket, key, data, content_type)
        except _AWS_ERRORS as exc:
            logger.error("Audio upload failed for %s: %s", report_id, _error_code(exc))
            raise UploadError(report_id, f"audio upload failed: {_error_code(exc)}") from exc
        transcript = self._transcribe(report_id, key, ext)
        return TranscriptResult(report_id, key, transcript, "transcribe")

    def retry(self, report_id: str) -> TranscriptResult:
        """Transcribe the audio already stored for `report_id`, without uploading it again."""
        if self.cached:
            key = None
            if self.bucket is not None:
                try:
                    key = self._find_audio(self.bucket, report_id)
                except _AWS_ERRORS as exc:
                    logger.warning("Audio lookup skipped in cached mode for %s: %s", report_id, _error_code(exc))
            return TranscriptResult(report_id, key, load_fixture(None), "cache")

        bucket = self._require_bucket()
        try:
            key = self._find_audio(bucket, report_id)
        except _AWS_ERRORS as exc:
            logger.error("Audio lookup failed for %s: %s", report_id, _error_code(exc))
            raise TranscriptionError(report_id, None, f"audio lookup failed: {_error_code(exc)}") from exc
        if key is None:
            raise AudioNotFoundError(report_id)
        ext = key.rsplit(".", 1)[-1]
        transcript = self._transcribe(report_id, key, ext)
        return TranscriptResult(report_id, key, transcript, "transcribe")

    # Internals

    def _upload(self, bucket: str, key: str, data: bytes, content_type: Optional[str]) -> None:
        params: dict[str, Any] = {"Bucket": bucket, "Key": key, "Body": data}
        if content_type:
            params["ContentType"] = content_type
        self.s3.put_object(**params)
        logger.info("Stored audio at s3://%s/%s (%d bytes)", bucket, key, len(data))

    def _upload_best_effort(
        self, report_id: str, data: bytes, ext: str, content_type: Optional[str]
    ) -> Optional[str]:
        bucket = self.bucket
        if bucket is None:
            return None
        key = audio_key(report_id, ext)
        try:
            self._upload(bucket, key, data, content_type)
        except _AWS_ERRORS as exc:
            logger.warning("Cached mode: audio upload skipped for %s: %s", report_id, _error_code(exc))
            return None
        return key

    def _find_audio(self, bucket: str, report_id: str) -> Optional[str]:
        response = self.s3.list_objects_v2(Bucket=bucket, Prefix=f"audio/{report_id}.")
        for item in response.get("Contents", []):
            key = item.get("Key", "")
            if key.rsplit(".", 1)[-1] in ALLOWED_FORMATS:
                return key
        return None

    def _transcribe(self, report_id: str, key: str, ext: str) -> str:
        bucket = self._require_bucket()
        job_name = f"karis-{report_id}-{secrets.token_hex(4)}"
        try:
            self.transcribe.start_transcription_job(
                TranscriptionJobName=job_name,
                LanguageCode=self.settings.transcribe_language,
                MediaFormat=media_format(ext),
                Media={"MediaFileUri": f"s3://{bucket}/{key}"},
                OutputBucketName=bucket,
                OutputKey=transcript_key(report_id),
            )
            logger.info("Started Transcribe job %s for %s", job_name, report_id)
            self._wait(report_id, key, job_name)
            return self._read_transcript(bucket, report_id, key)
        except _AWS_ERRORS as exc:
            logger.error("Transcription failed for %s (job %s): %s", report_id, job_name, _error_code(exc))
            raise TranscriptionError(report_id, key, f"AWS error: {_error_code(exc)}") from exc

    def _wait(self, report_id: str, key: str, job_name: str) -> None:
        # Elapsed time is counted from the injected sleeps so tests never wait for real.
        elapsed = 0.0
        while True:
            job = self.transcribe.get_transcription_job(TranscriptionJobName=job_name)["TranscriptionJob"]
            status = job.get("TranscriptionJobStatus")
            if status == "COMPLETED":
                return
            if status not in _PENDING_STATUSES:
                reason = job.get("FailureReason", "unknown reason")
                logger.error("Transcribe job %s ended %s: %s", job_name, status, reason)
                raise TranscriptionError(report_id, key, f"Transcribe job {status}: {reason}")
            if elapsed >= self.timeout:
                logger.error("Transcribe job %s still %s after %.0f s", job_name, status, elapsed)
                raise TranscriptionError(report_id, key, f"Transcribe job timed out after {elapsed:.0f} s")
            self.sleep(self.poll_interval)
            elapsed += self.poll_interval

    def _read_transcript(self, bucket: str, report_id: str, key: str) -> str:
        body = self.s3.get_object(Bucket=bucket, Key=transcript_key(report_id))["Body"].read()
        try:
            result = json.loads(body)
            parts = [item["transcript"] for item in result["results"]["transcripts"]]
        except (ValueError, KeyError, TypeError) as exc:
            raise TranscriptionError(report_id, key, "unreadable transcript output") from exc
        return " ".join(part.strip() for part in parts if part.strip())
