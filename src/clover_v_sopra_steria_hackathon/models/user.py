"""User — a person who interacts with Karis (caregiver, helper, professional)."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base
from .mixins import CreatedAtMixin, IdMixin


class User(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
