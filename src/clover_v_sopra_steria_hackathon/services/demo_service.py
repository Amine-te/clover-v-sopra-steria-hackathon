"""Reset only the demo family's data and reseed the previous complete week.

Run:
    uv run python scripts/reset_demo.py

Demo family:
    Thomas — primary caregiver (author of the journal)
    Marie  — care recipient, 82
    Sophie — family caregiver
    Nadia  — auxiliary
    Marc   — administrative helper
    Paul   — family informed
"""

import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import delete, or_, select
from clover_v_sopra_steria_hackathon.db.session import SessionLocal
from clover_v_sopra_steria_hackathon import models  # noqa: F401 — register tables
from clover_v_sopra_steria_hackathon.models import (
    ActionItem,
    ActionStatus,
    CareCircleMember,
    CareRecipient,
    CaregiverFeeling,
    InputType,
    JournalEntry,
    JournalStatus,
    Observation,
    Role,
    SubjectType,
    User,
    VocalAffectSignal,
    WearableWindow,
    Clarification,
    GeneratedMessage,
    WeeklyReport,
)

UTC = timezone.utc


def demo_id(name: str) -> uuid.UUID:
    """Stable, deterministic identifier for a named demo entity."""
    return uuid.uuid5(uuid.NAMESPACE_URL, f"https://karis.demo/{name}")


# --- Deterministic demo identities -----------------------------------------

MARIE_ID = demo_id("recipient.marie")
THOMAS_ID = demo_id("user.thomas")
SOPHIE_ID = demo_id("user.sophie")
NADIA_ID = demo_id("user.nadia")
MARC_ID = demo_id("user.marc")
PAUL_ID = demo_id("user.paul")


def at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=UTC)


def wipe_demo(session) -> None:
    """Delete Marie's demo history, preserving other families and shared users."""
    entries = select(JournalEntry.id).where(JournalEntry.recipient_id == MARIE_ID)
    members = select(CareCircleMember.id).where(CareCircleMember.recipient_id == MARIE_ID)
    session.execute(delete(GeneratedMessage).where(or_(
        GeneratedMessage.source_entry_id.in_(entries),
        GeneratedMessage.recipient_member_id.in_(members),
    )))
    for model in (Observation, CaregiverFeeling, Clarification, VocalAffectSignal):
        session.execute(delete(model).where(model.entry_id.in_(entries)))
    session.execute(delete(WearableWindow).where(or_(
        WearableWindow.entry_id.in_(entries),
        (WearableWindow.entry_id.is_(None) & WearableWindow.subject_id.in_([MARIE_ID, THOMAS_ID])),
    )))
    session.execute(delete(ActionItem).where(ActionItem.recipient_id == MARIE_ID))
    session.execute(delete(WeeklyReport).where(WeeklyReport.recipient_id == MARIE_ID))
    session.execute(delete(JournalEntry).where(JournalEntry.recipient_id == MARIE_ID))
    session.execute(delete(CareCircleMember).where(CareCircleMember.recipient_id == MARIE_ID))
    session.execute(delete(CareRecipient).where(CareRecipient.id == MARIE_ID))


def demo_period() -> tuple[date, date]:
    today = date.today()
    end = today - timedelta(days=today.weekday() + 1)
    return end - timedelta(days=6), end


def reset_demo(session) -> dict[str, int]:
    """Caller owns the transaction; deletion and reseeding are atomic."""
    wipe_demo(session)
    return seed(session)


