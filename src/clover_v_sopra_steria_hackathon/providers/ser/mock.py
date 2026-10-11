"""Deterministic mock speech-emotion provider for M5."""

from ..base import VocalAffectResult


class MockSpeechEmotionProvider:
    def analyze(self, *, audio_object_key: str) -> VocalAffectResult | None:
        return VocalAffectResult(
            valence="negative",
            arousal="high",
            top_label="tension_like",
            confidence=0.61,
            quality="good",
            model_version="demo-ser-v1",
            visibility="private",
            provider="mock-ser",
        )
