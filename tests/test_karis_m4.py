"""M4 clarification workflow tests."""

from fastapi.testclient import TestClient

from clover_v_sopra_steria_hackathon.main import create_app

DEMO_TEXT = (
    "Maman était plus fatiguée aujourd’hui. Elle a pris son traitement mais elle "
    "n’a presque rien mangé. Sophie passe ce soir. Moi je suis vraiment crevé."
)


def _entry(text=DEMO_TEXT):
    client = TestClient(create_app())
    recipient_id = client.get("/api/care-recipients").json()[0]["id"]
    entry = client.post("/api/journal", json={
        "care_recipient_id": recipient_id, "input_type": "text", "original_text": text,
    }).json()
    return client, entry["id"], recipient_id


def test_demo_analysis_creates_exactly_two_questions():
    client, entry_id, _ = _entry()
    body = client.post(f"/api/journal/{entry_id}/analyze").json()
    assert body["clarification_needed"] is True
    assert len(body["clarifications"]) == 2
    assert body["clarifications"][0]["reason"] == "Préciser si la fatigue est inhabituelle."


def test_clarifications_are_capped_at_three():
    client, entry_id, _ = _entry()
    body = client.post(f"/api/journal/{entry_id}/analyze").json()
    assert len(body["clarifications"]) <= 3


def test_answers_reanalyze_without_duplicate_children():
    client, entry_id, _ = _entry()
    analyzed = client.post(f"/api/journal/{entry_id}/analyze").json()
    answers = [
        {"clarification_id": item["id"], "answer": "Oui"}
        for item in analyzed["clarifications"]
    ]
    updated = client.post(f"/api/journal/{entry_id}/clarifications", json={"answers": answers})
    assert updated.status_code == 200
    body = updated.json()
    assert all(item["answer"] == "Oui" for item in body["clarifications"])
    assert body["clarification_needed"] is False
    assert len(body["observations"]) == 3
    assert len(body["actions"]) == 1
    again = client.post(f"/api/journal/{entry_id}/clarifications", json={"answers": answers})
    assert again.status_code == 200
    assert len(again.json()["observations"]) == 3
    assert len(again.json()["actions"]) == 1


def test_yes_fatigue_answer_becomes_clarified_and_sophie_is_assignee():
    client, entry_id, recipient_id = _entry()
    analyzed = client.post(f"/api/journal/{entry_id}/analyze").json()
    answers = [{"clarification_id": item["id"], "answer": "Oui"} for item in analyzed["clarifications"]]
    body = client.post(f"/api/journal/{entry_id}/clarifications", json={"answers": answers}).json()
    assert body["observations"][0]["description"] == "Marie était plus fatiguée que d’habitude aujourd’hui"
    assert body["actions"][0]["description"] == "Sophie vérifie l’alimentation lors de sa visite ce soir"
    assert body["actions"][0]["assigned_member_id"] is not None
    members = client.get(f"/api/care-recipients/{recipient_id}/members").json()
    sophie = next(member for member in members if member["name"].startswith("Sophie"))
    assert body["actions"][0]["assigned_member_id"] == sophie["user_id"]
    assert body["caregiver_feelings"][0]["visibility"] == "private"


def test_sufficient_entry_skips_clarification():
    client, entry_id, _ = _entry("Marie a bien dormi et a pris son traitement.")
    body = client.post(f"/api/journal/{entry_id}/analyze").json()
    assert body["clarification_needed"] is False
    assert body["clarifications"] == []


def test_vague_entry_asks_for_observed_facts_without_inventing_symptoms():
    client, entry_id, _ = _entry("Maman n’était vraiment pas bien aujourd’hui.")
    body = client.post(f"/api/journal/{entry_id}/analyze").json()
    assert body["clarification_needed"] is True
    assert body["clarifications"][0]["question"] == "Qu’avez-vous remarqué exactement ?"
    assert body["observations"] == []
