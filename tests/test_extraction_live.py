"""Live extraction: a real Bedrock Converse call with Claude Haiku 4.5 on one fixture transcript.

This is the first live Claude call in the project. If it fails with AccessDeniedException or
ValidationException, the Bedrock model access or the bedrock:InvokeModel IAM permission is not
yet in place; see docs/steps/000-project-foundations.md "Manual AWS configuration".
"""
from datetime import datetime, timezone

import pytest

from clover_v_sopra_steria_hackathon.audio.fixtures import load_fixture
from clover_v_sopra_steria_hackathon.config import Settings
from clover_v_sopra_steria_hackathon.extraction.service import ExtractionRequest, ExtractionService
from clover_v_sopra_steria_hackathon.models import Observation

pytestmark = pytest.mark.aws_live

# A fact must never read as a diagnosis or a named condition (constitution rule 2).
DIAGNOSIS_KEYWORDS = ["diagnostic", "dépression", "alzheimer", "infection", "maladie"]


def test_extraction_live(aws_session):
    settings = Settings()
    service = ExtractionService(settings, aws_session.client("bedrock-runtime"))
    transcript = load_fixture("default")
    request = ExtractionRequest(
        transcript=transcript,
        subject_id="subject-demo-1",
        reported_by="caregiver-demo-1",
        reported_at=datetime(2026, 10, 10, 20, 5, tzinfo=timezone.utc),
    )

    observations = service.extract(request)

    print(f"Model: {settings.bedrock_model_extract}")
    print(f"Extracted {len(observations)} observation(s):")
    for obs in observations:
        print(f"  [{obs.severity}] {obs.category} — {obs.value}  (span: {obs.transcript_span!r})")

    assert observations, "expected at least one observation from the default fixture"
    normalized_transcript = " ".join(transcript.split()).lower()
    for obs in observations:
        assert isinstance(obs, Observation)
        assert obs.source == "caregiver_voice"
        assert obs.subject_id == "subject-demo-1"
        assert obs.reported_by == "caregiver-demo-1"
        # Grounding is enforced in code, so every span must be in the transcript.
        assert " ".join(obs.transcript_span.split()).lower() in normalized_transcript
        lowered = obs.value.lower()
        for keyword in DIAGNOSIS_KEYWORDS:
            assert keyword not in lowered, f"diagnosis keyword {keyword!r} in value {obs.value!r}"
