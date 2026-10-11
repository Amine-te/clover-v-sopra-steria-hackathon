"""M8 voice upload and transcription tests."""

from fastapi.testclient import TestClient

from clover_v_sopra_steria_hackathon.api.deps import get_transcription_provider
from clover_v_sopra_steria_hackathon.main import create_app
from clover_v_sopra_steria_hackathon.providers.storage.mock import MockObjectStorageProvider
from clover_v_sopra_steria_hackathon.providers.transcription.mock import MockTranscriptionProvider


def _voice_entry():
    app = create_app()
    client = TestClient(app)
    recipient = client.get("/api/care-recipients").json()[0]
    entry = client.post("/api/journal", json={
        "care_recipient_id": recipient["id"],
        "input_type": "voice",
        "original_text": "Note vocale",
    }).json()
    return app, client, entry


def test_mock_storage_is_deterministic_and_round_trips():
    storage = MockObjectStorageProvider(root=".data/test-audio")
    key = storage.put_audio(data=b"demo", content_type="audio/mpeg")
    assert key == storage.put_audio(data=b"demo", content_type="audio/mpeg")
    assert storage.get_bytes(object_key=key) == b"demo"


def test_mock_transcription_returns_demo_sentence():
    result = MockTranscriptionProvider().transcribe(audio_object_key="mock-audio/demo")
    assert "Maman était plus fatiguée aujourd’hui" in result.text
    assert result.provider == "mock-transcribe"


def test_upload_and_transcribe_persist_voice_state():
    _, client, entry = _voice_entry()
    uploaded = client.post(
        f"/api/journal/{entry['id']}/audio",
        files={"audio": ("note.mp3", b"audio bytes", "audio/mpeg")},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["audio_object_key"].startswith("mock-audio/")
    transcript = client.post(f"/api/journal/{entry['id']}/transcribe")
    assert transcript.status_code == 200
    assert transcript.json()["transcription_status"] == "completed"
    current = client.get(f"/api/journal/{entry['id']}").json()
    assert current["transcript"].startswith("Maman était plus fatiguée")
    assert current["input_type"] == "voice"


def test_unsupported_audio_and_missing_audio_are_rejected():
    _, client, entry = _voice_entry()
    unsupported = client.post(
        f"/api/journal/{entry['id']}/audio",
        files={"audio": ("note.txt", b"not audio", "text/plain")},
    )
    assert unsupported.status_code == 415
    assert client.post(f"/api/journal/{entry['id']}/transcribe").status_code == 409


def test_transcription_failure_preserves_audio_key():
    app, client, entry = _voice_entry()
    uploaded = client.post(
        f"/api/journal/{entry['id']}/audio",
        files={"audio": ("note.webm", b"audio bytes", "audio/webm")},
    ).json()

    class FailingTranscription:
        def transcribe(self, *, audio_object_key: str, language: str = "fr-FR"):
            raise RuntimeError("provider failed")

    app.dependency_overrides[get_transcription_provider] = lambda: FailingTranscription()
    response = client.post(f"/api/journal/{entry['id']}/transcribe")
    assert response.status_code == 502
    current = client.get(f"/api/journal/{entry['id']}").json()
    assert current["audio_object_key"] == uploaded["audio_object_key"]
    assert current["transcript"] is None


def test_demo_audio_endpoint_works():
    _, client, entry = _voice_entry()
    response = client.post(f"/api/journal/{entry['id']}/audio/demo")
    assert response.status_code == 200
    assert response.json()["audio_mime_type"] == "audio/mpeg"
