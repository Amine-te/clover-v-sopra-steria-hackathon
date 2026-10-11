"""S3 key layout tests (Task 1): observation_key, subject_prefix, day_prefixes."""
from datetime import datetime, timedelta, timezone

from clover_v_sopra_steria_hackathon.models import Observation
from clover_v_sopra_steria_hackathon.store.keys import day_prefixes, observation_key, subject_prefix

PARIS = timezone(timedelta(hours=2))


def _obs(obs_id="obs-0001", subject_id="subject-demo-1", timestamp=None):
    timestamp = timestamp or datetime(2026, 10, 10, 8, 30, tzinfo=timezone.utc)
    return Observation(
        id=obs_id,
        timestamp=timestamp,
        reported_at=datetime(2026, 10, 10, 20, 5, tzinfo=timezone.utc),
        subject_id=subject_id,
        category="medication",
        value="Traitement du matin non pris",
        severity="watch",
        source="caregiver_voice",
        reported_by="caregiver-demo-1",
        confidence=0.9,
        transcript_span="il a refusé son traitement ce matin",
    )


def test_observation_key_format():
    obs = _obs(obs_id="obs-abc", subject_id="subject-7")
    assert observation_key(obs) == "observations/subject-7/2026-10-10/obs-abc.json"


def test_observation_key_date_is_utc():
    # 00:30 at +02:00 is 22:30 the previous day in UTC.
    obs = _obs(timestamp=datetime(2026, 10, 11, 0, 30, tzinfo=PARIS))
    assert observation_key(obs) == "observations/subject-demo-1/2026-10-10/obs-0001.json"


def test_subject_prefix():
    assert subject_prefix("subject-demo-1") == "observations/subject-demo-1/"


def test_day_prefixes_single_day():
    start = datetime(2026, 10, 10, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 10, 10, 23, 59, tzinfo=timezone.utc)
    assert day_prefixes("s1", start, end) == ["observations/s1/2026-10-10/"]


def test_day_prefixes_multi_day_inclusive():
    start = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
    end = datetime(2026, 10, 12, 1, 0, tzinfo=timezone.utc)
    assert day_prefixes("s1", start, end) == [
        "observations/s1/2026-10-10/",
        "observations/s1/2026-10-11/",
        "observations/s1/2026-10-12/",
    ]


def test_day_prefixes_month_boundary():
    start = datetime(2026, 1, 30, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 2, 2, 0, 0, tzinfo=timezone.utc)
    assert day_prefixes("s1", start, end) == [
        "observations/s1/2026-01-30/",
        "observations/s1/2026-01-31/",
        "observations/s1/2026-02-01/",
        "observations/s1/2026-02-02/",
    ]


def test_day_prefixes_uses_utc_days():
    # start/end given in +02:00 collapse to their UTC days.
    start = datetime(2026, 10, 11, 1, 0, tzinfo=PARIS)  # 2026-10-10 23:00 UTC
    end = datetime(2026, 10, 11, 1, 30, tzinfo=PARIS)  # 2026-10-10 23:30 UTC
    assert day_prefixes("s1", start, end) == ["observations/s1/2026-10-10/"]


def test_day_prefixes_empty_when_end_before_start():
    start = datetime(2026, 10, 12, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 10, 10, 0, 0, tzinfo=timezone.utc)
    assert day_prefixes("s1", start, end) == []
