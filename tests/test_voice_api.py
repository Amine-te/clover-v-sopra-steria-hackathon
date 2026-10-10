"""Voice report API tests (Requirement 5) with the VoiceService replaced through dependency overrides."""
import io

import pytest
from fastapi.testclient import TestClient

from clover_v_sopra_steria_hackathon.api import create_app
from clover_v_sopra_steria_hackathon.audio import routes
from clover_v_sopra_steria_hackathon.audio.formats import MAX_AUDIO_BYTES
from clover_v_sopra_steria_hackathon.audio.service import (
    AudioNotFoundError,
    FixtureNotFoundError,
    TranscriptionError,
    TranscriptResult,
    UploadError,
    VoiceService,
)
from clover_v_sopra_steria_hackathon.config import ConfigError, Settings

RID = "rep-" + "c" * 32
KEY = f"audio/{RID}.mp3"
RETRY_DETAIL = "La transcription a échoué. Votre enregistrement est sauvegardé, vous pouvez réessayer."


class StubService:
    def __init__(self, outcome=None):
        self.outcome = outcome or TranscriptResult(RID, KEY, "Bonjour.", "transcribe")
        self.calls = []

    def _answer(self):
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome

    def submit(self, data, ext, content_type, fixture=None):
        self.calls.append(("submit", data, ext, content_type, fixture))
        return self._answer()

    def retry(self, report_id):
        self.calls.append(("retry", report_id))
        return self._answer()


@pytest.fixture
def stub():
    return StubService()


@pytest.fixture
def client(stub):
    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[routes.get_voice_service] = lambda: stub
    return TestClient(app)


def _post(client, name="note.mp3", data=b"audio", content_type="audio/mpeg", **form):
    return client.post("/api/reports/voice", files={"audio": (name, io.BytesIO(data), content_type)}, data=form)


def test_success_shape(client, stub):
    response = _post(client)
    assert response.status_code == 200
    assert response.json() == {"report_id": RID, "audio_s3_key": KEY, "transcript": "Bonjour.", "source": "transcribe"}
    assert stub.calls == [("submit", b"audio", "mp3", "audio/mpeg", None)]


def test_cache_source_and_fixture_field(client, stub):
    stub.outcome = TranscriptResult(RID, None, "Fixture.", "cache")
    response = _post(client, name="Note.M4A", fixture="chute")
    assert response.status_code == 200
    assert response.json()["source"] == "cache"
    assert response.json()["audio_s3_key"] is None
    assert stub.calls[0][2] == "m4a"
    assert stub.calls[0][4] == "chute"


@pytest.mark.parametrize("name", ["note.txt", "note", "audio.mp3.exe"])
def test_unsupported_extension_415(client, stub, name):
    response = _post(client, name=name)
    assert response.status_code == 415
    assert response.json()["detail"].startswith("Format audio non pris en charge")
    assert stub.calls == []


def test_extension_checked_before_emptiness(client):
    assert _post(client, name="empty.txt", data=b"").status_code == 415


def test_empty_file_400(client, stub):
    response = _post(client, data=b"")
    assert response.status_code == 400
    assert response.json()["detail"] == "Le fichier audio est vide."
    assert stub.calls == []


def test_too_large_413(client, stub):
    response = _post(client, data=b"\0" * (MAX_AUDIO_BYTES + 1))
    assert response.status_code == 413
    assert response.json()["detail"] == "Le fichier audio dépasse 25 Mo."
    assert stub.calls == []


def test_exactly_max_size_accepted(client):
    assert _post(client, data=b"\0" * MAX_AUDIO_BYTES).status_code == 200


def test_missing_audio_field_422(client):
    assert client.post("/api/reports/voice", data={"fixture": "x"}).status_code == 422


def test_unknown_fixture_404(client, stub):
    stub.outcome = FixtureNotFoundError("inconnu")
    response = _post(client, fixture="inconnu")
    assert response.status_code == 404
    assert response.json()["detail"] == "Transcription de démonstration introuvable."


def test_missing_bucket_500(client, stub):
    stub.outcome = ConfigError("GAMEDAY_BUCKET is not set")
    response = _post(client)
    assert response.status_code == 500
    assert "GAMEDAY_BUCKET" in response.json()["detail"]


def test_upload_failure_502_not_retryable(client, stub):
    stub.outcome = UploadError(RID, "AccessDenied")
    response = _post(client)
    assert response.status_code == 502
    body = response.json()
    assert body["report_id"] == RID
    assert body["audio_s3_key"] is None
    assert body["retryable"] is False
    assert set(body) == {"report_id", "audio_s3_key", "detail", "retryable"}


def test_transcription_failure_502_retryable(client, stub):
    stub.outcome = TranscriptionError(RID, KEY, "FAILED")
    response = _post(client)
    assert response.status_code == 502
    assert response.json() == {"report_id": RID, "audio_s3_key": KEY, "detail": RETRY_DETAIL, "retryable": True}


def test_retry_200(client, stub):
    response = client.post(f"/api/reports/{RID}/transcribe")
    assert response.status_code == 200
    assert response.json()["report_id"] == RID
    assert stub.calls == [("retry", RID)]


def test_retry_404(client, stub):
    stub.outcome = AudioNotFoundError(RID)
    response = client.post(f"/api/reports/{RID}/transcribe")
    assert response.status_code == 404
    assert response.json()["detail"] == "Aucun enregistrement trouvé pour ce rapport."


def test_retry_502_shape(client, stub):
    stub.outcome = TranscriptionError(RID, KEY, "timeout")
    response = client.post(f"/api/reports/{RID}/transcribe")
    assert response.status_code == 502
    assert response.json()["retryable"] is True
    assert response.json()["audio_s3_key"] == KEY


@pytest.mark.parametrize("bad", ["rep-123", "rep-" + "C" * 32, "rep-" + "g" * 32, "x" + "c" * 35])
def test_retry_bad_id_422(client, stub, bad):
    assert client.post(f"/api/reports/{bad}/transcribe").status_code == 422
    assert stub.calls == []


def test_default_dependency_builds_service_from_app_settings(monkeypatch):
    seen = []
    monkeypatch.setattr(routes.aws, "client", lambda service, settings: seen.append((service, settings)) or object())
    settings = Settings(_env_file=None, use_cached_transcripts=True)
    app = create_app(settings)
    response = TestClient(app).post(
        "/api/reports/voice", files={"audio": ("a.mp3", io.BytesIO(b"x"), "audio/mpeg")}
    )
    assert response.status_code == 200
    assert response.json()["source"] == "cache"
    assert [name for name, _ in seen] == ["s3", "transcribe"]
    assert all(s is settings for _, s in seen)
    assert isinstance(routes.get_voice_service(settings), VoiceService)


def test_voice_routes_are_under_api():
    paths = set(create_app(Settings(_env_file=None)).openapi()["paths"])
    assert {"/api/reports/voice", "/api/reports/{report_id}/transcribe"} <= paths
