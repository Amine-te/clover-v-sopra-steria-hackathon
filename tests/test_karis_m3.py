"""M3 text journal vertical-slice API tests."""

from fastapi.testclient import TestClient

from clover_v_sopra_steria_hackathon.main import create_app

DEMO_TEXT = (
    "Maman était plus fatiguée aujourd’hui. Elle a pris son traitement mais elle "
    "n’a presque rien mangé. Sophie passe ce soir. Moi je suis vraiment crevé."
)


def _client_and_recipient():
    client = TestClient(create_app())
    recipient = client.get("/api/care-recipients").json()[0]
    return client, recipient["id"]


def _create_entry(client: TestClient, recipient_id: str, text: str = DEMO_TEXT):
    response = client.post(
        "/api/journal",
        json={
            "care_recipient_id": recipient_id,
            "input_type": "text",
            "original_text": text,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_demo_auth_returns_thomas():
    with TestClient(create_app()) as client:
        response = client.post("/api/auth/demo")
    assert response.status_code == 200
    assert response.json()["full_name"] == "Thomas Durand"


def test_create_and_analyze_demo_sentence():
    client, recipient_id = _client_and_recipient()
    entry = _create_entry(client, recipient_id)
    analyzed = client.post(f"/api/journal/{entry['id']}/analyze")
    assert analyzed.status_code == 200
    body = analyzed.json()
    assert body["status"] == "analyzed"
    assert [item["category"] for item in body["observations"]] == [
        "fatigue",
        "nutrition",
        "medication",
    ]


def test_caregiver_feeling_is_persisted_private():
    client, recipient_id = _client_and_recipient()
    entry = _create_entry(client, recipient_id)
    body = client.post(f"/api/journal/{entry['id']}/analyze").json()
    assert body["caregiver_feelings"][0]["visibility"] == "private"


def test_analyze_is_idempotent():
    client, recipient_id = _client_and_recipient()
    entry = _create_entry(client, recipient_id)
    first = client.post(f"/api/journal/{entry['id']}/analyze").json()
    second = client.post(f"/api/journal/{entry['id']}/analyze").json()
    assert len(first["observations"]) == len(second["observations"]) == 3
    assert len(first["caregiver_feelings"]) == len(second["caregiver_feelings"]) == 1
    assert len(first["actions"]) == len(second["actions"]) == 1


def test_finalize_requires_analyzed_status():
    client, recipient_id = _client_and_recipient()
    entry = _create_entry(client, recipient_id)
    response = client.post(f"/api/journal/{entry['id']}/finalize")
    assert response.status_code == 409
    client.post(f"/api/journal/{entry['id']}/analyze")
    assert client.post(f"/api/journal/{entry['id']}/finalize").json()["status"] == "finalized"


def test_finalized_entry_appears_without_private_feeling_text():
    client, recipient_id = _client_and_recipient()
    entry = _create_entry(client, recipient_id)
    client.post(f"/api/journal/{entry['id']}/analyze")
    client.post(f"/api/journal/{entry['id']}/finalize")
    timeline = client.get(f"/api/care-recipients/{recipient_id}/timeline")
    assert timeline.status_code == 200
    item = next(item for item in timeline.json()["items"] if item["id"] == entry["id"])
    assert item["has_private_data"] is True
    assert "Thomas se dit vraiment fatigué" not in item


def test_non_finalized_entry_is_not_in_timeline():
    client, recipient_id = _client_and_recipient()
    entry = _create_entry(client, recipient_id)
    client.post(f"/api/journal/{entry['id']}/analyze")
    timeline = client.get(f"/api/care-recipients/{recipient_id}/timeline").json()
    assert all(item["id"] != entry["id"] for item in timeline["items"])
