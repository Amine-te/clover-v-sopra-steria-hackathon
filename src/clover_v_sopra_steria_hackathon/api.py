"""Backend entry point: FastAPI application serving the Next.js frontend."""

from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .audio.routes import router as voice_router
from .config import Settings, get_settings
from .extraction.routes import router as extraction_router
from .store.routes import router as store_router

PACKAGE_NAME = "clover-v-sopra-steria-hackathon"
APP_VERSION = version(PACKAGE_NAME)


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Build the API. Tests inject `settings`; otherwise the cached process settings are used."""
    settings = settings or get_settings()

    app = FastAPI(title="Karis API", version=APP_VERSION)

    # Exact-match allow-list from CORS_ORIGINS; the wildcard is never used.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        """Liveness check used by the frontend; makes no AWS call."""
        return {
            "status": "ok",
            "version": APP_VERSION,
            "notify_channel": settings.notify_channel,
        }

    # Route dependencies read the settings of this app instance (see audio.routes.get_settings_dep).
    app.state.settings = settings

    # Every feature route is registered under /api.
    api_router = APIRouter(prefix="/api")
    api_router.include_router(voice_router)
    api_router.include_router(extraction_router)
    api_router.include_router(store_router)
    app.include_router(api_router)

    return app


app = create_app()


def run() -> None:
    """Start the API with auto-reload on API_HOST / API_PORT (`uv run clover-api`)."""
    settings = get_settings()
    uvicorn.run(
        "clover_v_sopra_steria_hackathon.api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        reload_dirs=[str(Path(__file__).resolve().parent)],
    )
