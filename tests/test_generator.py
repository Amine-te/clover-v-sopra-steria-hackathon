"""Generator tests (Task 3): determinism, 30-day coverage, invented IDs, seed_store count."""
from datetime import datetime, timezone

import pytest

from clover_v_sopra_steria_hackathon.config import Settings
from clover_v_sopra_steria_hackathon.models import Observation, WearableSample
from clover_v_sopra_steria_hackathon.store.generator import generate, seed_store
from clover_v_sopra_steria_hackathon.store.service import TimelineStore

END = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, ContentType=None):
        self.objects[Key] = Body
        return {}


def test_same_seed_is_deterministic():
    first = generate(end=END, seed=7)
    second = generate(end=END, seed=7)
    assert [o.model_dump() for o in first.observations] == [o.model_dump() for o in second.observations]
    assert [w.model_dump() for w in first.wearables] == [w.model_dump() for w in second.wearables]


def test_different_seed_differs():
    a = generate(end=END, seed=1)
    b = generate(end=END, seed=2)
    assert [o.model_dump() for o in a.observations] != [o.model_dump() for o in b.observations]


def test_thirty_day_coverage():
    data = generate(end=END, days=30, seed=42)
    obs_days = {o.timestamp.date() for o in data.observations}
    wear_days = {w.timestamp.date() for w in data.wearables}
    assert len(obs_days) == 30
    assert len(wear_days) == 30
    assert min(obs_days) == datetime(2026, 10, 2, tzinfo=timezone.utc).date()
    assert max(obs_days) == END.date()


def test_produces_both_models():
    data = generate(end=END, seed=42)
    assert data.observations and all(isinstance(o, Observation) for o in data.observations)
    assert data.wearables and all(isinstance(w, WearableSample) for w in data.wearables)


def test_covers_several_categories_and_severities():
    data = generate(end=END, seed=42)
    categories = {o.category for o in data.observations}
    severities = {o.severity for o in data.observations}
    assert len(categories) >= 5
    # The window is large enough to surface the higher-severity templates.
    assert "watch" in severities
    assert "urgent" in severities


def test_invented_identifiers_and_subject():
    data = generate(subject_id="subject-demo-1", reporter_id="caregiver-demo-1", end=END, seed=42)
    assert all(o.subject_id == "subject-demo-1" for o in data.observations)
    assert all(o.reported_by == "caregiver-demo-1" for o in data.observations)
    assert all(o.id.startswith("obs-") for o in data.observations)
    assert all(w.subject_id == "subject-demo-1" for w in data.wearables)


def test_observations_are_caregiver_voice():
    data = generate(end=END, seed=42)
    assert all(o.source == "caregiver_voice" for o in data.observations)


def test_seed_store_writes_every_observation():
    data = generate(end=END, seed=42)
    store = TimelineStore(Settings(_env_file=None, gameday_bucket="b"), s3=FakeS3())
    keys = seed_store(store, data)
    assert len(keys) == len(data.observations)
    assert len(store.s3.objects) == len(data.observations)
