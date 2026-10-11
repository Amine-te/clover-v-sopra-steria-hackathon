"""WearableWindow — aggregated wearable metrics over a time window.

Privacy rule: windows about a CAREGIVER are PRIVATE by default;
windows about the CARE RECIPIENT are circle-visible by default.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from .enums import SubjectType, Visibility, pg_enum
from .mixins import CreatedAtMixin, IdMixin


class WearableWindow(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "wearable_windows"
    __table_args__ = (
        Index("ix_wearable_subject_window", "subject_type", "subject_id", "window_start"),
    )

    # Polymorphic subject (caregiver -> users.id, recipient -> care_recipients.id):
    # intentionally no FK, the subject spans two tables.
    subject_type: Mapped[SubjectType] = mapped_column(pg_enum(SubjectType, "subject_type"))
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    entry_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("journal_entries.id"), index=True
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    visibility: Mapped[Visibility] = mapped_column(pg_enum(Visibility, "visibility"))
    entry: Mapped["JournalEntry"] = relationship(back_populates="wearable_windows")

    def __init__(self, **kwargs):
        subject = kwargs.get("subject_type")
        if subject is not None and SubjectType(subject) == SubjectType.CAREGIVER:
            # Caregiver wearable data is private by default.
            kwargs.setdefault("visibility", Visibility.PRIVATE)
        else:
            kwargs.setdefault("visibility", Visibility.CIRCLE)
        super().__init__(**kwargs)
