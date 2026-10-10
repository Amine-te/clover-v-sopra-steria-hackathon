"""Live end-to-end voice capture: real S3 upload and Transcribe job on the sample recording."""
import pytest

from clover_v_sopra_steria_hackathon.audio.service import TranscriptionError, VoiceService, transcript_key
from clover_v_sopra_steria_hackathon.config import Settings

pytestmark = pytest.mark.aws_live


class RecordingTranscribe:
    """Pass-through Transcribe client that remembers the job names it started (for cleanup)."""

    def __init__(self, client):
        self._client = client
        self.job_names = []

    def start_transcription_job(self, **kwargs):
        self.job_names.append(kwargs["TranscriptionJobName"])
        return self._client.start_transcription_job(**kwargs)

    def __getattr__(self, name):
        return getattr(self._client, name)


def test_voice_capture_live(aws_session, bucket, audio_path):
    s3 = aws_session.client("s3")
    transcribe = RecordingTranscribe(aws_session.client("transcribe"))
    settings = Settings(gameday_bucket=bucket, use_cached_transcripts=False)
    service = VoiceService(settings, s3, transcribe, poll_interval=5.0, timeout=240.0)
    ext = audio_path.suffix.lstrip(".")
    report_id = audio_s3_key = None
    try:
        try:
            result = service.submit(audio_path.read_bytes(), ext, "audio/mpeg")
        except TranscriptionError as exc:
            report_id, audio_s3_key = exc.report_id, exc.audio_s3_key
            raise
        report_id, audio_s3_key = result.report_id, result.audio_s3_key
        print(f"French transcript: {result.transcript}")
        assert result.source == "transcribe"
        assert result.audio_s3_key == f"audio/{result.report_id}.{ext.lower()}"
        assert result.transcript.strip()
    finally:
        for name in transcribe.job_names:
            try:
                transcribe.delete_transcription_job(TranscriptionJobName=name)
            except Exception as exc:
                print(f"Cleanup warning (job {name}): {exc}")
        keys = [audio_s3_key] if audio_s3_key else []
        if report_id:
            # Transcribe may also leave a write-access check file under the output prefix.
            keys += [transcript_key(report_id), "transcripts/.write_access_check_file.temp"]
        for key in keys:
            try:
                s3.delete_object(Bucket=bucket, Key=key)
            except Exception as exc:
                print(f"Cleanup warning (object s3://{bucket}/{key}): {exc}")
