"""Journal aggregate: JournalEntry (aggregate root) and its child entities.

Privacy defaults are enforced at construction time (not only at INSERT) so the
rules are real in Python and testable without a database session.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from ..domain.exceptions import BusinessRuleViolation
from .enums import ActionStatus, InputType, JournalStatus, Visibility, pg_enum
from .mixins import CreatedAtMixin, IdMixin, utcnow


class JournalEntry(IdMixin, CreatedAtMixin, Base):
    """Aggregate root: the original dictation/text is always preserved."""

    __tablename__ = "journal_entries"

    recipient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("care_recipients.id"), index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    input_type: Mapped[InputType] = mapped_column(pg_enum(InputType, "input_type"))
    status: Mapped[JournalStatus] = mapped_column(
        pg_enum(JournalStatus, "journal_status")
    )
    original_text: Mapped[str] = mapped_column(Text)
    transcript: Mapped[str | None] = mapped_column(Text)
    audio_object_key: Mapped[str | None] = mapped_column(String(512))
    audio_mime_type: Mapped[str | None] = mapped_column(String(100))
    transcription_status: Mapped[str | None] = mapped_column(String(30))
    transcription_duration_ms: Mapped[int | None] = mapped_column(Integer)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    analysis_summary: Mapped[str | None] = mapped_column(Text)
    people_mentioned: Mapped[list] = mapped_column(JSON, default=list)

    observations: Mapped[list["Observation"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )
    feelings: Mapped[list["CaregiverFeeling"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )
    action_items: Mapped[list["ActionItem"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )
    clarifications: Mapped[list["Clarification"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )
    vocal_signals: Mapped[list["VocalAffectSignal"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )
    wearable_windows: Mapped[list["WearableWindow"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("status", JournalStatus.DRAFT)
        super().__init__(**kwargs)

    @property
    def is_finalized(self) -> bool:
        return self.status == JournalStatus.FINALIZED

    def finalize(self) -> None:
        if self.status == JournalStatus.FINALIZED:
            raise BusinessRuleViolation("Journal entry is already finalized.")
        self.status = JournalStatus.FINALIZED
        self.finalized_at = utcnow()


class Observation(IdMixin, CreatedAtMixin, Base):
    """A factual observation about the care recipient (shareable by default)."""

    __tablename__ = "observations"

    entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journal_entries.id"), index=True
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("care_recipients.id"), index=True
    )
    category: Mapped[str] = mapped_column(String(50), index=True)
    summary: Mapped[str] = mapped_column(Text)
    visibility: Mapped[Visibility] = mapped_column(pg_enum(Visibility, "visibility"))
    include_in_weekly_report: Mapped[bool] = mapped_column(Boolean, default=True)

    entry: Mapped[JournalEntry] = relationship(back_populates="observations")

    def __init__(self, **kwargs):
        kwargs.setdefault("visibility", Visibility.CIRCLE)
        super().__init__(**kwargs)


class CaregiverFeeling(IdMixin, CreatedAtMixin, Base):
    """How the caregiver feels. PRIVATE by default — never shared implicitly."""

    __tablename__ = "caregiver_feelings"
    __table_args__ = (
        CheckConstraint(
            "intensity IS NULL OR (intensity >= 1 AND intensity <= 5)",
            name="ck_feeling_intensity_range",
        ),
    )

    entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journal_entries.id"), index=True
    )
    caregiver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    feeling: Mapped[str] = mapped_column(String(80))
    intensity: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str] = mapped_column(Text, default="")
    visibility: Mapped[Visibility] = mapped_column(pg_enum(Visibility, "visibility"))

    entry: Mapped[JournalEntry] = relationship(back_populates="feelings")

    def __init__(self, **kwargs):
        kwargs.setdefault("visibility", Visibility.PRIVATE)
        super().__init__(**kwargs)


class ActionItem(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "action_items"

    recipient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("care_recipients.id"), index=True
    )
    entry_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("journal_entries.id"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[ActionStatus] = mapped_column(pg_enum(ActionStatus, "action_status"))
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    entry: Mapped[JournalEntry | None] = relationship(back_populates="action_items")

    def __init__(self, **kwargs):
        kwargs.setdefault("status", ActionStatus.PENDING)
        super().__init__(**kwargs)

    def complete(self) -> None:
        if self.status == ActionStatus.CANCELLED:
            raise BusinessRuleViolation("A cancelled action cannot be completed.")
        self.status = ActionStatus.DONE
        self.completed_at = utcnow()

    def cancel(self) -> None:
        if self.status == ActionStatus.DONE:
            raise BusinessRuleViolation("A completed action cannot be cancelled.")
        self.status = ActionStatus.CANCELLED


class Clarification(IdMixin, CreatedAtMixin, Base):
    """A follow-up question asked to the caregiver about an entry (M4)."""

    __tablename__ = "clarifications"

    entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journal_entries.id"), index=True
    )
    question: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text, default="")
    answer: Mapped[str | None] = mapped_column(Text)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    entry: Mapped[JournalEntry] = relationship(back_populates="clarifications")

    @property
    def is_answered(self) -> bool:
        return self.answer is not None


class VocalAffectSignal(IdMixin, CreatedAtMixin, Base):
    """Vocal emotion signal about the CAREGIVER's voice. PRIVATE by default."""

    __tablename__ = "vocal_affect_signals"

    entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journal_entries.id"), index=True
    )
    caregiver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    valence: Mapped[str | None] = mapped_column(String(20))
    arousal: Mapped[str | None] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    top_label: Mapped[str | None] = mapped_column(String(50))
    quality: Mapped[str] = mapped_column(String(30), default="unknown")
    model_version: Mapped[str] = mapped_column(String(80), default="")
    provider: Mapped[str] = mapped_column(String(80), default="mock")
    visibility: Mapped[Visibility] = mapped_column(pg_enum(Visibility, "visibility"))

    entry: Mapped[JournalEntry] = relationship(back_populates="vocal_signals")

    def __init__(self, **kwargs):
        kwargs.setdefault("visibility", Visibility.PRIVATE)
        super().__init__(**kwargs)
