"""M5 multimodal context tests."""

from datetime import datetime

from fastapi.testclient import TestClient

from clover_v_sopra_steria_hackathon.main import create_app
from clover_v_sopra_steria_hackathon.providers.ser.mock import MockSpeechEmotionProvider
from clover_v_sopra_steria_hackathon.providers.wearables.mock import MockWearableProvider


DEMO_TEXT = (
    "Maman était plus fatiguée aujourd’hui. Elle a pris son traitement mais elle "
    "n’a presque rien mangé. Sophie passe ce soir. Moi je suis vraiment crevé."
)


def _entry():
    app = create_app()
    client = TestClient(app)
    recipient_id = client.get("/api/care-recipients").json()[0]["id"]
    entry = client.post(
        "/api/journal",
        json={
            "care_recipient_id": recipient_id,
            "input_type": "text",
            "original_text": DEMO_TEXT,
        },
    ).json()
    client.post(f"/api/journal/{entry['id']}/analyze")
    return client, entry["id"], app


def test_mock_ser_is_deterministic_and_private():
    result = MockSpeechEmotionProvider().analyze(audio_object_key="demo")
    assert result is not None
    assert result.model_dump() == {
        "valence": "negative",
        "arousal": "high",
        "top_label": "tension_like",
        "confidence": 0.61,
        "quality": "good",
        "model_version": "demo-ser-v1",
        "visibility": "private",
        "provider": "mock-ser",
    }


def test_mock_wearables_keep_subject_specific_values():
    provider = MockWearableProvider()
    caregiver = provider.summarize(
        subject_type="caregiver", subject_id="thomas", around=datetime.now()
    )
    recipient = provider.summarize(
        subject_type="care_recipient", subject_id="marie", around=datetime.now()
    )
    assert caregiver is not None and caregiver.metrics["heart_rate_avg_bpm"] == 91
    assert recipient is not None and recipient.metrics["heart_rate_avg_bpm"] == 74
    assert recipient.metrics["steps_total"] == 1320


def test_enrichment_contains_all_sources_and_privacy():
    client, entry_id, _ = _entry()
    response = client.post(f"/api/journal/{entry_id}/multimodal/enrich")
    assert response.status_code == 200
    body = response.json()
    assert body["modalities_present"] == [
        "text",
        "ser_caregiver",
        "wearable_caregiver",
        "wearable_care_recipient",
    ]
    assert body["caregiver_vocal_affect"]["visibility"] == "private"
    assert body["caregiver_wearable"]["visibility"] == "private"
    assert body["care_recipient_wearable"]["subject_type"] == "care_recipient"
    assert body["care_recipient_wearable"]["visibility"] == "circle"
    assert "stress" not in str(body).lower()
    assert "diagnos" not in str(body).lower()


def test_repeated_enrichment_is_idempotent():
    client, entry_id, _ = _entry()
    first = client.post(f"/api/journal/{entry_id}/multimodal/enrich").json()
    second = client.post(f"/api/journal/{entry_id}/multimodal/enrich").json()
    assert first["modalities_present"] == second["modalities_present"]
    assert first["caregiver_vocal_affect"]["confidence"] == 0.61


def test_provider_none_is_gracefully_omitted():
    client, entry_id, app = _entry()

    class EmptySER:
        def analyze(self, *, audio_object_key: str):
            return None

    app.dependency_overrides[
        __import__(
            "clover_v_sopra_steria_hackathon.api.deps",
            fromlist=["get_ser_provider"],
        ).get_ser_provider
    ] = lambda: EmptySER()
    try:
        body = client.post(f"/api/journal/{entry_id}/multimodal/enrich").json()
        assert "ser_caregiver" not in body["modalities_present"]
        assert body["caregiver_vocal_affect"] is None
    finally:
        app.dependency_overrides.clear()


def test_get_reads_persisted_context_without_rerunning_provider():
    client, entry_id, app = _entry()
    client.post(f"/api/journal/{entry_id}/multimodal/enrich")

    class ExplodingSER:
        def analyze(self, *, audio_object_key: str):
            raise AssertionError("GET must not run providers")

    from clover_v_sopra_steria_hackathon.api.deps import get_ser_provider

    app.dependency_overrides[get_ser_provider] = lambda: ExplodingSER()
    try:
        response = client.get(f"/api/journal/{entry_id}/multimodal-context")
        assert response.status_code == 200
        assert "ser_caregiver" in response.json()["modalities_present"]
    finally:
        app.dependency_overrides.clear()