def seed(session) -> dict[str, int]:
    today = date.today()
    # Full Mon→Sun week ending the most recent Sunday strictly before today,
    # so the whole seeded week is always in the past and content is stable.
    _, last_sunday = demo_period()
    days = [last_sunday - timedelta(days=6 - i) for i in range(7)]  # Mon..Sun

    # --- People & circle ---
    marie = CareRecipient(
        id=MARIE_ID, first_name="Marie", last_name="Durand",
        date_of_birth=date(1944, 3, 12), notes="82 ans, vit à domicile.",
    )
    users = [
        User(id=THOMAS_ID, full_name="Thomas Durand", email="thomas@karis.demo"),
        User(id=SOPHIE_ID, full_name="Sophie Lambert", email="sophie@karis.demo"),
        User(id=NADIA_ID, full_name="Nadia Benali", email="nadia@karis.demo"),
        User(id=MARC_ID, full_name="Marc Petit", email="marc@karis.demo"),
        User(id=PAUL_ID, full_name="Paul Durand", email="paul@karis.demo"),
    ]
    members = [
        CareCircleMember(id=demo_id("member.thomas"), recipient_id=MARIE_ID,
                         user_id=THOMAS_ID, role=Role.PRIMARY_CAREGIVER),
        CareCircleMember(id=demo_id("member.sophie"), recipient_id=MARIE_ID,
                         user_id=SOPHIE_ID, role=Role.FAMILY_CAREGIVER),
        CareCircleMember(id=demo_id("member.nadia"), recipient_id=MARIE_ID,
                         user_id=NADIA_ID, role=Role.AUXILIARY),
        CareCircleMember(id=demo_id("member.marc"), recipient_id=MARIE_ID,
                         user_id=MARC_ID, role=Role.ADMINISTRATIVE_HELPER),
        CareCircleMember(id=demo_id("member.paul"), recipient_id=MARIE_ID,
                         user_id=PAUL_ID, role=Role.FAMILY_INFORMED),
    ]
    for user in users:
        session.merge(user)
    session.add_all([marie, *members])
    session.flush()  # people must exist before dependent rows are inserted

    monday, tuesday, wednesday, thursday, friday, saturday, sunday = days

    counts: dict[str, int] = {
        "users": len(users),
        "care_circle_members": len(members),
        "care_recipients": 1,
    }

    def make_entry(day: date, text: str, *, finalized: bool = True, **kwargs) -> JournalEntry:
        occurred = at(day, 18)
        kwargs.setdefault("input_type", InputType.TEXT)
        entry = JournalEntry(
            id=demo_id(f"entry.{day.isoformat()}"),
            recipient_id=MARIE_ID,
            author_id=THOMAS_ID,
            original_text=text,
            occurred_at=occurred,
            **kwargs,
        )
        if finalized:
            entry.status = JournalStatus.FINALIZED
            entry.finalized_at = occurred + timedelta(hours=2)
        session.add(entry)
        return entry

    def observe(entry: JournalEntry, category: str, summary: str) -> None:
        session.add(
            Observation(
                id=demo_id(f"obs.{entry.occurred_at.date().isoformat()}.{category}"),
                entry_id=entry.id,
                recipient_id=MARIE_ID,
                category=category,
                summary=summary,
            )
        )
        counts["observations"] = counts.get("observations", 0) + 1

    # --- 7 days of history ---
    e_mon = make_entry(monday, "Nuit agitée pour maman, elle s'est levée trois fois. La matinée a été calme.")
    observe(e_mon, "sleep", "Nuit agitée (3 réveils nocturnes)")

    e_tue = make_entry(tuesday, "Maman a à peine touché son assiette ce midi, deux bouchées de purée. Traitement pris normalement.")
    observe(e_tue, "nutrition", "Repas du midi presque pas touché (faible prise alimentaire)")
    observe(e_tue, "medication", "Traitement pris normalement (rapporté)")

    e_wed = make_entry(wednesday, "Encore un repas presque pas mangé ce soir. Elle dit qu'elle n'a pas faim.")
    observe(e_wed, "nutrition", "Repas du soir presque pas mangé — appétit en baisse")

    demo_sentence = (
        "Maman était plus fatiguée aujourd'hui. Elle a pris son traitement mais "
        "elle n'a presque rien mangé. Sophie passe ce soir. Moi je suis vraiment crevé."
    )
    e_thu = make_entry(
        thursday,
        demo_sentence,
        input_type=InputType.VOICE,
        audio_object_key="mock-audio/demo/thomas-jeudi",
        transcript=demo_sentence,
    )
    observe(e_thu, "fatigue", "Fatigue inhabituelle dans la journée")
    observe(e_thu, "nutrition", "Presque rien mangé dans la journée (3e jour consécutif)")
    observe(e_thu, "medication", "Traitement pris (rapporté par Thomas)")
    observe(e_thu, "appointment", "Séance de kiné annulée par le cabinet")

    # Thomas' exhaustion — PRIVATE by default (visibility intentionally omitted).
    session.add(
        CaregiverFeeling(
            id=demo_id("feeling.thomas.fatigue"),
            entry_id=e_thu.id,
            caregiver_id=THOMAS_ID,
            feeling="fatigue",
            intensity=4,
            note="Moi je suis vraiment crevé.",
        )
    )
    counts["caregiver_feelings"] = 1

    # Mock SER signal on Thomas' voice — PRIVATE by default as well.
    session.add(
        VocalAffectSignal(
            id=demo_id("ser.thomas.jeudi"),
            entry_id=e_thu.id,
            caregiver_id=THOMAS_ID,
            valence="negative",
            arousal="high",
            confidence=0.61,
        )
    )
    counts["vocal_affect_signals"] = 1

    e_fri = make_entry(friday, "Deuxième nuit très agitée cette semaine, maman était confuse au réveil.")
    observe(e_fri, "sleep", "Nuit très agitée, confusion au réveil")

    e_sat = make_entry(saturday, "Bonne journée dans l'ensemble. Maman a bien mangé et a marché un peu dans le jardin.")
    observe(e_sat, "mood", "Moral stable")

    # Latest entry stays DRAFT (weekly reports must ignore non-finalized entries).
    make_entry(sunday, "Journée tranquille. Repas correct ce soir.", finalized=False)

    counts["journal_entries"] = 7

    # --- Actions: 1 cancelled appointment, 1 done, 1 pending ---
    actions = [
        ActionItem(
            id=demo_id("action.kine"),
            recipient_id=MARIE_ID,
            entry_id=e_thu.id,
            title="Séance de kiné du jeudi",
            description="Annulée par le cabinet (indisponibilité du kinésithérapeute).",
            status=ActionStatus.CANCELLED,
            assignee_id=THOMAS_ID,
            due_date=at(thursday, 14),
        ),
        ActionItem(
            id=demo_id("action.ordonnance"),
            recipient_id=MARIE_ID,
            entry_id=e_tue.id,
            title="Renouveler l'ordonnance de Marie",
            status=ActionStatus.DONE,
            assignee_id=THOMAS_ID,
            due_date=at(friday, 10),
            completed_at=at(friday, 10),
        ),
        ActionItem(
            id=demo_id("action.dentiste"),
            recipient_id=MARIE_ID,
            entry_id=e_sat.id,
            title="Prendre rendez-vous chez le dentiste",
            status=ActionStatus.PENDING,
            assignee_id=SOPHIE_ID,
            due_date=at(today + timedelta(days=5), 9),
        ),
    ]
    session.add_all(actions)
    counts["action_items"] = len(actions)

    # --- Wearable windows: Marie (circle-visible) & Thomas (PRIVATE by rule) ---
    windows: list[WearableWindow] = []
    for day in days:
        windows.append(
            WearableWindow(
                id=demo_id(f"wear.marie.{day.isoformat()}"),
                subject_type=SubjectType.CARE_RECIPIENT,
                subject_id=MARIE_ID,
                window_start=at(day, 7),
                window_end=at(day, 21),
                metrics={"heart_rate_avg": 74, "steps": 1320, "sleep_hours": 7.1},
            )
        )
        windows.append(
            WearableWindow(
                id=demo_id(f"wear.thomas.{day.isoformat()}"),
                subject_type=SubjectType.CAREGIVER,
                subject_id=THOMAS_ID,
                window_start=at(day, 7),
                window_end=at(day, 21),
                metrics={"heart_rate_avg": 91, "steps": 8600, "sleep_hours": 5.5},
            )
        )
    session.add_all(windows)
    counts["wearable_windows"] = len(windows)

    return counts


def main() -> int:
    with SessionLocal() as session, session.begin():
        counts = reset_demo(session)

    print("Demo reset OK — deterministic dataset (uuid5 ids):")
    for table, count in sorted(counts.items()):
        print(f"  {table:<24} {count}")
    print("Circle: Thomas (primary), Marie (recipient), Sophie (family), "
          "Nadia (auxiliary), Marc (admin), Paul (informed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
