"""TimelineStore tests (Task 2) against an in-memory fake S3 (no network)."""
import io
import json
from datetime import datetime, timedelta, timezone

import pytest
from botocore.exceptions import ClientError

from clover_v_sopra_steria_hackathon.config import ConfigError, Settings
from clover_v_sopra_steria_hackathon.models import Observation
from clover_v_sopra_steria_hackathon.store.keys import observation_key
from clover_v_sopra_steria_hackathon.store.service import Period, StoreError, TimelineStore

BUCKET = "karis-test-bucket"


class FakeS3:
    """Minimal in-memory S3: put/get/list_objects_v2 with Prefix and ContinuationToken paging."""

    def __init__(self, page_size: int = 1000):
        self.objects: dict[str, dict] = {}
        self.page_size = page_size

    def put_object(self, Bucket, Key, Body, ContentType=None):
        assert Bucket == BUCKET
        self.objects[Key] = {"Body": Body, "ContentType": ContentType}
        return {}

    def get_object(self, Bucket, Key):
        assert Bucket == BUCKET
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": io.BytesIO(self.objects[Key]["Body"])}

    def list_objects_v2(self, Bucket, Prefix="", ContinuationToken=None):
        assert Bucket == BUCKET
        keys = sorted(k for k in self.objects if k.startswith(Prefix))
        start = int(ContinuationToken) if ContinuationToken is not None else 0
        page = keys[start : start + self.page_size]
        next_start = start + self.page_size
        truncated = next_start < len(keys)
        response = {"Contents": [{"Key": k} for k in page], "IsTruncated": truncated}
        if truncated:
            response["NextContinuationToken"] = str(next_start)
        return response


class ExplodingS3:
    """S3 double whose operations raise a ClientError with a known code."""

    def __init__(self, code="AccessDenied"):
        self.code = code

    def put_object(self, **kwargs):
        raise ClientError({"Error": {"Code": self.code}}, "PutObject")

    def list_objects_v2(self, **kwargs):
        raise ClientError({"Error": {"Code": self.code}}, "ListObjectsV2")

    def get_object(self, **kwargs):
        raise ClientError({"Error": {"Code": self.code}}, "GetObject")


def _settings(bucket=BUCKET):
    return Settings(_env_file=None, gameday_bucket=bucket)


def _obs(obs_id, when, *, subject="subject-demo-1", category="sleep", severity="info"):
    return Observation(
        id=obs_id,
        timestamp=when,
        reported_at=datetime(2026, 10, 10, 20, 5, tzinfo=timezone.utc),
        subject_id=subject,
        category=category,
        value="valeur factuelle",
        severity=severity,
        source="caregiver_voice",
        reported_by="caregiver-demo-1",
        confidence=0.8,
        transcript_span="span",
    )


@pytest.fixture
def store():
    return TimelineStore(_settings(), s3=FakeS3())


def test_save_returns_key(store):
    obs = _obs("obs-1", datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc))
    assert store.save(obs) == observation_key(obs)


def test_save_body_is_json_with_iso_offsets(store):
    offset = timezone(timedelta(hours=2))
    obs = _obs("obs-1", datetime(2026, 10, 10, 8, 0, tzinfo=offset))
    key = store.save(obs)
    stored = store.s3.objects[key]
    assert stored["ContentType"] == "application/json"
    body = json.loads(stored["Body"].decode("utf-8"))
    assert body["timestamp"] == "2026-10-10T08:00:00+02:00"
    assert body["id"] == "obs-1"


def test_save_many_returns_all_keys(store):
    observations = [
        _obs("obs-1", datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)),
        _obs("obs-2", datetime(2026, 10, 11, 9, 0, tzinfo=timezone.utc)),
    ]
    keys = store.save_many(observations)
    assert keys == [observation_key(o) for o in observations]
    assert len(store.s3.objects) == 2


def test_overwrite_is_idempotent(store):
    first = _obs("obs-1", datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc), severity="info")
    second = _obs("obs-1", datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc), severity="urgent")
    assert store.save(first) == store.save(second)
    assert len(store.s3.objects) == 1
    [result] = store.query("subject-demo-1")
    assert result.severity == "urgent"


