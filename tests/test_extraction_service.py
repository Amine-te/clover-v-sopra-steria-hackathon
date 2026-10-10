"""ExtractionService post-processing and Converse wiring (Task 2) with a fake Bedrock client."""
import json
from datetime import datetime, timezone

import pytest
from botocore.exceptions import ClientError

from clover_v_sopra_steria_hackathon.config import Settings
from clover_v_sopra_steria_hackathon.extraction.service import (
    ExtractionError,
    ExtractionRequest,
    ExtractionService,
)
from clover_v_sopra_steria_hackathon.models import Observation

REPORTED_AT = datetime(2026, 10, 10, 20, 5, tzinfo=timezone.utc)
TRANSCRIPT = "Elle a mal dormi cette nuit. Elle a pris ses médicaments du matin."


class FakeBedrock:
    """Returns a canned Converse response and records the call kwargs."""

    def __init__(self, text="[]", error=None):
        self.text = text
        self.error = error
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return {"output": {"message": {"content": [{"text": self.text}]}}}


def _response(items):
    return json.dumps(items)


def _request(transcript=TRANSCRIPT):
    return ExtractionRequest(
        transcript=transcript,
        subject_id="subject-demo-1",
        reported_by="caregiver-demo-1",
        reported_at=REPORTED_AT,
    )


def _service(bedrock, **kwargs):
    return ExtractionService(Settings(_env_file=None), bedrock, **kwargs)


def _item(**overrides):
    base = {
        "category": "sleep",
        "value": "a mal dormi cette nuit",
        "severity": "watch",
        "confidence": 0.8,
        "transcript_span": "Elle a mal dormi cette nuit",
    }
    base.update(overrides)
    return base


def test_authoritative_fields_from_request():
    service = _service(FakeBedrock(_response([_item()])))
    [obs] = service.extract(_request())
    assert isinstance(obs, Observation)
    assert obs.subject_id == "subject-demo-1"
    assert obs.reported_by == "caregiver-demo-1"
    assert obs.reported_at == REPORTED_AT
    assert obs.source == "caregiver_voice"
    assert obs.category == "sleep"
    assert obs.severity == "watch"


def test_ids_are_unique_and_prefixed():
    items = [_item(), _item(transcript_span="Elle a pris ses médicaments du matin")]
    service = _service(FakeBedrock(_response(items)))
    result = service.extract(_request())
    ids = [obs.id for obs in result]
    assert all(i.startswith("obs-") for i in ids)
    assert len(set(ids)) == len(ids) == 2


def test_timestamp_defaults_to_reported_at():
    [obs] = _service(FakeBedrock(_response([_item()]))).extract(_request())
    assert obs.timestamp == REPORTED_AT


def test_timestamp_uses_valid_aware_event_time():
    event = "2026-10-10T03:00:00+02:00"
    [obs] = _service(FakeBedrock(_response([_item(event_time=event)]))).extract(_request())
    assert obs.timestamp == datetime.fromisoformat(event)


def test_naive_event_time_falls_back_to_reported_at():
    [obs] = _service(FakeBedrock(_response([_item(event_time="2026-10-10T03:00:00")]))).extract(_request())
    assert obs.timestamp == REPORTED_AT


def test_invalid_item_dropped_valid_kept():
    # The second item is ungrounded (its span is not in the transcript), so it is dropped.
    items = [_item(), _item(transcript_span="texte absent du transcript")]
    [obs] = _service(FakeBedrock(_response(items))).extract(_request())
    assert obs.transcript_span == "Elle a mal dormi cette nuit"


def test_confidence_clamped_to_unit_interval():
    high = _item(confidence=5)
    low = _item(confidence=-2, transcript_span="Elle a pris ses médicaments du matin")
    result = _service(FakeBedrock(_response([high, low]))).extract(_request())
    assert result[0].confidence == 1.0
    assert result[1].confidence == 0.0


def test_unknown_category_and_severity_defaulted():
    item = _item(category="hallucinated", severity="critique")
    [obs] = _service(FakeBedrock(_response([item]))).extract(_request())
    assert obs.category == "logistics"
    assert obs.severity == "info"


def test_ungrounded_span_dropped():
    item = _item(transcript_span="elle a couru un marathon")
    assert _service(FakeBedrock(_response([item]))).extract(_request()) == []


def test_grounding_is_case_and_whitespace_insensitive():
    item = _item(transcript_span="ELLE   a   MAL   dormi cette nuit")
    assert len(_service(FakeBedrock(_response([item]))).extract(_request())) == 1


def test_empty_span_dropped():
    assert _service(FakeBedrock(_response([_item(transcript_span="")]))).extract(_request()) == []


def test_empty_transcript_returns_empty_without_calling_model():
    fake = FakeBedrock(_response([_item()]))
    assert _service(fake).extract(_request(transcript="   ")) == []
    assert fake.calls == []


def test_empty_array_returns_empty():
    assert _service(FakeBedrock("[]")).extract(_request()) == []


def test_client_error_becomes_extraction_error_with_code():
    error = ClientError({"Error": {"Code": "AccessDeniedException"}}, "Converse")
    service = _service(FakeBedrock(error=error))
    with pytest.raises(ExtractionError) as excinfo:
        service.extract(_request())
    assert excinfo.value.aws_code == "AccessDeniedException"


def test_converse_wiring_model_temperature_tokens():
    fake = FakeBedrock(_response([]))
    _service(fake, max_tokens=1500, temperature=0.0).extract(_request())
    [call] = fake.calls
    settings = Settings(_env_file=None)
    assert call["modelId"] == settings.bedrock_model_extract
    assert call["inferenceConfig"]["temperature"] == 0.0
    assert call["inferenceConfig"]["maxTokens"] == 1500
    assert call["system"][0]["text"]
    assert call["messages"][0]["role"] == "user"


def test_handles_fenced_and_prose_output():
    fenced = "```json\n" + _response([_item()]) + "\n```"
    assert len(_service(FakeBedrock(fenced)).extract(_request())) == 1
