"""M1 — provider registry resolves mock implementations satisfying the protocols."""

import pytest

from clover_v_sopra_steria_hackathon.providers import registry
from clover_v_sopra_steria_hackathon.providers.base import (
    LLMProvider,
    MessagingProvider,
    ObjectStorageProvider,
    SpeechEmotionProvider,
    TranscriptionProvider,
    WearableProvider,
)


@pytest.mark.parametrize(
    ("getter", "protocol"),
    [
        (registry.get_llm_provider, LLMProvider),
        (registry.get_transcription_provider, TranscriptionProvider),
        (registry.get_ser_provider, SpeechEmotionProvider),
        (registry.get_wearable_provider, WearableProvider),
        (registry.get_object_storage_provider, ObjectStorageProvider),
        (registry.get_messaging_provider, MessagingProvider),
    ],
)
def test_registry_resolves_mock_providers(getter, protocol):
    provider = getter()
    assert isinstance(provider, protocol)
    assert "Mock" in type(provider).__name__


def test_registry_providers_are_cached_singletons():
    assert registry.get_llm_provider() is registry.get_llm_provider()
    assert registry.get_object_storage_provider() is registry.get_object_storage_provider()


def test_mock_object_storage_roundtrip():
    storage = registry.get_object_storage_provider()
    key = storage.put_audio(data=b"fake-audio-bytes", content_type="audio/mpeg")
    assert key.startswith("mock-audio/")
    assert storage.get_bytes(object_key=key) == b"fake-audio-bytes"
