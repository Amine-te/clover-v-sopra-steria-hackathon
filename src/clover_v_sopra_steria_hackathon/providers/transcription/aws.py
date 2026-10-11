"""Amazon Transcribe provider for audio already stored in S3."""

import json
import time
import urllib.request
from uuid import uuid4

import boto3

from ...core.config import get_settings
from ..base import TranscriptResult, TranscriptionProvider


class AWSTranscribeProvider:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gameday_bucket:
            raise ValueError("GAMEDAY_BUCKET is required for Amazon Transcribe.")
        self.bucket = settings.gameday_bucket
        self.timeout = settings.transcription_timeout_seconds
        self.client = boto3.client("transcribe", region_name=settings.aws_default_region or None)

    def transcribe(self, *, audio_object_key: str, language: str = "fr-FR") -> TranscriptResult:
        job_name = f"karis-transcribe-{uuid4().hex}"
        extension = audio_object_key.rsplit(".", 1)[-1] if "." in audio_object_key else "mp3"
        self.client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": f"s3://{self.bucket}/{audio_object_key}"},
            MediaFormat=extension,
            LanguageCode=language,
        )
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            job = self.client.get_transcription_job(TranscriptionJobName=job_name)["TranscriptionJob"]
            state = job["TranscriptionJobStatus"]
            if state == "FAILED":
                raise RuntimeError(job.get("FailureReason", "Amazon Transcribe failed."))
            if state == "COMPLETED":
                uri = job.get("Transcript", {}).get("TranscriptFileUri")
                if not uri:
                    raise RuntimeError("Amazon Transcribe returned no transcript URI.")
                with urllib.request.urlopen(uri, timeout=30) as response:  # noqa: S310
                    payload = json.loads(response.read().decode("utf-8"))
                text = payload["results"]["transcripts"][0]["transcript"].strip()
                if not text:
                    raise RuntimeError("Amazon Transcribe returned an empty transcript.")
                return TranscriptResult(text=text, language=language, provider="aws-transcribe")
            time.sleep(min(5, max(1, deadline - time.monotonic())))
        raise TimeoutError("Amazon Transcribe timed out.")


_: TranscriptionProvider = AWSTranscribeProvider.__new__(AWSTranscribeProvider)
