"""S3 key layout for stored Observations: `observations/<subject_id>/<YYYY-MM-DD>/<id>.json`.

The date segment comes from the Observation's `timestamp` converted to UTC, so a day prefix
groups every observation whose UTC calendar day matches, regardless of its original offset.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from ..models import Observation

PREFIX = "observations"


def _utc_date(moment: datetime) -> date:
    """The UTC calendar day of an aware datetime."""
    return moment.astimezone(timezone.utc).date()


def observation_key(obs: Observation) -> str:
    """S3 key for one Observation: `observations/<subject_id>/<YYYY-MM-DD>/<id>.json`."""
    return f"{PREFIX}/{obs.subject_id}/{_utc_date(obs.timestamp).isoformat()}/{obs.id}.json"


def subject_prefix(subject_id: str) -> str:
    """Prefix under which every observation for a subject lives (trailing slash included)."""
    return f"{PREFIX}/{subject_id}/"


def day_prefixes(subject_id: str, start: datetime, end: datetime) -> list[str]:
    """Inclusive list of day prefixes `observations/<subject_id>/<date>/` for each UTC day in range.

    `start` and `end` are aware datetimes; their UTC calendar days bound the range inclusively.
    Returns an empty list when `end` precedes `start`.
    """
    first = _utc_date(start)
    last = _utc_date(end)
    prefixes: list[str] = []
    current = first
    while current <= last:
        prefixes.append(f"{PREFIX}/{subject_id}/{current.isoformat()}/")
        current += timedelta(days=1)
    return prefixes
