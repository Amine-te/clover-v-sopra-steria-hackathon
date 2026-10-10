"""VoiceService tests (Requirements 2, 3 and 4) with in-memory fake S3 and Transcribe clients."""
import io
import json
import re

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from clover_v_sopra_steria_hackathon.audio.fixtures import load_fixture
from clover_v_sopra_steria_hackathon.audio.service import (
    AudioNotFoundError,
    FixtureNotFoundError,
    TranscriptionError,
    UploadError,
    VoiceService,
)
from clover_v_sopra_steria_hackathon.config import ConfigError, Settings

BUCKET = "test-bucket"
REPORT_ID = re.compile(r"^rep-[0-9a-f]{32}$")
AUDIO = b"ID3-fake-audio-bytes"


def _client_error(code="AccessDenied", operation="Op"):
    return ClientError({"Error": {"Code": code, "Message": "denied"}}, operation)


class FakeS3:
    def __init__(self, calls, *, fail_put=False, fail_get=False):
        self.calls = calls
        self.objects = {}
        self.fail_put = fail_put
        self.fail_get = fail_get

    def put_object(self, **kwargs):
        self.calls.append(("s3.put_object", kwargs))
        if self.fail_put:
            raise _client_error(operation="PutObject")
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs["Body"]

    def get_object(self, **kwargs):
        self.calls.append(("s3.get_object", kwargs))
        if self.fail_get:
            raise _client_error("NoSuchKey", "GetObject")
        return {"Body": io.BytesIO(self.objects[(kwargs["Bucket"], kwargs["Key"])])}

    def list_objects_v2(self, **kwargs):
        self.calls.append(("s3.list_objects_v2", kwargs))
        keys = [k for (b, k) in self.objects if b == kwargs["Bucket"] and k.startswith(kwargs["Prefix"])]
        return {"Contents": [{"Key": k} for k in keys]} if keys else {"KeyCount": 0}


class FakeTranscribe:
    """Returns `statuses` in order from get_transcription_job; writes the output on COMPLETED."""

    def __init__(self, calls, s3, statuses=("IN_PROGRESS", "COMPLETED"), text="Bonjour tout le monde.",
                 fail_start=False):
        self.calls = calls
        self.s3 = s3
        self.statuses = list(statuses)
        self.text = text
        self.fail_start = fail_start
        self.job = None

    def start_transcription_job(self, **kwargs):
        self.calls.append(("transcribe.start_transcription_job", kwargs))
        if self.fail_start:
            raise _client_error("LimitExceededException", "StartTranscriptionJob")
        self.job = kwargs

    def get_transcription_job(self, **kwargs):
        self.calls.append(("transcribe.get_transcription_job", kwargs))
        status = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
        job = {"TranscriptionJobName": kwargs["TranscriptionJobName"], "TranscriptionJobStatus": status}
        if status == "FAILED":
            job["FailureReason"] = "The media format is invalid."
        if status == "COMPLETED":
            output = {"results": {"transcripts": [{"transcript": self.text}]}}
            self.s3.objects[(self.job["OutputBucketName"], self.job["OutputKey"])] = json.dumps(output).encode()
        return {"TranscriptionJob": job}


class Harness:
    def __init__(self, *, cached=False, bucket=BUCKET, timeout=180.0, s3_kwargs=None, tr_kwargs=None):
        self.calls = []
        self.sleeps = []
        self.s3 = FakeS3(self.calls, **(s3_kwargs or {}))
        self.transcribe = FakeTranscribe(self.calls, self.s3, **(tr_kwargs or {}))
        settings = Settings(_env_file=None, gameday_bucket=bucket, use_cached_transcripts=cached)
        self.service = VoiceService(
            settings, self.s3, self.transcribe, poll_interval=3.0, timeout=timeout, sleep=self.sleeps.append
        )

    def names(self):
        return [name for name, _ in self.calls]

    def params(self, name):
        return [kwargs for n, kwargs in self.calls if n == name]


# Live mode


