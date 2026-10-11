"""Karis API — FastAPI application factory.

Boot requirements: none beyond this package. No AWS credentials, no running
database are needed to start the app or serve /api/health.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes import demo, health, journal
from .core.config import get_settings
from .providers.llm.bedrock import LLMProviderError


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Karis API", version="0.1.0")

    @app.exception_handler(LLMProviderError)
    async def llm_failure_handler(request, error: LLMProviderError):
        return JSONResponse(status_code=502, content={
            "detail": error.detail,
            "code": error.code,
            "provider_metadata": error.metadata.model_dump() if error.metadata else None,
        })

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api")
    app.include_router(journal.router, prefix="/api")
    app.include_router(demo.router, prefix="/api")
    return app


app = create_app()
