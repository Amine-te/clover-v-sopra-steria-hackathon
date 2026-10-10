"""HTTP routes for voice reports, mounted under /api/reports.

Endpoints are sync `def`, so FastAPI runs them in its thread pool and blocking AWS polling
never blocks the event loop.
"""

from __future__ import annotations

from pathlib import PurePath
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Request, UploadFile
from fastapi.responses import JSONResponse

from .. import aws
from ..config import ConfigError, Settings, get_settings
from ..models import VoiceReportError, VoiceReportResponse
from .fixtures import FixtureNotFoundError
from .formats import ALLOWED_FORMATS, MAX_AUDIO_BYTES, normalize_ext
from .service import AudioNotFoundError, TranscriptionError, TranscriptResult, UploadError, VoiceService

REPORT_ID_PATTERN = r"^rep-[0-9a-f]{32}$"

DETAIL_UNSUPPORTED = (
    "Format audio non pris en charge. Formats acceptés : " + ", ".join(sorted(ALLOWED_FORMATS)) + "."
)
DETAIL_EMPTY = "Le fichier audio est vide."
DETAIL_TOO_LARGE = "Le fichier audio dépasse 25 Mo."
DETAIL_FIXTURE_NOT_FOUND = "Transcription de démonstration introuvable."
DETAIL_NO_BUCKET = "Configuration incomplète : GAMEDAY_BUCKET n'est pas défini."
DETAIL_UPLOAD_FAILED = "L'enregistrement n'a pas pu être sauvegardé. Veuillez réessayer l'envoi."
DETAIL_TRANSCRIPTION_FAILED = (
    "La transcription a échoué. Votre enregistrement est sauvegardé, vous pouvez réessayer."
)
DETAIL_AUDIO_NOT_FOUND = "Aucun enregistrement trouvé pour ce rapport."

_ERROR_RESPONSES: dict[int | str, dict] = {
    404: {"description": "Not found (French detail)"},
    500: {"description": "Server configuration incomplete (French detail)"},
    502: {"model": VoiceReportError, "description": "Upload or transcription failed"},
}

router = APIRouter(prefix="/reports", tags=["reports"])


def get_settings_dep(request: Request) -> Settings:
    """Settings of the running app (set by create_app); falls back to the process settings."""
    settings = getattr(request.app.state, "settings", None)
    return settings if isinstance(settings, Settings) else get_settings()


def get_voice_service(settings: Annotated[Settings, Depends(get_settings_dep)]) -> VoiceService:
    """Build the VoiceService with S3 and Transcribe clients from the AWS client factory."""
    return VoiceService(settings, aws.client("s3", settings), aws.client("transcribe", settings))


VoiceServiceDep = Annotated[VoiceService, Depends(get_voice_service)]


def _to_response(result: TranscriptResult) -> VoiceReportResponse:
    return VoiceReportResponse(
        report_id=result.report_id,
        audio_s3_key=result.audio_s3_key,
        transcript=result.transcript,
        source=result.source,
    )


def _error(report_id: Optional[str], key: Optional[str], detail: str, retryable: bool) -> JSONResponse:
    body = VoiceReportError(report_id=report_id, audio_s3_key=key, detail=detail, retryable=retryable)
    return JSONResponse(status_code=502, content=body.model_dump())


def _run(action) -> VoiceReportResponse | JSONResponse:
    """Run a service call and map its errors to HTTP responses."""
    try:
        return _to_response(action())
    except FixtureNotFoundError:
        raise HTTPException(status_code=404, detail=DETAIL_FIXTURE_NOT_FOUND) from None
    except AudioNotFoundError:
        raise HTTPException(status_code=404, detail=DETAIL_AUDIO_NOT_FOUND) from None
    except ConfigError:
        raise HTTPException(status_code=500, detail=DETAIL_NO_BUCKET) from None
    except UploadError as exc:
        return _error(exc.report_id, None, DETAIL_UPLOAD_FAILED, retryable=False)
    except TranscriptionError as exc:
        return _error(exc.report_id, exc.audio_s3_key, DETAIL_TRANSCRIPTION_FAILED, retryable=True)


@router.post("/voice", response_model=VoiceReportResponse, responses=_ERROR_RESPONSES)
def submit_voice_report(
    service: VoiceServiceDep,
    audio: Annotated[UploadFile, File(description="Recording (mp3, mp4, m4a, wav, flac, ogg, webm), max 25 MB")],
    fixture: Annotated[Optional[str], Form(description="Cached mode only: fixture transcript name")] = None,
):
    """Store a voice report in S3 and return its French transcript (or a fixture in cached mode)."""
    ext = normalize_ext(PurePath(audio.filename or "").suffix)
    if ext not in ALLOWED_FORMATS:
        raise HTTPException(status_code=415, detail=DETAIL_UNSUPPORTED)
    data = audio.file.read(MAX_AUDIO_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail=DETAIL_EMPTY)
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail=DETAIL_TOO_LARGE)
    return _run(lambda: service.submit(data, ext, audio.content_type, fixture))


@router.post("/{report_id}/transcribe", response_model=VoiceReportResponse, responses=_ERROR_RESPONSES)
def retry_transcription(
    service: VoiceServiceDep,
    report_id: Annotated[str, Path(pattern=REPORT_ID_PATTERN)],
):
    """Transcribe again the audio already stored for `report_id` (no new upload)."""
    return _run(lambda: service.retry(report_id))
