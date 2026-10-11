"""Provider interfaces (typing.Protocol) and shared result models.

All providers are swappable via environment variables (see registry.py).
Business services must depend ONLY on these protocols — never on a concrete
implementation — so live providers (BedrockLLMProvider, AWSTranscribeProvider,
S3ObjectStorageProvider, ...) can be added later without touching services.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, TYPE_CHECKING, runtime_checkable

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .llm.contracts import JournalAnalysisContext


class ProviderMetadata(BaseModel):
    provider_used: str
    model_id: str | None = None
    latency_ms: int = Field(default=0, ge=0)
    validation_retry_count: int = Field(default=0, ge=0, le=1)
    fallback_used: bool = False

# ---------------------------------------------------------------------------
# Result models (Pydantic v2) — placeholders, refined in later milestones.
# ---------------------------------------------------------------------------


class JournalAnalysisResult(BaseModel):
    provider_metadata: ProviderMetadata | None = None
    short_summary: str = ""
    observations: list[dict[str, Any]] = Field(default_factory=list)
    caregiver_feelings: list[dict[str, Any]] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    people_mentioned: list[str] = Field(default_factory=list)
    clarification_needed: bool = False
    questions: list[str] = Field(default_factory=list)
    clarification_reasons: list[str] = Field(default_factory=list)
    provider: str = "mock"


class RecipientMessageDraft(BaseModel):
    provider_metadata: ProviderMetadata | None = None
    recipient: str
    channel: str = "mock"
    text: str
    provider: str = "mock"


class WeeklyReportDraft(BaseModel):
    provider_metadata: ProviderMetadata | None = None
    title: str = ""
    markdown: str = ""
    provider: str = "mock"


class TranscriptResult(BaseModel):
    text: str
    language: str = "fr-FR"
    provider: str = "mock"


class VocalAffectResult(BaseModel):
    valence: str | None = None
    arousal: str | None = None
    top_label: str | None = None
    confidence: float = 0.0
    quality: str = "unknown"
    model_version: str = ""
    visibility: str = "private"
    provider: str = "mock"


class WearableSummary(BaseModel):
    subject_type: str
    subject_id: str
    window_start: datetime
    window_end: datetime
    metrics: dict[str, Any] = Field(default_factory=dict)
    quality: str = "unknown"
    visibility: str = "circle"
    provider: str = "mock"


class DeliveryReceipt(BaseModel):
    channel: str
    recipient: str
    status: str = "queued"
    provider: str = "mock"


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class LLMProvider(Protocol):
    def analyze_journal(
        self, *, text: str, context: JournalAnalysisContext | None = None
    ) -> JournalAnalysisResult: ...

    def generate_recipient_message(
        self, *, recipient_name: str, context: dict[str, Any]
    ) -> RecipientMessageDraft: ...

    def generate_weekly_report(
        self, *, context: dict[str, Any]
    ) -> WeeklyReportDraft: ...


@runtime_checkable
class TranscriptionProvider(Protocol):
    def transcribe(
        self, *, audio_object_key: str, language: str = "fr-FR"
    ) -> TranscriptResult: ...


@runtime_checkable
class SpeechEmotionProvider(Protocol):
    def analyze(self, *, audio_object_key: str) -> VocalAffectResult | None: ...


@runtime_checkable
class WearableProvider(Protocol):
    def summarize(
        self, *, subject_type: str, subject_id: str, around: datetime
    ) -> WearableSummary | None: ...


@runtime_checkable
class ObjectStorageProvider(Protocol):
    def put_audio(self, *, data: bytes, content_type: str) -> str:
        """Store audio bytes and return the object key."""
        ...

    def get_bytes(self, *, object_key: str) -> bytes: ...


@runtime_checkable
class MessagingProvider(Protocol):
    def send(
        self, *, channel: str, recipient: str, text: str
    ) -> DeliveryReceipt: ...
