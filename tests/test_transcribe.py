"""Batch speech-to-text using existing sample audio and S3."""
import json
import time
import uuid
import urllib.request
import pytest

pytestmark = pytest.mark.aws_live


def test_transcribe_french(aws_session, bucket, audio_path):
    s3 = aws_session.client("s3")
    client = aws_session.client("transcribe")
    suffix = audio_path.suffix.lower().lstrip(".")
    if suffix not in {"mp3", "mp4", "wav", "flac", "ogg", "amr", "webm", "m4a"}:
        pytest.skip(f"Unsupported media file extension: {audio_path.suffix}")
    key = f"clover-aws-tests/transcribe-{uuid.uuid4().hex}.{suffix}"
    name = f"clover-aws-test-{uuid.uuid4().hex[:16]}"
    uploaded = False
    started = False
    try:
        s3.upload_file(str(audio_path), bucket, key)
        uploaded = True
        client.start_transcription_job(
            TranscriptionJobName=name,
            LanguageCode="fr-FR",
            MediaFormat=suffix,
            Media={"MediaFileUri": f"s3://{bucket}/{key}"},
        )
        started = True
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            job = client.get_transcription_job(TranscriptionJobName=name)["TranscriptionJob"]
            status = job["TranscriptionJobStatus"]
            if status == "FAILED":
                pytest.fail(f"Transcribe failed: {job.get('FailureReason', 'unknown reason')}")
            if status == "COMPLETED":
                uri = job["Transcript"]["TranscriptFileUri"]
                with urllib.request.urlopen(uri, timeout=30) as response:
                    result = json.load(response)
                text = result["results"]["transcripts"][0]["transcript"]
                print(f"French transcript: {text}")
                assert text.strip(), "Transcription result was empty"
                return
            time.sleep(5)
        pytest.fail(f"Transcribe still running after 240s; job={name}")
    finally:
        if started:
            try:
                client.delete_transcription_job(TranscriptionJobName=name)
            except Exception as exc:
                print(f"Cleanup warning (job {name}): {exc}")
        if uploaded:
            try:
                s3.delete_object(Bucket=bucket, Key=key)
            except Exception as exc:
                print(f"Cleanup warning (object s3://{bucket}/{key}): {exc}")
