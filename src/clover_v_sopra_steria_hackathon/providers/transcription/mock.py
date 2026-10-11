"""Deterministic mock transcription provider (stand-in for AWS Transcribe)."""

from ..base import TranscriptResult


class MockTranscriptionProvider:
    def transcribe(
        self, *, audio_object_key: str, language: str = "fr-FR"
    ) -> TranscriptResult:
        return TranscriptResult(
            text=(
                "Maman était plus fatiguée aujourd’hui. Elle a pris son traitement "
                "mais elle n’a presque rien mangé. Sophie passe ce soir. Moi je suis "
                "vraiment crevé."
            ),
            language=language,
            provider="mock-transcribe",
        )
