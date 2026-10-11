"""M7 deterministic weekly aggregation and report workflow tests."""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from clover_v_sopra_steria_hackathon.main import create_app
from clover_v_sopra_steria_hackathon.providers.llm.mock import MockLLMProvider


def _period() -> tuple[str, str]:
    end = date.today() - timedelta(days=date.today().weekday() + 1)
    return str(end - timedelta(days=6)), str(end)


def _report():
    client = TestClient(create_app())
    recipient = client.get("/api/care-recipients").json()[0]
    start, end = _period()
    response = client.post(
        f"/api/care-recipients/{recipient['id']}/reports/weekly/generate",
        json={"period_start": start, "period_end": end},
    )
    assert response.status_code == 200
    return client, response.json()


def test_seeded_report_has_deterministic_counts_and_exclusions():
    _, report = _report()
    assert report["source_entry_count"] == 6
    assert report["excluded_private_count"] >= 9
    assert report["content"].count("trois reprises") == 1
    assert "Deux nuits perturbées" in report["content"]
    assert "Séance de kiné annulée" in report["content"]
    assert "malnutrition" not in report["content"].lower()
    assert "état se dégrade" not in report["content"].lower()


def test_mock_report_does_not_invent_medication_or_diagnosis():
    draft = MockLLMProvider().generate_weekly_report(
        context={
            "care_recipient_name": "Marie",
            "recurring_observations": {},
            "observations_by_category": {},
            "medication_reported": [],
            "completed_actions": [],
            "pending_actions": [],
        }
    )
    assert "malnutrition" not in draft.markdown.lower()
    assert "traitement" not in draft.markdown.lower()


def test_report_generation_is_idempotent_and_does_not_change_timeline():
    client, first = _report()
    recipient = client.get("/api/care-recipients").json()[0]
    before = client.get(f"/api/care-recipients/{recipient['id']}/timeline").json()
    start, end = _period()
    second = client.post(
        f"/api/care-recipients/{recipient['id']}/reports/weekly/generate",
        json={"period_start": start, "period_end": end},
    ).json()
    after = client.get(f"/api/care-recipients/{recipient['id']}/timeline").json()
    assert first["id"] == second["id"]
    assert before == after


def test_report_can_be_edited_and_approved():
    client, report = _report()
    edited = client.patch(
        f"/api/reports/{report['id']}",
        json={"edited_markdown": "Version relue."},
    )
    assert edited.status_code == 200
    assert edited.json()["content"] == "Version relue."
    approved = client.post(f"/api/reports/{report['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["approved"] is True
    assert approved.json()["approved_at"] is not None
    assert client.patch(
        f"/api/reports/{report['id']}",
        json={"edited_markdown": "Interdit."},
    ).status_code == 409
