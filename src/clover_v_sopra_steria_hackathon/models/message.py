"""GeneratedMessage — an AI-drafted message for a care circle member.

Hard rule: a generated message can NEVER be sent unless approved=True.
Sending goes through approve() then mark_sent() — no auto-send path exists.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base
from ..domain.exceptions import BusinessRuleViolation
from .enums import DeliveryStatus, pg_enum
from .mixins import CreatedAtMixin, IdMixin, utcnow


class GeneratedMessage(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "generated_messages"

    recipient_member_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("care_circle_members.id"), index=True
    )
    source_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("journal_entries.id")
    )
    channel: Mapped[str] = mapped_column(String(30), default="inbox")
    text: Mapped[str] = mapped_column(Text)
    approved: Mapped[bool] = mapped_column(default=False)
    delivery_status: Mapped[DeliveryStatus] = mapped_column(
        pg_enum(DeliveryStatus, "delivery_status")
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __init__(self, **kwargs):
        kwargs.setdefault("approved", False)
        kwargs.setdefault("delivery_status", DeliveryStatus.DRAFT)
        super().__init__(**kwargs)

    @property
    def can_send(self) -> bool:
        return self.approved and self.delivery_status == DeliveryStatus.APPROVED

    def approve(self) -> None:
        if self.delivery_status == DeliveryStatus.SENT:
            raise BusinessRuleViolation("A message already sent cannot be approved.")
        self.approved = True
        self.delivery_status = DeliveryStatus.APPROVED

    def mark_sent(self) -> None:
        if not self.approved:
            raise BusinessRuleViolation(
                "A generated message cannot be sent before approval (approved=True)."
            )
        self.delivery_status = DeliveryStatus.SENT
        self.sent_at = utcnow()
