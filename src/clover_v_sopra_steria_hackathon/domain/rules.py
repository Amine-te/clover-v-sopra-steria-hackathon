"""Core business rules shared across the Karis domain."""

from ..models.enums import JournalStatus
from .exceptions import BusinessRuleViolation

__all__ = ["BusinessRuleViolation", "is_report_eligible"]


def is_report_eligible(entry: object) -> bool:
    """Weekly reports are built from FINALIZED journal entries only."""
    return getattr(entry, "status", None) == JournalStatus.FINALIZED
