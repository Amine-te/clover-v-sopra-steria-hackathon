"""Focused demo safety, metadata, smoke, and degradation regressions (no AWS)."""

import importlib.util
import io
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from clover_v_sopra_steria_hackathon.api.deps import get_messaging_provider, get_ser_provider, get_transcription_provider, get_wearable_provider
from clover_v_sopra_steria_hackathon.api.routes import demo
from clover_v_sopra_steria_hackathon.core.config import Settings
from clover_v_sopra_steria_hackathon.db.session import SessionLocal
from clover_v_sopra_steria_hackathon.main import create_app
from clover_v_sopra_steria_hackathon.models import CareRecipient, GeneratedMessage, InputType, JournalEntry, SubjectType, User, WearableWindow
from clover_v_sopra_steria_hackathon.services.demo_service import MARIE_ID, THOMAS_ID, reset_demo

DEMO_TEXT = "Maman était plus fatiguée aujourd’hui. Elle a pris son traitement mais elle n’a presque rien mangé. Sophie passe ce soir. Moi je suis vraiment crevé."


@pytest.fixture
def demo_client():
    with SessionLocal() as db, db.begin():
        reset_demo(db)
    app = create_app()
    with TestClient(app) as client:
        yield app, client


def create_entry(client, voice=False):
    response = client.post("/api/journal", json={"care_recipient_id": str(MARIE_ID), "original_text": DEMO_TEXT, "input_type": "voice" if voice else "text"})
    assert response.status_code == 201
    return response.json()["id"]


def test_reset_is_scoped_repeatable_and_restores_seven_days(demo_client):
    _, client = demo_client
    other_id, user_id, entry_id = uuid4(), uuid4(), uuid4()
    try:
        with SessionLocal() as db, db.begin():
            db.add(User(id=user_id, full_name="Autre famille", email=f"{user_id}@example.test"))
            db.add(CareRecipient(id=other_id, first_name="Autre", last_name="Famille"))
            db.flush()
            # Even another family's note authored by Thomas must survive.
            db.add(JournalEntry(id=entry_id, recipient_id=other_id, author_id=THOMAS_ID, input_type=InputType.TEXT, original_text="Note à préserver"))
            db.flush()
        created = create_entry(client)
        for _ in range(2):
            response = client.post("/api/demo/reset", json={"confirmed": True})
            assert response.status_code == 200
            assert response.json()["counts"]["journal_entries"] == 7
        with SessionLocal() as db:
            assert db.get(User, user_id).full_name == "Autre famille"
            assert db.get(CareRecipient, other_id).first_name == "Autre"
            assert db.get(JournalEntry, entry_id).original_text == "Note à préserver"
            assert db.scalar(select(func.count()).select_from(JournalEntry).where(JournalEntry.recipient_id == MARIE_ID)) == 7
        assert client.get(f"/api/journal/{created}").status_code == 404
    finally:
        with SessionLocal() as db, db.begin():
            db.execute(delete(JournalEntry).where(JournalEntry.id == entry_id))
            db.execute(delete(CareRecipient).where(CareRecipient.id == other_id))
            db.execute(delete(User).where(User.id == user_id))


def test_reset_requires_confirmation_and_is_disabled_in_production(demo_client, monkeypatch):
    _, client = demo_client
    assert client.post("/api/demo/reset", json={}).status_code == 409
    for settings in (Settings(app_env="production", _env_file=None), Settings(demo_reset_enabled=False, _env_file=None)):
        monkeypatch.setattr(demo, "get_settings", lambda: settings)
        assert client.post("/api/demo/reset", json={"confirmed": True}).status_code == 404
        assert client.get("/api/demo/status").status_code == 404


def test_reset_failure_rolls_back_deletion(demo_client, monkeypatch):
    import clover_v_sopra_steria_hackathon.services.demo_service as service
    _, client = demo_client
    def broken_seed(db):
        raise RuntimeError("seed interrupted")
    monkeypatch.setattr(service, "seed", broken_seed)
    with pytest.raises(RuntimeError, match="seed interrupted"):
        client.post("/api/demo/reset", json={"confirmed": True})
    assert client.get("/api/demo/status").json()["seed_entry_count"] == 7


def test_safe_technical_privacy_counts_and_read_drafts_preserve_edits(demo_client):
    _, client = demo_client
    id = create_entry(client)
    client.post(f"/api/journal/{id}/multimodal/enrich")
    client.post(f"/api/journal/{id}/analyze")
    drafts = client.post(f"/api/journal/{id}/messages/generate").json()["drafts"]
    sophie = next(item for item in drafts if item["recipient_name"] == "Sophie")
    assert sophie["privacy_pipeline"] == {"structured_count": 8, "shareable_count": 4, "authorized_count": 3, "transmitted_count": 3, "private_transmitted_count": 0}
    assert sophie["excluded_private_count"] == 3
    assert set(sophie["provider_metadata"]) == {"provider_used", "model_id", "latency_ms", "validation_retry_count", "fallback_used"}
    client.patch(f"/api/messages/{sophie['id']}", json={"edited_text": "Message relu par Thomas", "approved": True})
    saved = client.get(f"/api/journal/{id}/messages").json()["drafts"]
    current = next(item for item in saved if item["id"] == sophie["id"])
    assert current["text"] == "Message relu par Thomas"
    assert current["approved"] is True
    assert current["privacy_pipeline"]["private_transmitted_count"] == 0
    status = client.get("/api/demo/status").json()
    assert set(status) == {"database", "reset_enabled", "period_start", "period_end", "seed_entry_count", "providers"}
    assert not any(word in str(status) for word in ("secret", "bucket", "password", "credential"))


