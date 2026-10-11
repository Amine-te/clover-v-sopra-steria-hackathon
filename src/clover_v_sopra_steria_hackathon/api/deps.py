"""Shared FastAPI dependencies (DB session, providers)."""

from ..db.session import get_db
from ..providers.registry import (
    get_llm_provider,
    get_object_storage_provider,
    get_ser_provider,
    get_messaging_provider,
    get_object_storage_provider,
    get_ser_provider,
    get_transcription_provider,
    get_wearable_provider,
)

__all__ = [
    "get_db",
    "get_llm_provider",
    "get_object_storage_provider",
    "get_ser_provider",
    "get_messaging_provider",
    "get_object_storage_provider",
    "get_ser_provider",
    "get_transcription_provider",
    "get_wearable_provider",
]
