"""Local, offline-provider preflight. Never resets demo data or sends a message."""

import argparse
import sys
from typing import TextIO
from uuid import UUID

import httpx
from sqlalchemy import delete, select, text

from clover_v_sopra_steria_hackathon.db.session import SessionLocal
from clover_v_sopra_steria_hackathon.domain.privacy import RecipientContextBuilder
from clover_v_sopra_steria_hackathon.models import CareCircleMember, CareRecipient, GeneratedMessage, JournalEntry, User
from clover_v_sopra_steria_hackathon.providers.registry import (
    get_llm_provider, get_messaging_provider, get_object_storage_provider,
    get_ser_provider, get_transcription_provider, get_wearable_provider,
)
from clover_v_sopra_steria_hackathon.services.demo_service import MARIE_ID, THOMAS_ID, demo_period

DEMO_TEXT = "Maman était plus fatiguée aujourd’hui. Elle a pris son traitement mais elle n’a presque rien mangé. Sophie passe ce soir. Moi je suis vraiment crevé."


def run_checks(client, output: TextIO = sys.stdout) -> bool:
    """Use the running API and its PostgreSQL database; stop on a critical failure."""
    entry_id = None
    results: list[bool] = []

    def check(label, action):
        try:
            value = action()
            if value is False:
                raise AssertionError("Check failed")
        except Exception as error:
            print(f"[FAIL] {label} ({type(error).__name__})", file=output)
            results.append(False)
            raise
        print(f"[PASS] {label}", file=output)
        results.append(True)
        return value

    def request(method, path, **kwargs):
        response = client.request(method, f"/api{path}", **kwargs)
        response.raise_for_status()
        return response.json()

    print("Karis demo smoke test", file=output)
    try:
        check("Backend", lambda: request("GET", "/health")["status"] == "ok")
        with SessionLocal() as db:
            check("Database", lambda: db.scalar(text("SELECT 1")) == 1)
            check("Thomas", lambda: db.get(User, THOMAS_ID).email == "thomas@karis.demo")
            check("Marie", lambda: db.get(CareRecipient, MARIE_ID).first_name == "Marie")
            check("Care circle", lambda: len(list(db.scalars(select(CareCircleMember).where(CareCircleMember.recipient_id == MARIE_ID, CareCircleMember.active.is_(True))))) == 5)
        status = check("7-day demo seed", lambda: request("GET", "/demo/status"))
        check("Seed complete", lambda: status["seed_entry_count"] == 7)

        def mocks():
            # Refuse to exercise a live provider in a mock-demo preflight.
            assert all(value == "mock" for value in status["providers"].values())
            providers = [getter() for getter in (get_llm_provider, get_transcription_provider, get_ser_provider, get_wearable_provider, get_object_storage_provider, get_messaging_provider)]
            return all(type(provider).__name__.startswith("Mock") for provider in providers)

        check("Mock providers", mocks)
        entry = check("Journal creation", lambda: request("POST", "/journal", json={"care_recipient_id": str(MARIE_ID), "input_type": "voice", "original_text": DEMO_TEXT}))
        entry_id = UUID(entry["id"])
        check("Audio storage", lambda: request("POST", f"/journal/{entry_id}/audio/demo"))
        check("Transcription", lambda: request("POST", f"/journal/{entry_id}/transcribe")["transcription_status"] == "completed")
        context = request("POST", f"/journal/{entry_id}/multimodal/enrich")
        check("Multimodal", lambda: all(context[key] is not None for key in ("caregiver_vocal_affect", "caregiver_wearable", "care_recipient_wearable")))
        analyzed = request("POST", f"/journal/{entry_id}/analyze")
        check("Analysis", lambda: len(analyzed["observations"]) == 3 and analyzed["caregiver_feelings"][0]["visibility"] == "private")
        clarified = request("POST", f"/journal/{entry_id}/clarifications", json={"answers": [{"clarification_id": item["id"], "answer": "Oui"} for item in analyzed["clarifications"]]})
        check("Clarification", lambda: len(analyzed["clarifications"]) == 2 and not clarified["clarification_needed"] and all(item["answer"] == "Oui" for item in clarified["clarifications"]))
        request("POST", f"/journal/{entry_id}/finalize")

        def privacy():
            from clover_v_sopra_steria_hackathon.api.routes.journal import _entry_query
            from sqlalchemy.orm import selectinload
            with SessionLocal() as db:
                saved = db.scalar(_entry_query().where(JournalEntry.id == entry_id))
                members = list(db.scalars(select(CareCircleMember).where(CareCircleMember.recipient_id == MARIE_ID).options(selectinload(CareCircleMember.user))))
                sophie = next(member for member in members if member.user.full_name.startswith("Sophie"))
                context = RecipientContextBuilder().build(entry=saved, member=sophie)
                serialized = context.model_dump_json()
                assert len(context.source_item_ids) == 3 and context.excluded_private_count == 3
                assert not any(key in serialized for key in ("original_text", "caregiver_feelings", "caregiver_vocal_affect", "caregiver_wearable", "crevé", "heart_rate_avg", "valence", "confidence"))
                return True

        check("Sophie privacy", privacy)
        drafts = request("POST", f"/journal/{entry_id}/messages/generate")["drafts"]
        check("Routing", lambda: {item["recipient_name"] for item in drafts} == {"Sophie", "Nadia"})
        check("Messaging drafts", lambda: all(not item["approved"] and item["delivery_status"] == "draft" and item["privacy_pipeline"]["private_transmitted_count"] == 0 and "crevé" not in item["text"] for item in drafts))
        start, end = demo_period()
        report = request("POST", f"/care-recipients/{MARIE_ID}/reports/weekly/generate", json={"period_start": start.isoformat(), "period_end": end.isoformat()})
        check("Weekly report", lambda: report["source_entry_count"] == 6 and "Une faible alimentation a été rapportée à trois reprises entre mardi et jeudi." in report["content"])
    except Exception:
        pass  # individual check has already printed a safe, compact failure
        if not results or results[-1]:
            print("[FAIL] Demo workflow", file=output)
            results.append(False)
    finally:
        if entry_id is not None:
            try:
                with SessionLocal() as db, db.begin():
                    db.execute(delete(GeneratedMessage).where(GeneratedMessage.source_entry_id == entry_id))
                    entry = db.get(JournalEntry, entry_id)
                    if entry is not None:
                        db.delete(entry)  # ORM removes only this preflight's child objects
            except Exception as error:
                print(f"[FAIL] Preflight cleanup ({type(error).__name__})", file=output)
                results.append(False)
    ready = bool(results) and all(results)
    print("\nDEMO READY" if ready else "\nDEMO NOT READY — vérifiez les services et relancez le préflight.", file=output)
    return ready


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the local Karis mock demo.")
    parser.add_argument("--api-url", default="http://localhost:8000")
    args = parser.parse_args()
    with httpx.Client(base_url=args.api_url, timeout=20) as client:
        return 0 if run_checks(client) else 1


if __name__ == "__main__":
    raise SystemExit(main())
