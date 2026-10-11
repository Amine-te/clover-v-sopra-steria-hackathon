"""HTTP routes for the timeline store: save observations and query the timeline.

Endpoints are sync `def`, so FastAPI runs the blocking S3 calls in its thread pool and never
blocks the event loop. Mounted under /api by api.create_app.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict

from .. import aws
from ..config import ConfigError, Settings, get_settings
from ..models import Category, Observation, Severity
from .service import Period, StoreError, TimelineStore

DETAIL_NO_BUCKET = "Configuration incomplète : GAMEDAY_BUCKET n'est pas défini."
DETAIL_STORE_FAILED = "L'accès à la chronologie a échoué. Veuillez réessayer."

router = APIRouter(tags=["timeline"])


class SaveObservationsResponse(BaseModel):
    """Result of saving a batch: how many were written and their S3 keys."""

    model_config = ConfigDict(extra="forbid")

    saved: int
    keys: list[str]


class TimelineResponse(BaseModel):
    """A timeline query result: the matching Observations in time order and their count."""

    model_config = ConfigDict(extra="forbid")

    observations: list[Observation]
    count: int


def get_settings_dep(request: Request) -> Settings:
    """Settings of the running app (set by create_app); falls back to the process settings."""
    settings = getattr(request.app.state, "settings", None)
    return settings if isinstance(settings, Settings) else get_settings()


def get_store(settings: Annotated[Settings, Depends(get_settings_dep)]) -> TimelineStore:
    """Build the TimelineStore with an S3 client from the AWS client factory."""
    return TimelineStore(settings, aws.client("s3", settings))


StoreDep = Annotated[TimelineStore, Depends(get_store)]


def _period(start: Optional[datetime], end: Optional[datetime]) -> Optional[Period]:
    """Turn the optional start/end query params into a Period, or None when both are absent."""
    if start is None and end is None:
        return None
    return Period(start=start, end=end)


@router.post("/observations", response_model=SaveObservationsResponse)
def save_observations(store: StoreDep, observations: list[Observation]) -> SaveObservationsResponse:
    """Save a JSON list of Observations and return the count and keys written."""
    try:
        keys = store.save_many(observations)
    except ConfigError:
        raise HTTPException(status_code=500, detail=DETAIL_NO_BUCKET) from None
    except StoreError:
        raise HTTPException(status_code=502, detail=DETAIL_STORE_FAILED) from None
    return SaveObservationsResponse(saved=len(keys), keys=keys)


@router.get("/timeline", response_model=TimelineResponse)
def get_timeline(
    store: StoreDep,
    subject_id: Annotated[str, Query(min_length=1)],
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    category: Optional[Category] = None,
    severity: Optional[Severity] = None,
) -> TimelineResponse:
    """Return the subject's Observations for the period/filters, ordered by `timestamp`."""
    try:
        observations = store.query(
            subject_id,
            period=_period(start, end),
            category=category,
            severity=severity,
        )
    except ConfigError:
        raise HTTPException(status_code=500, detail=DETAIL_NO_BUCKET) from None
    except StoreError:
        raise HTTPException(status_code=502, detail=DETAIL_STORE_FAILED) from None
    return TimelineResponse(observations=observations, count=len(observations))
