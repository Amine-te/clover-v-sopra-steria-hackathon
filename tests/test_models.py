"""Shared data model tests (Requirement 3). All data is fictional."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from clover_v_sopra_steria_hackathon.models import Observation, SentMessage, WearableSample

CONTRACTS_DIR = Path(__file__).resolve().parents[1] / "specs" / "contracts"
CONTRACT_MODELS = {
    "observation.md": Observation,
    "wearable-sample.md": WearableSample,
}
JSON_BLOCK = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)

OBSERVATION = {
    "id": "obs-test-1",
    "timestamp": "2026-10-10T08:30:00+02:00",
    "reported_at": "2026-10-10T20:05:00+02:00",
    "subject_id": "subject-demo-1",
    "category": "sleep",
    "value": "Woke up twice during the night",
    "severity": "info",
    "source": "caregiver_voice",
    "reported_by": "caregiver-demo-1",
    "confidence": 0.8,
    "transcript_span": "elle s'est réveillée deux fois",
}
WEARABLE = {
    "timestamp": "2026-10-10T03:00:00+02:00",
    "subject_id": "subject-demo-1",
    "heart_rate_bpm": 62,
    "sleep_state": "deep",
    "spo2_pct": 97.5,
    "steps": 0,
}
SENT_MESSAGE = {
    "id": "msg-test-1",
    "recipient": "family",
    "channel": "mock",
    "body": "Résumé du jour",
    "observation_ids": ["obs-test-1"],
    "sent_at": "2026-10-10T20:10:00+02:00",
}


def contract_examples():
    for path in sorted(CONTRACTS_DIR.glob("*.md")):
        for index, block in enumerate(JSON_BLOCK.findall(path.read_text(encoding="utf-8"))):
            yield pytest.param(path.name, json.loads(block), id=f"{path.name}#{index}")


def error_fields(exc: ValidationError) -> set[str]:
    return {str(error["loc"][0]) for error in exc.errors() if error["loc"]}


def assert_rejected(model, data, field):
    with pytest.raises(ValidationError) as info:
        model.model_validate(data)
    assert field in error_fields(info.value)


def test_contracts_have_examples():
    assert list(contract_examples()), "expected at least one JSON example in specs/contracts/"


@pytest.mark.parametrize(("filename", "example"), list(contract_examples()))
def test_contract_example_validates(filename, example):
    assert filename in CONTRACT_MODELS, f"no model mapped for JSON example in {filename}"
    instance = CONTRACT_MODELS[filename].model_validate(example)
    dumped = json.loads(instance.model_dump_json())
    for key, value in example.items():
        if key in ("timestamp", "reported_at", "sent_at"):
            assert getattr(instance, key) == datetime.fromisoformat(value)
            assert getattr(instance, key).utcoffset() == datetime.fromisoformat(value).utcoffset()
        else:
            assert getattr(instance, key) == value
            assert dumped[key] == value


def test_observation_example_keeps_offset():
    path = CONTRACTS_DIR / "observation.md"
    example = json.loads(JSON_BLOCK.findall(path.read_text(encoding="utf-8"))[0])
    obs = Observation.model_validate(example)
    assert obs.timestamp.utcoffset() == timedelta(hours=2)
    assert obs.reported_at.utcoffset() == timedelta(hours=2)
    assert obs.model_dump(mode="json")["timestamp"].endswith("+02:00")


def test_valid_samples():
    Observation.model_validate(OBSERVATION)
    WearableSample.model_validate(WEARABLE)
    SentMessage.model_validate(SENT_MESSAGE)
    SentMessage.model_validate({**SENT_MESSAGE, "observation_ids": []})
    Observation.model_validate({**OBSERVATION, "source": "wearable", "transcript_span": ""})


@pytest.mark.parametrize("value", [0, 1, 0.0, 1.0])
def test_confidence_boundaries_accepted(value):
    assert Observation.model_validate({**OBSERVATION, "confidence": value}).confidence == value


@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_confidence_out_of_range(value):
    assert_rejected(Observation, {**OBSERVATION, "confidence": value}, "confidence")


@pytest.mark.parametrize("value", [0, 100])
def test_spo2_boundaries_accepted(value):
    assert WearableSample.model_validate({**WEARABLE, "spo2_pct": value}).spo2_pct == value


@pytest.mark.parametrize(
    ("field", "value"),
    [("spo2_pct", -1), ("spo2_pct", 101), ("heart_rate_bpm", -1), ("steps", -1)],
)
def test_wearable_out_of_range(field, value):
    assert_rejected(WearableSample, {**WEARABLE, field: value}, field)


@pytest.mark.parametrize(
    ("model", "base", "field", "value"),
    [
        (Observation, OBSERVATION, "category", "Sleep"),
        (Observation, OBSERVATION, "category", "diagnosis"),
        (Observation, OBSERVATION, "severity", "URGENT"),
        (Observation, OBSERVATION, "source", "Wearable"),
        (WearableSample, WEARABLE, "sleep_state", "REM"),
        (WearableSample, WEARABLE, "sleep_state", "Deep"),
        (SentMessage, SENT_MESSAGE, "recipient", "Doctor"),
        (SentMessage, SENT_MESSAGE, "recipient", "neighbour"),
        (SentMessage, SENT_MESSAGE, "channel", "email"),
        (SentMessage, SENT_MESSAGE, "channel", "SNS"),
    ],
)
def test_enum_values_rejected(model, base, field, value):
    assert_rejected(model, {**base, field: value}, field)


@pytest.mark.parametrize(
    ("model", "base", "field"),
    [
        (Observation, OBSERVATION, "timestamp"),
        (Observation, OBSERVATION, "reported_at"),
        (WearableSample, WEARABLE, "timestamp"),
        (SentMessage, SENT_MESSAGE, "sent_at"),
    ],
)
def test_naive_datetime_rejected(model, base, field):
    assert_rejected(model, {**base, field: "2026-10-10T08:30:00"}, field)


@pytest.mark.parametrize(
    ("model", "base", "field"),
    [(Observation, OBSERVATION, name) for name in OBSERVATION]
    + [(WearableSample, WEARABLE, "timestamp"), (WearableSample, WEARABLE, "subject_id")]
    + [(SentMessage, SENT_MESSAGE, name) for name in SENT_MESSAGE],
)
def test_missing_required_field(model, base, field):
    data = {key: value for key, value in base.items() if key != field}
    assert_rejected(model, data, field)


@pytest.mark.parametrize(
    ("model", "base", "field", "value"),
    [
        (Observation, OBSERVATION, "confidence", "very sure"),
        (Observation, OBSERVATION, "timestamp", "yesterday"),
        (WearableSample, WEARABLE, "heart_rate_bpm", "fast"),
        (WearableSample, WEARABLE, "steps", 1.5),
        (SentMessage, SENT_MESSAGE, "observation_ids", "obs-test-1"),
    ],
)
def test_wrong_type_rejected(model, base, field, value):
    assert_rejected(model, {**base, field: value}, field)


@pytest.mark.parametrize(
    ("model", "base"),
    [(Observation, OBSERVATION), (WearableSample, WEARABLE), (SentMessage, SENT_MESSAGE)],
)
def test_unknown_field_rejected(model, base):
    assert_rejected(model, {**base, "diagnosis": "none"}, "diagnosis")


def test_wearable_minimal_is_valid_and_omits_optionals():
    sample = WearableSample(
        timestamp=datetime(2026, 10, 10, 3, 0, tzinfo=timezone(timedelta(hours=2))),
        subject_id="subject-demo-1",
    )
    data = json.loads(sample.model_dump_json())
    assert set(data) == {"timestamp", "subject_id"}
    assert set(sample.model_dump()) == {"timestamp", "subject_id"}
    assert "null" not in sample.model_dump_json()


def test_wearable_partial_omits_only_missing():
    sample = WearableSample.model_validate({**WEARABLE, "sleep_state": None, "steps": None})
    assert set(json.loads(sample.model_dump_json())) == {
        "timestamp", "subject_id", "heart_rate_bpm", "spo2_pct",
    }
