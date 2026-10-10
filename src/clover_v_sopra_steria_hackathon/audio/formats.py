"""Accepted audio formats, their Transcribe MediaFormat, and the upload size limit."""

from __future__ import annotations

ALLOWED_FORMATS: frozenset[str] = frozenset({"mp3", "mp4", "m4a", "wav", "flac", "ogg", "webm"})

# Transcribe has no "m4a" MediaFormat; m4a files are MPEG-4 audio.
_MEDIA_FORMAT_OVERRIDES = {"m4a": "mp4"}

MAX_AUDIO_BYTES = 25 * 1024 * 1024


def normalize_ext(ext: str) -> str:
    """Lowercase an extension and drop any leading dot ("." + "MP3" -> "mp3")."""
    return ext.strip().lower().lstrip(".")


def media_format(ext: str) -> str:
    """Return the Transcribe MediaFormat for an allowed extension; raise ValueError otherwise."""
    ext = normalize_ext(ext)
    if ext not in ALLOWED_FORMATS:
        raise ValueError(f"unsupported audio format: {ext!r}")
    return _MEDIA_FORMAT_OVERRIDES.get(ext, ext)
