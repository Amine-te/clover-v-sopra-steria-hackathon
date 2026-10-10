"""Property-based JSON round-trip tests for the shared models (Requirement 3.9)."""
import json
from datetime import datetime, timedelta, timezone
from typing import get_args

from hypothesis import given, settings
from hypothesis import strategies as st

from clover_v_sopra_steria_hackathon.models import (
    Category,
    Channel,
    Observation,
    RecipientRole,
    SentMessage,
    Severity,
    SleepState,
    Source,
    WearableSample,
)

EXAMPLES = settings(max_examples=150, deadline=None)

# Fixed-offset time zones from -12:00 to +14:00 in 15-minute steps.
offsets = st.integers(min_value=-48, max_value=56).map(lambda q: timezone(timedelta(minutes=15 * q)))
aware_datetimes = st.datetimes(
    min_value=datetime(2000, 1, 1), max_value=datetime(2100, 1, 1), timezones=offsets,
)
text = st.text(max_size=40)


def enum(literal):
    return st.sampled_from(get_args(literal))


observations = st.builds(
    Observation,
    id=text,
    timestamp=aware_datetimes,
    reported_at=aware_datetimes,
    subject_id=text,
    category=enum(Category),
    value=text,
    severity=enum(Severity),
    source=enum(Source),
    reported_by=text,
    confidence=st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    transcript_span=text,
)

wearable_samples = st.builds(
    WearableSample,
    timestamp=aware_datetimes,
    subject_id=text,
    heart_rate_bpm=st.none() | st.integers(min_value=0, max_value=250),
    sleep_state=st.none() | enum(SleepState),
    spo2_pct=st.none() | st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
    steps=st.none() | st.integers(min_value=0, max_value=100_000),
)

sent_messages = st.builds(
    SentMessage,
    id=text,
    recipient=enum(RecipientRole),
    channel=enum(Channel),
    body=text,
    observation_ids=st.lists(text, max_size=5),
    sent_at=aware_datetimes,
)


def assert_round_trip(instance, datetime_fields):
    restored = type(instance).model_validate_json(instance.model_dump_json())
    assert restored == instance
    for field in datetime_fields:
        assert getattr(restored, field).utcoffset() == getattr(instance, field).utcoffset()


@EXAMPLES
@given(observations)
def test_observation_round_trip(obs):
    assert_round_trip(obs, ["timestamp", "reported_at"])


@EXAMPLES
@given(wearable_samples)
def test_wearable_sample_round_trip(sample):
    assert None not in json.loads(sample.model_dump_json()).values()
    assert_round_trip(sample, ["timestamp"])


@EXAMPLES
@given(sent_messages)
def test_sent_message_round_trip(message):
    assert_round_trip(message, ["sent_at"])
