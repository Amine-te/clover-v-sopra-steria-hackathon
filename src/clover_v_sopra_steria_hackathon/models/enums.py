"""Domain enums. Stored in PostgreSQL as lowercase string values (varchar + check)."""

import enum
from typing import Any

import sqlalchemy as sa


class Role(enum.StrEnum):
    PRIMARY_CAREGIVER = "primary_caregiver"
    FAMILY_CAREGIVER = "family_caregiver"
    AUXILIARY = "auxiliary"
    ADMINISTRATIVE_HELPER = "administrative_helper"
    FAMILY_INFORMED = "family_informed"
    MEDICAL_PROFESSIONAL = "medical_professional"


class Visibility(enum.StrEnum):
    PRIVATE = "private"  # author only
    CIRCLE = "circle"  # care circle (filtered per role at routing time)


class JournalStatus(enum.StrEnum):
    DRAFT = "draft"
    ANALYZED = "analyzed"
    PENDING_CLARIFICATION = "pending_clarification"
    FINALIZED = "finalized"


class InputType(enum.StrEnum):
    TEXT = "text"
    VOICE = "voice"


class ActionStatus(enum.StrEnum):
    PENDING = "pending"
    DONE = "done"
    CANCELLED = "cancelled"


class DeliveryStatus(enum.StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    SENT = "sent"
    FAILED = "failed"


class SubjectType(enum.StrEnum):
    CAREGIVER = "caregiver"
    CARE_RECIPIENT = "care_recipient"


def pg_enum(enum_cls: type[enum.Enum], name: str) -> sa.Enum:
    """SQLAlchemy Enum persisting the lowercase *values* (not member names)."""
    return sa.Enum(
        enum_cls,
        name=name,
        native_enum=False,
        length=50,
        validate_strings=True,
        values_callable=lambda e: [m.value for m in e],
    )


__all__ = [
    "ActionStatus",
    "DeliveryStatus",
    "InputType",
    "JournalStatus",
    "Role",
    "SubjectType",
    "Visibility",
    "pg_enum",
]


def _all_values() -> list[Any]:  # pragma: no cover - convenience for debugging
    return [m.value for c in (Role, Visibility, JournalStatus, InputType, ActionStatus, DeliveryStatus, SubjectType) for m in c]
