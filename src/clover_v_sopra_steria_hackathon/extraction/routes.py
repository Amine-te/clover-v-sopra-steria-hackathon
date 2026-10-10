"""HTTP route for fact extraction, mounted under /api/reports.

The endpoint is a sync `def`, so FastAPI runs the blocking Bedrock Converse call in its thread
pool and never blocks the event loop.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from .. import aws
from ..config import Settings, get_settings
from ..models import ExtractRequest, ExtractResponse
from .service import ExtractionError, ExtractionRequest, ExtractionService

DETAIL_EMPTY = "Le texte de la transcription est vide."
DETAIL_FAILED = "L'extraction des faits a échoué. Veuillez réessayer."

router = APIRouter(prefix="/reports", tags=["reports"])


def get_settings_dep(request: Request) -> Settings:
    """Settings of the running app (set by create_app); falls back to the process settings."""
    settings = getattr(request.app.state, "settings", None)
    return settings if isinstance(settings, Settings) else get_settings()


def get_extraction_service(settings: Annotated[Settings, Depends(get_settings_dep)]) -> ExtractionService:
    """Build the ExtractionService with a bedrock-runtime client from the AWS client factory."""
    return ExtractionService(settings, aws.client("bedrock-runtime", settings))


ExtractionServiceDep = Annotated[ExtractionService, Depends(get_extraction_service)]


@router.post("/extract", response_model=ExtractResponse)
def extract_observations(service: ExtractionServiceDep, body: ExtractRequest) -> ExtractResponse:
    """Extract Observations from a French transcript. Empty transcript → 422; model error → 502."""
    if not body.transcript.strip():
        raise HTTPException(status_code=422, detail=DETAIL_EMPTY)
    request = ExtractionRequest(
        transcript=body.transcript,
        subject_id=body.subject_id,
        reported_by=body.reported_by,
        reported_at=body.resolved_reported_at(),
    )
    try:
        observations = service.extract(request)
    except ExtractionError:
        raise HTTPException(status_code=502, detail=DETAIL_FAILED) from None
    return ExtractResponse(observations=observations, count=len(observations))
