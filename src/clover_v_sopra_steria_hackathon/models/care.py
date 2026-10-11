"""Care recipient and care circle membership (a user's role within a circle)."""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from .enums import Role, pg_enum
from .mixins import CreatedAtMixin, IdMixin
from .user import User


class CareRecipient(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "care_recipients"

    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80), default="")
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(Text, default="")

    members: Mapped[list["CareCircleMember"]] = relationship(
        back_populates="recipient", cascade="all, delete-orphan"
    )


class CareCircleMember(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "care_circle_members"
    __table_args__ = (
        UniqueConstraint("user_id", "recipient_id", name="uq_member_user_recipient"),
    )

    recipient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("care_recipients.id"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[Role] = mapped_column(pg_enum(Role, "role"))
    active: Mapped[bool] = mapped_column(default=True)

    recipient: Mapped[CareRecipient] = relationship(back_populates="members")
    user: Mapped[User] = relationship()
