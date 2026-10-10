"""Shared Pydantic models from specs/contracts/ (Observation, WearableSample, SentMessage)."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from datetime import datetime, timezone

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    model_serializer,
)

Category = Literal[
    "sleep",
    "meals_hydration",
    "medication",
    "mood_behavior",
    "mobility_falls",
    "pain",
    "vitals",
    "incident",
    "appointment",
    "logistics",
]
Severity = Literal["info", "watch", "urgent"]
Source = Literal["caregiver_voice", "wearable", "auxiliary_report"]
SleepState = Literal["awake", "light", "deep"]
RecipientRole = Literal["auxiliary", "family", "doctor", "caregiver"]
Channel = Literal["mock", "sns", "ses", "telegram"]


class _ContractModel(BaseModel):
    """Base for contract models: unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")


class Observation(_ContractModel):
    """One fact about the cared-for person (specs/contracts/observation.md)."""

    id: str
    timestamp: AwareDatetime
    reported_at: AwareDatetime
    subject_id: str
    category: Category
    value: str
    severity: Severity
    source: Source
    reported_by: str
    confidence: Annotated[float, Field(ge=0, le=1)]
    transcript_span: str


class WearableSample(_ContractModel):
    """One bracelet reading (specs/contracts/wearable-sample.md). Unset optional fields are omitted on output."""

    timestamp: AwareDatetime
    subject_id: str
    heart_rate_bpm: Optional[Annotated[int, Field(ge=0)]] = None
    sleep_state: Optional[SleepState] = None
    spo2_pct: Optional[Annotated[float, Field(ge=0, le=100)]] = None
    steps: Optional[Annotated[int, Field(ge=0)]] = None

    @model_serializer(mode="wrap")
    def _omit_none(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data = handler(self)
        return {key: value for key, value in data.items() if value is not None}


class SentMessage(_ContractModel):
    """A notification sent to one recipient, with the observation IDs it was built from."""

    id: str
    recipient: RecipientRole
    channel: Channel
    body: str
    observation_ids: list[str]
    sent_at: AwareDatetime


class VoiceReportResponse(_ContractModel):
    """Successful voice report: the stored audio key (null when not uploaded) and its transcript."""

    report_id: str
    audio_s3_key: Optional[str]
    transcript: str
    source: Literal["transcribe", "cache"]


class ExtractRequest(_ContractModel):
    """Body of POST /api/reports/extract. `reported_at` defaults to now (UTC) when omitted.

    An empty or whitespace-only transcript is accepted by the model so the route can return the
    feature's own French 422 detail rather than a generic Pydantic validation error.
    """

    transcript: str
    subject_id: str = Field(min_length=1)
    reported_by: str = Field(min_length=1)
    reported_at: Optional[AwareDatetime] = None

    def resolved_reported_at(self) -> datetime:
        """The report time to use: the supplied aware datetime, or now in UTC."""
        return self.reported_at or datetime.now(timezone.utc)


class ExtractResponse(_ContractModel):
    """Successful extraction: the Observations found and their count."""

    observations: list[Observation]
    count: int


class VoiceReportError(_ContractModel):
    """Failed voice report (HTTP 502). `retryable` is true when the audio is stored and can be re-transcribed."""

    report_id: Optional[str]
    audio_s3_key: Optional[str]
    detail: str
    retryable: bool
