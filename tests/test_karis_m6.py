"""M6 privacy filtering, deterministic routing, and approved mock delivery."""

from fastapi.testclient import TestClient

from clover_v_sopra_steria_hackathon.api.deps import get_llm_provider
from clover_v_sopra_steria_hackathon.main import create_app
from clover_v_sopra_steria_hackathon.providers.llm.mock import MockLLMProvider


DEMO_TEXT = (
    "Maman était plus fatiguée aujourd’hui. Elle a pris son traitement mais elle "
    "n’a presque rien mangé. Sophie passe ce soir. Moi je suis vraiment crevé."
)


def _entry(text: str = DEMO_TEXT):
    app = create_app()
    client = TestClient(app)
    recipient = client.get("/api/care-recipients").json()[0]
    entry = client.post(
        "/api/journal",
        json={
            "care_recipient_id": recipient["id"],
            "input_type": "text",
            "original_text": text,
        },
    ).json()
    client.post(f"/api/journal/{entry['id']}/analyze")
    return app, client, entry["id"]


def test_sophie_context_excludes_private_data_and_original_text():
    app, client, entry_id = _entry()
    captured = {}

    class SpyLLM(MockLLMProvider):
        def generate_recipient_message(self, *, recipient_name, context):
            captured[recipient_name] = context
            return super().generate_recipient_message(
                recipient_name=recipient_name, context=context
            )

    app.dependency_overrides[get_llm_provider] = lambda: SpyLLM()
    response = client.post(f"/api/journal/{entry_id}/messages/generate")
    assert response.status_code == 200
    sophie = captured["Sophie"]
    assert "caregiver_vocal_affect" not in sophie
    assert "caregiver_wearable" not in sophie
    assert "Thomas se dit vraiment fatigué" not in sophie["relevant_context"]
    assert DEMO_TEXT not in sophie["relevant_context"]
    assert any("fatiguée" in item["description"] for item in sophie["allowed_observations"])
    assert any("mangé" in item["description"] for item in sophie["allowed_observations"])


def test_marc_receives_logistics_but_not_nutrition():
    _, client, entry_id = _entry(
        "Le kiné a annulé. Marc doit reprendre rendez-vous."
    )
    response = client.post(f"/api/journal/{entry_id}/messages/generate")
    assert response.status_code == 200
    drafts = response.json()["drafts"]
    marc = next(item for item in drafts if item["recipient_name"] == "Marc")
    assert marc["allowed_item_count"] == 2
    assert "mangé" not in marc["text"]
    assert "rendez-vous" in marc["text"]


def test_generation_is_idempotent_and_unapproved_message_is_not_sent():
    _, client, entry_id = _entry()
    first = client.post(f"/api/journal/{entry_id}/messages/generate").json()
    second = client.post(f"/api/journal/{entry_id}/messages/generate").json()
    assert [item["id"] for item in first["drafts"]] == [item["id"] for item in second["drafts"]]
    assert all(item["delivery_status"] == "draft" for item in second["drafts"])
    sent = client.post(f"/api/journal/{entry_id}/messages/send").json()
    assert all(item["delivery_status"] != "sent" for item in sent["drafts"])


def test_approved_message_can_be_mock_sent_without_private_inbox_metadata():
    _, client, entry_id = _entry()
    generated = client.post(f"/api/journal/{entry_id}/messages/generate").json()
    message_id = next(
        item["id"] for item in generated["drafts"] if item["recipient_name"] == "Sophie"
    )
    approved = client.patch(
        f"/api/messages/{message_id}",
        json={"approved": True},
    )
    assert approved.status_code == 200
    assert approved.json()["delivery_status"] == "approved"
    sent = client.post(f"/api/journal/{entry_id}/messages/send").json()
    sophie = next(item for item in sent["drafts"] if item["id"] == message_id)
    assert sophie["delivery_status"] == "sent"
    inbox = client.get("/api/messages/mock-inbox").json()["messages"]
    inbox_item = next(item for item in inbox if item["id"] == message_id)
    assert "Thomas se dit vraiment fatigué" not in str(inbox_item)
    assert "tension_like" not in str(inbox_item)
