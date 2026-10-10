"""Offline golden cases (Task 3): run the service against canned Converse responses per fixture.

Each golden file pairs a fictional transcript with the raw items an acceptable extraction would
produce. Running the real service post-processing over those items checks the result shape,
the grounding rule and the absence of diagnosis language, without any live model call.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from clover_v_sopra_steria_hackathon.audio.fixtures import load_fixture
from clover_v_sopra_steria_hackathon.config import Settings
from clover_v_sopra_steria_hackathon.extraction.service import ExtractionRequest, ExtractionService
from clover_v_sopra_steria_hackathon.models import Category, Observation

GOLDEN_DIR = Path(__file__).resolve().parent / "fixtures" / "golden"
REPORTED_AT = datetime(2026, 10, 10, 20, 5, tzinfo=timezone.utc)

# A fact must never read as a diagnosis or named condition (constitution rule 2).
DIAGNOSIS_KEYWORDS = [
    "diagnostic",
    "dépression",
    "alzheimer",
    "démence",
    "infection",
    "maladie",
    "avc",
    "parkinson",
]

GOLDEN_CASES = sorted(GOLDEN_DIR.glob("*.json"))


class CannedBedrock:
    def __init__(self, items):
        self._text = json.dumps(items)

    def converse(self, **kwargs):
        return {"output": {"message": {"content": [{"text": self._text}]}}}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _run(case):
    transcript = load_fixture(case["fixture"])
    service = ExtractionService(Settings(_env_file=None), CannedBedrock(case["canned_response"]))
    request = ExtractionRequest(
        transcript=transcript,
        subject_id="subject-demo-1",
        reported_by="caregiver-demo-1",
        reported_at=REPORTED_AT,
    )
    return transcript, service.extract(request)


def test_golden_dir_has_one_case_per_fixture():
    fixtures = {path.stem for path in (GOLDEN_DIR.parent / "transcripts").glob("*.txt")}
    golden = {path.stem for path in GOLDEN_CASES}
    assert golden == fixtures
    assert len(golden) >= 6


@pytest.mark.parametrize("path", GOLDEN_CASES, ids=[p.stem for p in GOLDEN_CASES])
def test_golden_case(path):
    case = _load(path)
    transcript, observations = _run(case)

    # Every returned item validates against the contract and carries authoritative fields.
    normalized_transcript = " ".join(transcript.split()).lower()
    for obs in observations:
        assert isinstance(obs, Observation)
        assert obs.source == "caregiver_voice"
        assert obs.subject_id == "subject-demo-1"
        # Grounding: the span survives only if present in the transcript.
        assert " ".join(obs.transcript_span.split()).lower() in normalized_transcript
        # No diagnosis language in the stated fact.
        lowered = obs.value.lower()
        for keyword in DIAGNOSIS_KEYWORDS:
            assert keyword not in lowered, f"diagnosis keyword {keyword!r} in {obs.value!r}"

    produced = {obs.category for obs in observations}
    assert produced <= set(Category.__args__)
    # The expected categories (that we grounded in the canned response) are produced.
    assert set(case["expected_categories"]) <= produced or not case["expected_categories"]


def test_near_empty_fixture_yields_no_observations():
    case = _load(GOLDEN_DIR / "rien-a-signaler.json")
    _, observations = _run(case)
    assert observations == []
