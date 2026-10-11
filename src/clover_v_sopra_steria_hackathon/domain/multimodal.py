"""Typed, provenance-preserving multimodal journal context."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ..models import JournalEntry, VocalAffectSignal, WearableWindow


class VocalAffectContext(BaseModel):
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


class WearableContext(BaseModel):
    source: str
    subject_type: str
    subject_id: UUID
    window_start: datetime
    window_end: datetime
    metrics: dict
    quality: str
    visibility: str
    provider: str


class MultimodalJournalContext(BaseModel):
    journal_entry_id: UUID
    transcript_or_text: str
    semantic_analysis: dict = Field(default_factory=dict)
    caregiver_vocal_affect: VocalAffectContext | None = None
    caregiver_wearable: WearableContext | None = None
    care_recipient_wearable: WearableContext | None = None
    modalities_present: list[str] = Field(default_factory=list)
    provenance: dict[str, str] = Field(default_factory=dict)


def build_multimodal_context(entry: JournalEntry) -> MultimodalJournalContext:
    signal = entry.vocal_signals[0] if entry.vocal_signals else None
    caregiver_window = next(
        (w for w in entry.wearable_windows if w.subject_type.value == "caregiver"),
        None,
    )
    recipient_window = next(
        (w for w in entry.wearable_windows if w.subject_type.value == "care_recipient"),
        None,
    )

    def wearable_context(window: WearableWindow) -> WearableContext:
        return WearableContext(
            source="wearable",
            subject_type=window.subject_type.value,
            subject_id=window.subject_id,
            window_start=window.window_start,
            window_end=window.window_end,
            metrics=window.metrics,
            quality=window.metrics.get("quality", "unknown"),
            visibility=window.visibility.value,
            provider=window.metrics.get("provider", "unknown"),
        )

    result = MultimodalJournalContext(
        journal_entry_id=entry.id,
        transcript_or_text=entry.transcript or entry.original_text,
        semantic_analysis={
            "summary": entry.analysis_summary,
            "observations": [
                {"category": item.category, "description": item.summary}
                for item in entry.observations
            ],
            "actions": [item.title for item in entry.action_items],
        },
        provenance={"text": "journal", "semantic_analysis": "llm"},
    )
    if signal:
        result.caregiver_vocal_affect = VocalAffectContext(
            source="ser_caregiver",
            subject_id=signal.caregiver_id,
            valence=signal.valence,
            arousal=signal.arousal,
            top_label=signal.top_label,
            confidence=signal.confidence,
            quality=signal.quality,
            model_version=signal.model_version,
            visibility=signal.visibility.value,
            provider=signal.provider,
            timestamp=signal.created_at,
        )
        result.modalities_present.append("ser_caregiver")
        result.provenance["ser_caregiver"] = signal.provider
    if caregiver_window:
        result.caregiver_wearable = wearable_context(caregiver_window)
        result.modalities_present.append("wearable_caregiver")
        result.provenance["wearable_caregiver"] = caregiver_window.metrics.get("provider", "unknown")
    if recipient_window:
        result.care_recipient_wearable = wearable_context(recipient_window)
        result.modalities_present.append("wearable_care_recipient")
        result.provenance["wearable_care_recipient"] = recipient_window.metrics.get("provider", "unknown")
    if entry.original_text or entry.transcript:
        result.modalities_present.insert(0, "text")
    return result
