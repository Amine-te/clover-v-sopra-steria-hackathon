"""Pydantic contracts for the M3 text journal vertical slice."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..models.enums import InputType, JournalStatus, Role, Visibility
from ..providers.base import ProviderMetadata


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str | None


class CareRecipientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    date_of_birth: date | None
    notes: str


class MemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    role: Role
    active: bool


class JournalCreate(BaseModel):
    care_recipient_id: UUID
    input_type: InputType = InputType.TEXT
    original_text: str = Field(min_length=1)


class TranscriptResponse(BaseModel):
    journal_entry_id: UUID
    transcript: str
    language: str
    provider: str
    transcription_status: str


class AudioUploadResponse(BaseModel):
    storage_provider: str | None = None
    journal_entry_id: UUID
    input_type: InputType
    audio_mime_type: str
    audio_object_key: str
    transcription_status: str


class TranscriptPatch(BaseModel):
    transcript: str = Field(min_length=1)


class ObservationResponse(BaseModel):
    id: UUID
    category: str
    description: str
    visibility: Visibility
    include_in_weekly_report: bool = True


class FeelingResponse(BaseModel):
    id: UUID
    description: str
    visibility: Visibility


class ActionResponse(BaseModel):
    id: UUID
    description: str
    status: str
    assigned_member_id: UUID | None = None


class ClarificationResponse(BaseModel):
    id: UUID
    question: str
    reason: str
    answer: str | None
    answered_at: datetime | None


class ClarificationAnswer(BaseModel):
    clarification_id: UUID
    answer: str = Field(min_length=1)


class ClarificationSubmission(BaseModel):
    answers: list[ClarificationAnswer] = Field(max_length=3)


class JournalResponse(BaseModel):
    provider_metadata: ProviderMetadata | None = None
    id: UUID
    care_recipient_id: UUID
    author_user_id: UUID
    input_type: InputType
    status: JournalStatus
    original_text: str
    transcript: str | None
    occurred_at: datetime
    finalized_at: datetime | None
    short_summary: str | None = None
    observations: list[ObservationResponse] = []
    caregiver_feelings: list[FeelingResponse] = []
    actions: list[ActionResponse] = []
    people_mentioned: list[str] = []
    has_private_data: bool = False
    clarifications: list[ClarificationResponse] = []
    clarification_needed: bool = False
    audio_object_key: str | None = None
    audio_mime_type: str | None = None
    transcription_status: str | None = None


class TimelineItem(BaseModel):
    id: UUID
    date: datetime
    short_summary: str
    observations: list[ObservationResponse]
    actions: list[ActionResponse]
    source_type: InputType
    has_private_data: bool


class TimelineResponse(BaseModel):
    care_recipient_id: UUID
    items: list[TimelineItem]


class VocalAffectResponse(BaseModel):
    source: str
    subject_id: UUID
    valence: str | None
    arousal: str | None
    top_label: str | None
    confidence: float
    quality: str
    model_version: str
    visibility: str
    provider: str
    timestamp: datetime


class WearableContextResponse(BaseModel):
    source: str
    subject_type: str
    subject_id: UUID
    window_start: datetime
    window_end: datetime
    metrics: dict[str, Any]
    quality: str
    visibility: str
    provider: str


class MultimodalContextResponse(BaseModel):
    journal_entry_id: UUID
    transcript_or_text: str
    semantic_analysis: dict[str, Any]
    caregiver_vocal_affect: VocalAffectResponse | None
    caregiver_wearable: WearableContextResponse | None
    care_recipient_wearable: WearableContextResponse | None
    modalities_present: list[str]
    provenance: dict[str, str]


class PrivacyPipeline(BaseModel):
    structured_count: int
    shareable_count: int
    authorized_count: int
    transmitted_count: int
    private_transmitted_count: int = 0


class MessageResponse(BaseModel):
    privacy_pipeline: PrivacyPipeline | None = None
    provider_metadata: ProviderMetadata | None = None
    id: UUID
    recipient_member_id: UUID
    recipient_name: str
    recipient_role: Role
    source_entry_id: UUID | None
    channel: str
    text: str
    approved: bool
    delivery_status: str
    sent_at: datetime | None
    structured_item_count: int
    allowed_item_count: int
    excluded_private_count: int


class MessageGenerationResponse(BaseModel):
    drafts: list[MessageResponse]


class MessagePatch(BaseModel):
    edited_text: str | None = Field(default=None, min_length=1)
    approved: bool | None = None
    enabled: bool | None = None


class MockInboxItem(BaseModel):
    id: UUID
    recipient_name: str
    recipient_role: Role
    channel: str
    text: str
    delivery_status: str
    sent_at: datetime


class MockInboxResponse(BaseModel):
    messages: list[MockInboxItem]


class WeeklyReportGenerate(BaseModel):
    period_start: date
    period_end: date


class WeeklyReportResponse(BaseModel):
    provider_metadata: ProviderMetadata | None = None
    id: UUID
    recipient_id: UUID
    period_start: date
    period_end: date
    title: str
    content: str
    approved: bool
    approved_at: datetime | None
    source_entry_count: int
    structured_item_count: int
    reportable_item_count: int
    excluded_private_count: int


class WeeklyReportPatch(BaseModel):
    edited_markdown: str = Field(min_length=1)


class AnalyzeResponse(JournalResponse):
    pass


class ErrorResponse(BaseModel):
    detail: str