@pytest.mark.parametrize("failed", ["ser", "wearable", "both"])
def test_optional_multimodal_failure_does_not_block_journal(demo_client, failed, caplog):
    app, client = demo_client
    class Unavailable:
        def analyze(self, **kwargs):
            raise RuntimeError("PRIVATE do not log this")
        def summarize(self, **kwargs):
            raise RuntimeError("PRIVATE do not log this")
    if failed in {"ser", "both"}:
        app.dependency_overrides[get_ser_provider] = lambda: Unavailable()
    if failed in {"wearable", "both"}:
        app.dependency_overrides[get_wearable_provider] = lambda: Unavailable()
    id = create_entry(client)
    result = client.post(f"/api/journal/{id}/multimodal/enrich")
    assert result.status_code == 200
    assert bool(result.json()["caregiver_vocal_affect"]) == (failed == "wearable")
    assert bool(result.json()["caregiver_wearable"]) == (failed == "ser")
    assert client.post(f"/api/journal/{id}/analyze").status_code == 200
    assert client.get(f"/api/journal/{id}").json()["original_text"] == DEMO_TEXT
    assert "PRIVATE do not log this" not in caplog.text


def test_transcription_failure_allows_explicit_demo_text_on_same_entry(demo_client):
    app, client = demo_client
    class Unavailable:
        def transcribe(self, **kwargs):
            raise TimeoutError("unsafe vendor details")
    app.dependency_overrides[get_transcription_provider] = lambda: Unavailable()
    id = create_entry(client, voice=True)
    client.post(f"/api/journal/{id}/audio/demo")
    assert client.post(f"/api/journal/{id}/transcribe").status_code == 502
    assert client.patch(f"/api/journal/{id}", json={"transcript": DEMO_TEXT}).status_code == 200
    assert client.post(f"/api/journal/{id}/analyze").status_code == 200
    current = client.get(f"/api/journal/{id}").json()
    assert current["original_text"] == DEMO_TEXT and current["transcript"] == DEMO_TEXT
    assert current["transcription_status"] == "failed"  # no pretend live success


def test_message_delivery_failure_keeps_approved_draft(demo_client, caplog):
    app, client = demo_client
    class Unavailable:
        def send(self, **kwargs):
            raise RuntimeError("unsafe recipient content")
    id = create_entry(client)
    client.post(f"/api/journal/{id}/analyze")
    sophie = next(item for item in client.post(f"/api/journal/{id}/messages/generate").json()["drafts"] if item["recipient_name"] == "Sophie")
    client.patch(f"/api/messages/{sophie['id']}", json={"approved": True})
    app.dependency_overrides[get_messaging_provider] = lambda: Unavailable()
    failed = client.post(f"/api/journal/{id}/messages/send")
    assert failed.status_code == 502 and "disponibles" in failed.json()["detail"]
    current = next(item for item in client.get(f"/api/journal/{id}/messages").json()["drafts"] if item["id"] == sophie["id"])
    assert current["approved"] and current["delivery_status"] == "approved"
    assert current["text"] == sophie["text"]
    assert "unsafe recipient content" not in caplog.text


def load_smoke():
    path = Path(__file__).resolve().parents[1] / "scripts" / "demo_smoke.py"
    spec = importlib.util.spec_from_file_location("demo_smoke", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_smoke_exercises_real_local_api_and_removes_temporary_entry(demo_client):
    _, client = demo_client
    output = io.StringIO()
    assert load_smoke().run_checks(client, output)
    assert "DEMO READY" in output.getvalue() and "[FAIL]" not in output.getvalue()
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(JournalEntry).where(JournalEntry.recipient_id == MARIE_ID)) == 7
        assert db.scalar(select(func.count()).select_from(GeneratedMessage)) == 0


def test_smoke_unreachable_backend_fails_without_exposing_error_content():
    class Offline:
        def request(self, *args, **kwargs):
            raise ConnectionError("secret raw error")
    output = io.StringIO()
    assert not load_smoke().run_checks(Offline(), output)
    assert "[FAIL] Backend (ConnectionError)" in output.getvalue()
    assert "DEMO NOT READY" in output.getvalue()
    assert "secret raw error" not in output.getvalue()
