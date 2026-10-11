"""Live timeline store round-trip (Task 5): save a few fictional Observations to the real bucket,
query them back in timestamp order, and delete every object created.

Marked aws_live. Uses a unique subject_id per run so concurrent runs never clash, and cleans up
in a finally block even if an assertion fails.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from clover_v_sopra_steria_hackathon.config import Settings
from clover_v_sopra_steria_hackathon.models import Observation
from clover_v_sopra_steria_hackathon.store.keys import subject_prefix
from clover_v_sopra_steria_hackathon.store.service import TimelineStore

pytestmark = pytest.mark.aws_live


def _observation(subject_id, obs_id, when, category, severity):
    return Observation(
        id=obs_id,
        timestamp=when,
        reported_at=datetime(2026, 10, 10, 20, 5, tzinfo=timezone.utc),
        subject_id=subject_id,
        category=category,
        value="valeur factuelle de démonstration",
        severity=severity,
        source="caregiver_voice",
        reported_by="caregiver-demo-1",
        confidence=0.9,
        transcript_span="note de démonstration",
    )


def _delete_all(s3, bucket, subject_id):
    """Delete every object under the subject prefix (best-effort cleanup)."""
    token = None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": subject_prefix(subject_id)}
        if token:
            kwargs["ContinuationToken"] = token
        response = s3.list_objects_v2(**kwargs)
        for item in response.get("Contents", []):
            s3.delete_object(Bucket=bucket, Key=item["Key"])
        if response.get("IsTruncated"):
            token = response.get("NextContinuationToken")
        else:
            break


def test_timeline_store_live_round_trip(aws_session, bucket):
    settings = Settings(gameday_bucket=bucket)
    s3 = aws_session.client("s3")
    store = TimelineStore(settings, s3=s3)

    subject_id = f"subject-live-{uuid4().hex[:12]}"
    base = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    observations = [
        _observation(subject_id, "obs-c", base + timedelta(days=2), "medication", "watch"),
        _observation(subject_id, "obs-a", base, "sleep", "info"),
        _observation(subject_id, "obs-b", base + timedelta(days=1), "mobility_falls", "urgent"),
    ]

    try:
        keys = store.save_many(observations)
        assert len(keys) == 3

        results = store.query(subject_id)
        print(f"Queried back {len(results)} observation(s) for {subject_id}:")
        for obs in results:
            print(f"  {obs.timestamp.isoformat()} [{obs.severity}] {obs.category} — {obs.value}")

        assert [o.id for o in results] == ["obs-a", "obs-b", "obs-c"]
        assert [o.category for o in results] == ["sleep", "mobility_falls", "medication"]

        urgent = store.query(subject_id, severity="urgent")
        assert [o.id for o in urgent] == ["obs-b"]
    finally:
        _delete_all(s3, bucket, subject_id)
