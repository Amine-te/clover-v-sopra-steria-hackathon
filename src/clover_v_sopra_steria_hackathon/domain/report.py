"""Typed, deterministic weekly-report evidence models."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReportObservation(BaseModel):
    id: UUID
    category: str
    description: str
    date: date


class ReportAction(BaseModel):
    id: UUID
    description: str
    status: str
    date: date


class ReportWearable(BaseModel):
    window_start: datetime
    window_end: datetime
    metrics: dict
    source: str = "wearable"


class WeeklyReportContext(BaseModel):
    care_recipient_name: str
    period_start: date
    period_end: date
    source_entry_count: int
    structured_item_count: int
    reportable_item_count: int
    excluded_private_count: int
    observations_by_category: dict[str, list[ReportObservation]] = Field(default_factory=dict)
    recurring_observations: dict[str, dict] = Field(default_factory=dict)
    medication_reported: list[ReportObservation] = Field(default_factory=list)
    completed_actions: list[ReportAction] = Field(default_factory=list)
    pending_actions: list[ReportAction] = Field(default_factory=list)
    notable_events: list[ReportObservation] = Field(default_factory=list)
    wearable_summary: list[ReportWearable] = Field(default_factory=list)
    missing_information_notes: list[str] = Field(default_factory=list)
