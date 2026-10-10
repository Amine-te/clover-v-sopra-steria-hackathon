"""Extraction API tests (Task 4) with the ExtractionService replaced through dependency overrides."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from clover_v_sopra_steria_hackathon.api import create_app
from clover_v_sopra_steria_hackathon.config import Settings
from clover_v_sopra_steria_hackathon.extraction import routes
from clover_v_sopra_steria_hackathon.extraction.service import ExtractionError
from clover_v_sopra_steria_hackathon.models import Observation

REPORTED_AT = datetime(2026, 10, 10, 20, 5, tzinfo=timezone.utc)

OBS = Observation(
    id="obs-abc123",
    timestamp=REPORTED_AT,
    reported_at=REPORTED_AT,
    subject_id="subject-demo-1",
    category="sleep",
    value="a mal dormi",
    severity="watch",
    source="caregiver_voice",
    reported_by="caregiver-demo-1",
    confidence=0.8,
    transcript_span="a mal dormi",
)


class StubService:
    def __init__(self, outcome=None):
        self.outcome = outcome if outcome is not None else [OBS]
        self.calls = []

    def extract(self, request):
        self.calls.append(request)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


@pytest.fixture
def stub():
    return StubService()


@pytest.fixture
def client(stub):
    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[routes.get_extraction_service] = lambda: stub
    return TestClient(app)


def _payload(**overrides):
    body = {
        "transcript": "Elle a mal dormi cette nuit.",
        "subject_id": "subject-demo-1",
        "reported_by": "caregiver-demo-1",
    }
    body.update(overrides)
    return body


def test_success_shape(client, stub):
    response = client.post("/api/reports/extract", json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert len(body["observations"]) == 1
    assert body["observations"][0]["category"] == "sleep"
    assert body["observations"][0]["source"] == "caregiver_voice"
    assert set(body) == {"observations", "count"}


def test_request_fields_forwarded_to_service(client, stub):
    client.post("/api/reports/extract", json=_payload(reported_at="2026-10-10T20:05:00+00:00"))
    [request] = stub.calls
    assert request.subject_id == "subject-demo-1"
    assert request.reported_by == "caregiver-demo-1"
    assert request.reported_at == REPORTED_AT


def test_reported_at_defaults_to_now(client, stub):
    client.post("/api/reports/extract", json=_payload())
    assert stub.calls[0].reported_at.tzinfo is not None


def test_empty_observations_shape(client, stub):
    stub.outcome = []
    response = client.post("/api/reports/extract", json=_payload())
    assert response.status_code == 200
    assert response.json() == {"observations": [], "count": 0}


@pytest.mark.parametrize("transcript", ["", "   ", "\n\t "])
def test_empty_transcript_422_french(client, stub, transcript):
    response = client.post("/api/reports/extract", json=_payload(transcript=transcript))
    assert response.status_code == 422
    assert response.json()["detail"] == "Le texte de la transcription est vide."
    assert stub.calls == []


def test_service_error_502_french(client, stub):
    stub.outcome = ExtractionError("boom", aws_code="AccessDeniedException")
    response = client.post("/api/reports/extract", json=_payload())
    assert response.status_code == 502
    assert response.json()["detail"] == "L'extraction des faits a échoué. Veuillez réessayer."


def test_unknown_field_rejected(client):
    response = client.post("/api/reports/extract", json=_payload(unexpected="x"))
    assert response.status_code == 422


def test_missing_subject_422(client):
    body = _payload()
    del body["subject_id"]
    assert client.post("/api/reports/extract", json=body).status_code == 422


def test_extract_route_is_under_api():
    paths = set(create_app(Settings(_env_file=None)).openapi()["paths"])
    assert "/api/reports/extract" in paths


def test_only_health_outside_api_prefix_still_holds():
    app = create_app(Settings(_env_file=None))
    top_level = {getattr(route, "path", None) for route in app.routes} - {None}
    paths = (top_level | set(app.openapi()["paths"])) - {"/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}
    outside = {path for path in paths if path != "/api" and not path.startswith("/api/")}
    assert outside == {"/health"}


def test_default_dependency_builds_service(monkeypatch):
    seen = []
    monkeypatch.setattr(routes.aws, "client", lambda service, settings: seen.append((service, settings)) or object())
    settings = Settings(_env_file=None)
    svc = routes.get_extraction_service(settings)
    assert seen == [("bedrock-runtime", settings)]
    assert svc.settings is settings