def test_query_sorted_by_timestamp(store):
    store.save(_obs("obs-late", datetime(2026, 10, 12, 8, 0, tzinfo=timezone.utc)))
    store.save(_obs("obs-early", datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)))
    store.save(_obs("obs-mid", datetime(2026, 10, 11, 8, 0, tzinfo=timezone.utc)))
    ids = [o.id for o in store.query("subject-demo-1")]
    assert ids == ["obs-early", "obs-mid", "obs-late"]


def test_query_period_inclusive(store):
    store.save(_obs("obs-9", datetime(2026, 10, 9, 8, 0, tzinfo=timezone.utc)))
    store.save(_obs("obs-10", datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)))
    store.save(_obs("obs-11", datetime(2026, 10, 11, 8, 0, tzinfo=timezone.utc)))
    store.save(_obs("obs-12", datetime(2026, 10, 12, 8, 0, tzinfo=timezone.utc)))
    period = Period(
        start=datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc),
        end=datetime(2026, 10, 11, 8, 0, tzinfo=timezone.utc),
    )
    ids = [o.id for o in store.query("subject-demo-1", period=period)]
    assert ids == ["obs-10", "obs-11"]


def test_query_open_bounds(store):
    store.save(_obs("obs-9", datetime(2026, 10, 9, 8, 0, tzinfo=timezone.utc)))
    store.save(_obs("obs-11", datetime(2026, 10, 11, 8, 0, tzinfo=timezone.utc)))
    only_end = Period(end=datetime(2026, 10, 10, 0, 0, tzinfo=timezone.utc))
    assert [o.id for o in store.query("subject-demo-1", period=only_end)] == ["obs-9"]
    only_start = Period(start=datetime(2026, 10, 10, 0, 0, tzinfo=timezone.utc))
    assert [o.id for o in store.query("subject-demo-1", period=only_start)] == ["obs-11"]


def test_query_category_filter(store):
    store.save(_obs("obs-s", datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc), category="sleep"))
    store.save(_obs("obs-m", datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc), category="medication"))
    ids = [o.id for o in store.query("subject-demo-1", category="medication")]
    assert ids == ["obs-m"]


def test_query_severity_filter(store):
    store.save(_obs("obs-info", datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc), severity="info"))
    store.save(_obs("obs-urgent", datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc), severity="urgent"))
    ids = [o.id for o in store.query("subject-demo-1", severity="urgent")]
    assert ids == ["obs-urgent"]


def test_query_no_match_returns_empty(store):
    store.save(_obs("obs-1", datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)))
    assert store.query("other-subject") == []


def test_query_paginates_across_pages():
    store = TimelineStore(_settings(), s3=FakeS3(page_size=2))
    base = datetime(2026, 10, 10, 0, 0, tzinfo=timezone.utc)
    for index in range(5):
        store.save(_obs(f"obs-{index:02d}", base + timedelta(hours=index)))
    ids = [o.id for o in store.query("subject-demo-1")]
    assert ids == ["obs-00", "obs-01", "obs-02", "obs-03", "obs-04"]


def test_query_skips_invalid_json(store):
    good = _obs("obs-good", datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc))
    store.save(good)
    store.s3.objects["observations/subject-demo-1/2026-10-10/obs-bad.json"] = {
        "Body": b"{ not valid json",
        "ContentType": "application/json",
    }
    results = store.query("subject-demo-1")
    assert [o.id for o in results] == ["obs-good"]


def test_no_bucket_raises_config_error():
    store = TimelineStore(_settings(bucket=None), s3=FakeS3())
    obs = _obs("obs-1", datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc))
    with pytest.raises(ConfigError) as excinfo:
        store.save(obs)
    assert "GAMEDAY_BUCKET" in str(excinfo.value)


def test_s3_error_wrapped_in_store_error_on_save():
    store = TimelineStore(_settings(), s3=ExplodingS3("AccessDenied"))
    obs = _obs("obs-1", datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc))
    with pytest.raises(StoreError) as excinfo:
        store.save(obs)
    assert excinfo.value.aws_code == "AccessDenied"


def test_s3_error_wrapped_in_store_error_on_query():
    store = TimelineStore(_settings(), s3=ExplodingS3("InternalError"))
    with pytest.raises(StoreError) as excinfo:
        store.query("subject-demo-1")
    assert excinfo.value.aws_code == "InternalError"