def test_submit_uploads_then_transcribes():
    h = Harness()
    result = h.service.submit(AUDIO, "mp3", "audio/mpeg")
    assert REPORT_ID.match(result.report_id)
    assert result.audio_s3_key == f"audio/{result.report_id}.mp3"
    assert result.transcript == "Bonjour tout le monde."
    assert result.source == "transcribe"
    assert h.names()[0] == "s3.put_object"
    assert h.names().index("s3.put_object") < h.names().index("transcribe.start_transcription_job")
    put = h.params("s3.put_object")[0]
    assert put == {"Bucket": BUCKET, "Key": result.audio_s3_key, "Body": AUDIO, "ContentType": "audio/mpeg"}


def test_job_parameters():
    h = Harness()
    result = h.service.submit(AUDIO, ".M4A", None)
    job = h.params("transcribe.start_transcription_job")[0]
    assert job["LanguageCode"] == "fr-FR"
    assert job["MediaFormat"] == "mp4"
    assert job["Media"] == {"MediaFileUri": f"s3://{BUCKET}/audio/{result.report_id}.m4a"}
    assert job["OutputBucketName"] == BUCKET
    assert job["OutputKey"] == f"transcripts/{result.report_id}.json"
    assert re.fullmatch(rf"karis-{result.report_id}-[0-9a-f]{{8}}", job["TranscriptionJobName"])
    assert "ContentType" not in h.params("s3.put_object")[0]


def test_language_comes_from_settings():
    h = Harness()
    h.service.settings = Settings(_env_file=None, gameday_bucket=BUCKET, transcribe_language="fr-CA")
    h.service.submit(AUDIO, "wav", None)
    assert h.params("transcribe.start_transcription_job")[0]["LanguageCode"] == "fr-CA"


def test_job_names_unique_per_attempt():
    h = Harness()
    h.service.submit(AUDIO, "mp3", None)
    h.service.submit(AUDIO, "mp3", None)
    names = [job["TranscriptionJobName"] for job in h.params("transcribe.start_transcription_job")]
    assert len(set(names)) == 2


def test_polls_until_completed_and_reads_from_s3():
    h = Harness(tr_kwargs={"statuses": ["QUEUED", "IN_PROGRESS", "IN_PROGRESS", "COMPLETED"]})
    result = h.service.submit(AUDIO, "mp3", None)
    assert len(h.params("transcribe.get_transcription_job")) == 4
    assert h.sleeps == [3.0, 3.0, 3.0]
    get = h.params("s3.get_object")[0]
    assert get == {"Bucket": BUCKET, "Key": f"transcripts/{result.report_id}.json"}


def test_failed_job_keeps_ids_and_audio():
    h = Harness(tr_kwargs={"statuses": ["IN_PROGRESS", "FAILED"]})
    with pytest.raises(TranscriptionError) as info:
        h.service.submit(AUDIO, "mp3", None)
    err = info.value
    assert REPORT_ID.match(err.report_id)
    assert err.audio_s3_key == f"audio/{err.report_id}.mp3"
    assert h.s3.objects[(BUCKET, err.audio_s3_key)] == AUDIO


def test_timeout_raises_transcription_error():
    h = Harness(timeout=9.0, tr_kwargs={"statuses": ["IN_PROGRESS"]})
    with pytest.raises(TranscriptionError) as info:
        h.service.submit(AUDIO, "mp3", None)
    assert info.value.audio_s3_key == f"audio/{info.value.report_id}.mp3"
    assert h.sleeps == [3.0, 3.0, 3.0]
    assert "timed out" in str(info.value)


def test_default_poll_and_timeout():
    service = VoiceService(Settings(_env_file=None), None, None)
    assert service.poll_interval == 3.0
    assert service.timeout == 180.0


@pytest.mark.parametrize(
    ("s3_kwargs", "tr_kwargs"),
    [({}, {"fail_start": True}), ({"fail_get": True}, {})],
)
def test_aws_errors_after_upload_are_transcription_errors(s3_kwargs, tr_kwargs):
    h = Harness(s3_kwargs=s3_kwargs, tr_kwargs=tr_kwargs)
    with pytest.raises(TranscriptionError) as info:
        h.service.submit(AUDIO, "mp3", None)
    assert info.value.audio_s3_key == f"audio/{info.value.report_id}.mp3"


def test_botocore_error_is_wrapped():
    h = Harness()

    def boom(**kwargs):
        raise EndpointConnectionError(endpoint_url="https://transcribe.example")

    h.transcribe.get_transcription_job = boom
    with pytest.raises(TranscriptionError):
        h.service.submit(AUDIO, "mp3", None)


