"""Deterministic evidence aggregation and weekly report generation."""

from collections import defaultdict
from datetime import date, datetime, time, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..domain.report import (
    ReportAction,
    ReportObservation,
    ReportWearable,
    WeeklyReportContext,
)
from ..models import (
    ActionItem,
    CareRecipient,
    JournalEntry,
    JournalStatus,
    SubjectType,
    Visibility,
    WearableWindow,
)
from ..providers.base import LLMProvider, WeeklyReportDraft


class ReportAggregationService:
    def __init__(self, db: Session):
        self.db = db

    def build(
        self, *, recipient_id: UUID, period_start: date, period_end: date
    ) -> WeeklyReportContext:
        start = datetime.combine(period_start, time.min, tzinfo=timezone.utc)
        end = datetime.combine(period_end, time.max, tzinfo=timezone.utc)
        entries = list(
            self.db.scalars(
                select(JournalEntry)
                .where(
                    JournalEntry.recipient_id == recipient_id,
                    JournalEntry.status == JournalStatus.FINALIZED,
                    JournalEntry.occurred_at >= start,
                    JournalEntry.occurred_at <= end,
                )
                .options(
                    selectinload(JournalEntry.observations),
                    selectinload(JournalEntry.action_items),
                    selectinload(JournalEntry.feelings),
                    selectinload(JournalEntry.vocal_signals),
                    selectinload(JournalEntry.wearable_windows),
                )
                .order_by(JournalEntry.occurred_at)
            )
        )
        recipient = self.db.get(CareRecipient, recipient_id)
        if recipient is None:
            raise ValueError("Care recipient not found.")

        observations_by_category: dict[str, list[ReportObservation]] = defaultdict(list)
        medication: list[ReportObservation] = []
        notable: list[ReportObservation] = []
        structured_count = 0
        reportable_count = 0
        excluded_private = 0
        for entry in entries:
            for observation in entry.observations:
                structured_count += 1
                if observation.visibility == Visibility.PRIVATE:
                    excluded_private += 1
                    continue
                if not observation.include_in_weekly_report:
                    continue
                reportable_count += 1
                item = ReportObservation(
                    id=observation.id,
                    category=observation.category,
                    description=observation.summary,
                    date=entry.occurred_at.date(),
                )
                observations_by_category[observation.category].append(item)
                if observation.category == "medication":
                    medication.append(item)
                if observation.category in {"sleep", "appointment", "logistics"}:
                    notable.append(item)
            excluded_private += len(entry.feelings) + len(entry.vocal_signals)

        actions = list(
            self.db.scalars(
                select(ActionItem)
                .where(
                    ActionItem.recipient_id == recipient_id,
                    ActionItem.entry_id.in_([entry.id for entry in entries])
                    if entries
                    else False,
                )
            )
        )
        completed: list[ReportAction] = []
        pending: list[ReportAction] = []
        for action in actions:
            action_date = action.due_date.date() if action.due_date else period_start
            item = ReportAction(
                id=action.id,
                description=action.title,
                status=action.status.value,
                date=action_date,
            )
            if action.status.value == "done":
                completed.append(item)
            elif action.status.value == "pending":
                pending.append(item)
            structured_count += 1
            reportable_count += 1

        recurring: dict[str, dict] = {}
        for category, items in observations_by_category.items():
            if len(items) > 1:
                recurring[category] = {
                    "count": len(items),
                    "dates": [item.date.isoformat() for item in items],
                    "descriptions": [item.description for item in items],
                }

        wearable = list(
            self.db.scalars(
                select(WearableWindow)
                .where(
                    WearableWindow.subject_type == SubjectType.CARE_RECIPIENT,
                    WearableWindow.subject_id == recipient_id,
                    WearableWindow.visibility != Visibility.PRIVATE,
                    WearableWindow.window_start <= end,
                    WearableWindow.window_end >= start,
                )
                .order_by(WearableWindow.window_start)
            )
        )
        wearable_summary = [
            ReportWearable(
                window_start=item.window_start,
                window_end=item.window_end,
                metrics=item.metrics,
            )
            for item in wearable
        ]
        caregiver_wearables = self.db.scalar(
            select(func.count(WearableWindow.id))
            .where(
                WearableWindow.subject_type == SubjectType.CAREGIVER,
                WearableWindow.visibility == Visibility.PRIVATE,
                WearableWindow.window_start <= end,
                WearableWindow.window_end >= start,
            )
        )
        excluded_private += caregiver_wearables or 0
        missing = []
        if not medication:
            missing.append("Aucune observation médicamenteuse n'est disponible sur la période.")
        return WeeklyReportContext(
            care_recipient_name=recipient.first_name,
            period_start=period_start,
            period_end=period_end,
            source_entry_count=len(entries),
            structured_item_count=structured_count,
            reportable_item_count=reportable_count,
            excluded_private_count=excluded_private,
            observations_by_category=dict(observations_by_category),
            recurring_observations=recurring,
            medication_reported=medication,
            completed_actions=completed,
            pending_actions=pending,
            notable_events=notable,
            wearable_summary=wearable_summary,
            missing_information_notes=missing,
        )


class WeeklyReportService:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def generate(self, context: WeeklyReportContext) -> WeeklyReportDraft:
        return self.llm.generate_weekly_report(
            context=context.model_dump(mode="json")
        )
