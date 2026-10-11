"""WeeklyReport — a shareable synthesis built from FINALIZED entries only."""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base
from .mixins import CreatedAtMixin, IdMixin


class WeeklyReport(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "weekly_reports"

    recipient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("care_recipients.id"), index=True
    )
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    title: Mapped[str] = mapped_column(String(200), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_entry_count: Mapped[int] = mapped_column(Integer, default=0)
    structured_item_count: Mapped[int] = mapped_column(Integer, default=0)
    reportable_item_count: Mapped[int] = mapped_column(Integer, default=0)
    excluded_private_count: Mapped[int] = mapped_column(Integer, default=0)