def test_upload_failure_is_not_a_transcription_error():
    h = Harness(s3_kwargs={"fail_put": True})
    with pytest.raises(UploadError) as info:
        h.service.submit(AUDIO, "mp3", None)
    assert REPORT_ID.match(info.value.report_id)
    assert "transcribe.start_transcription_job" not in h.names()


@pytest.mark.parametrize("bucket", [None, "", "   "])
def test_missing_bucket_is_config_error(bucket):
    h = Harness(bucket=bucket)
    with pytest.raises(ConfigError, match="GAMEDAY_BUCKET"):
        h.service.submit(AUDIO, "mp3", None)
    assert h.calls == []


def test_unsupported_extension_rejected():
    h = Harness()
    with pytest.raises(ValueError):
        h.service.submit(AUDIO, "txt", None)
    assert h.calls == []


# Cached mode


def test_cached_mode_never_calls_transcribe():
    h = Harness(cached=True)
    result = h.service.submit(AUDIO, "webm", "audio/webm")
    assert result.source == "cache"
    assert result.transcript == load_fixture("default")
    assert result.audio_s3_key == f"audio/{result.report_id}.webm"
    assert not [n for n in h.names() if n.startswith("transcribe.")]


def test_cached_mode_without_bucket_skips_upload():
    h = Harness(cached=True, bucket=None)
    result = h.service.submit(AUDIO, "mp3", None)
    assert result.audio_s3_key is None
    assert result.transcript == load_fixture("default")
    assert h.calls == []


def test_cached_mode_upload_failure_still_returns_fixture():
    h = Harness(cached=True, s3_kwargs={"fail_put": True})
    result = h.service.submit(AUDIO, "mp3", None)
    assert result.audio_s3_key is None
    assert result.source == "cache"
    assert result.transcript == load_fixture("default")


def test_cached_mode_named_fixture():
    h = Harness(cached=True)
    assert h.service.submit(AUDIO, "mp3", None, fixture="chute").transcript == load_fixture("chute")


@pytest.mark.parametrize("name", ["inconnu", "../default"])
def test_cached_mode_unknown_fixture(name):
    h = Harness(cached=True)
    with pytest.raises(FixtureNotFoundError):
        h.service.submit(AUDIO, "mp3", None, fixture=name)
    assert h.calls == []


# Retry


def test_retry_uses_stored_audio_without_upload():
    h = Harness(tr_kwargs={"statuses": ["FAILED"]})
    with pytest.raises(TranscriptionError) as info:
        h.service.submit(AUDIO, "ogg", None)
    report_id = info.value.report_id
    h.transcribe.statuses = ["IN_PROGRESS", "COMPLETED"]
    h.calls.clear()
    result = h.service.retry(report_id)
    assert result == type(result)(report_id, f"audio/{report_id}.ogg", "Bonjour tout le monde.", "transcribe")
    assert "s3.put_object" not in h.names()
    assert h.params("s3.list_objects_v2")[0] == {"Bucket": BUCKET, "Prefix": f"audio/{report_id}."}
    job = h.params("transcribe.start_transcription_job")[0]
    assert job["MediaFormat"] == "ogg"
    assert job["Media"]["MediaFileUri"] == f"s3://{BUCKET}/audio/{report_id}.ogg"


def test_retry_not_found():
    h = Harness()
    with pytest.raises(AudioNotFoundError):
        h.service.retry("rep-" + "0" * 32)
    assert "transcribe.start_transcription_job" not in h.names()


def test_retry_failure_keeps_key():
    h = Harness()
    h.s3.objects[(BUCKET, "audio/rep-" + "a" * 32 + ".mp3")] = AUDIO
    h.transcribe.statuses = ["FAILED"]
    with pytest.raises(TranscriptionError) as info:
        h.service.retry("rep-" + "a" * 32)
    assert info.value.audio_s3_key == "audio/rep-" + "a" * 32 + ".mp3"


def test_retry_in_cached_mode_returns_default_fixture():
    h = Harness(cached=True, bucket=None)
    result = h.service.retry("rep-" + "b" * 32)
    assert result.source == "cache"
    assert result.transcript == load_fixture("default")
    assert h.calls == []
