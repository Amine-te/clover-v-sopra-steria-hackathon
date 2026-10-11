"""Timeline API tests (Task 4) with the TimelineStore replaced through dependency overrides."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from clover_v_sopra_steria_hackathon.api import create_app
from clover_v_sopra_steria_hackathon.config import ConfigError, Settings
from clover_v_sopra_steria_hackathon.models import Observation
from clover_v_sopra_steria_hackathon.store import routes
from clover_v_sopra_steria_hackathon.store.service import StoreError

DOC_PATHS = {"/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}


def _obs(obs_id, when, *, category="sleep", severity="info"):
    return Observation(
        id=obs_id,
        timestamp=when,
        reported_at=datetime(2026, 10, 10, 20, 5, tzinfo=timezone.utc),
        subject_id="subject-demo-1",
        category=category,
        value="valeur factuelle",
        severity=severity,
        source="caregiver_voice",
        reported_by="caregiver-demo-1",
        confidence=0.8,
        transcript_span="span",
    )


class StubStore:
    """In-memory stand-in for TimelineStore: records saves, answers queries from a canned list."""

    def __init__(self, timeline=None, error=None):
        self.saved = []
        self.timeline = timeline or []
        self.error = error
        self.queries = []

    def save_many(self, observations):
        if self.error is not None:
            raise self.error
        obs = list(observations)
        self.saved.extend(obs)
        return [f"observations/subject-demo-1/key-{o.id}.json" for o in obs]

    def query(self, subject_id, period=None, category=None, severity=None):
        if self.error is not None:
            raise self.error
        self.queries.append((subject_id, period, category, severity))
        results = [
            o
            for o in self.timeline
            if (category is None or o.category == category)
            and (severity is None or o.severity == severity)
        ]
        return sorted(results, key=lambda o: o.timestamp)


@pytest.fixture
def stub():
    return StubStore()


@pytest.fixture
def client(stub):
    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[routes.get_store] = lambda: stub
    return TestClient(app)


def _obs_payload(obs_id="obs-1"):
    return {
        "id": obs_id,
        "timestamp": "2026-10-10T08:30:00+00:00",
        "reported_at": "2026-10-10T20:05:00+00:00",
        "subject_id": "subject-demo-1",
        "category": "sleep",
        "value": "a bien dormi",
        "severity": "info",
        "source": "caregiver_voice",
        "reported_by": "caregiver-demo-1",
        "confidence": 0.9,
        "transcript_span": "a bien dormi",
    }


def test_post_observations_returns_saved_and_keys(client, stub):
    response = client.post("/api/observations", json=[_obs_payload("obs-1"), _obs_payload("obs-2")])
    assert response.status_code == 200
    body = response.json()
    assert body["saved"] == 2
    assert len(body["keys"]) == 2
    assert len(stub.saved) == 2


def test_post_observations_validates_each(client):
    bad = _obs_payload()
    bad["severity"] = "catastrophic"
    assert client.post("/api/observations", json=[bad]).status_code == 422


def test_post_observations_store_error_502(client, stub):
    stub.error = StoreError("boom", aws_code="AccessDenied")
    response = client.post("/api/observations", json=[_obs_payload()])
    assert response.status_code == 502
    assert response.json()["detail"] == "L'accès à la chronologie a échoué. Veuillez réessayer."


def test_post_observations_config_error_500(client, stub):
    stub.error = ConfigError("GAMEDAY_BUCKET not set")
    response = client.post("/api/observations", json=[_obs_payload()])
    assert response.status_code == 500
    assert response.json()["detail"] == "Configuration incomplète : GAMEDAY_BUCKET n'est pas défini."


def test_get_timeline_ordered(stub):
    stub.timeline = [
        _obs("obs-late", datetime(2026, 10, 12, 8, 0, tzinfo=timezone.utc)),
        _obs("obs-early", datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)),
    ]
    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[routes.get_store] = lambda: stub
    client = TestClient(app)
    response = client.get("/api/timeline", params={"subject_id": "subject-demo-1"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert [o["id"] for o in body["observations"]] == ["obs-early", "obs-late"]


def test_get_timeline_forwards_filters(client, stub):
    client.get(
        "/api/timeline",
        params={
            "subject_id": "subject-demo-1",
            "start": "2026-10-10T00:00:00+00:00",
            "end": "2026-10-12T00:00:00+00:00",
            "category": "medication",
            "severity": "watch",
        },
    )
    subject, period, category, severity = stub.queries[0]
    assert subject == "subject-demo-1"
    assert period is not None
    assert period.start == datetime(2026, 10, 10, tzinfo=timezone.utc)
    assert period.end == datetime(2026, 10, 12, tzinfo=timezone.utc)
    assert category == "medication"
    assert severity == "watch"


def test_get_timeline_no_period_when_bounds_absent(client, stub):
    client.get("/api/timeline", params={"subject_id": "subject-demo-1"})
    _, period, _, _ = stub.queries[0]
    assert period is None


def test_get_timeline_missing_subject_422(client):
    assert client.get("/api/timeline").status_code == 422


def test_get_timeline_bad_enum_422(client):
    response = client.get(
        "/api/timeline", params={"subject_id": "subject-demo-1", "category": "not-a-category"}
    )
    assert response.status_code == 422


def test_get_timeline_bad_datetime_422(client):
    response = client.get(
        "/api/timeline", params={"subject_id": "subject-demo-1", "start": "not-a-date"}
    )
    assert response.status_code == 422


def test_get_timeline_store_error_502(client, stub):
    stub.error = StoreError("boom", aws_code="InternalError")
    response = client.get("/api/timeline", params={"subject_id": "subject-demo-1"})
    assert response.status_code == 502
    assert response.json()["detail"] == "L'accès à la chronologie a échoué. Veuillez réessayer."


def test_store_routes_under_api():
    paths = set(create_app(Settings(_env_file=None)).openapi()["paths"])
    assert "/api/observations" in paths
    assert "/api/timeline" in paths


def test_only_health_outside_api_prefix_still_holds():
    app = create_app(Settings(_env_file=None))
    top_level = {getattr(route, "path", None) for route in app.routes} - {None}
    paths = (top_level | set(app.openapi()["paths"])) - DOC_PATHS
    outside = {path for path in paths if path != "/api" and not path.startswith("/api/")}
    assert outside == {"/health"}


def test_default_dependency_builds_store(monkeypatch):
    seen = []
    monkeypatch.setattr(
        routes.aws, "client", lambda service, settings: seen.append((service, settings)) or object()
    )
    settings = Settings(_env_file=None)
    store = routes.get_store(settings)
    assert seen == [("s3", settings)]
    assert store.settings is settings
