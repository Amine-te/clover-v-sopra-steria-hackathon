"""M1 — FastAPI app boots and serves /api/health without AWS or DB."""

from fastapi.testclient import TestClient

from clover_v_sopra_steria_hackathon.main import create_app


def test_app_starts_and_health_returns_200():
    with TestClient(create_app()) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "karis-api"}
