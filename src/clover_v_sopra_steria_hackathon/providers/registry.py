"""Provider registry — selects implementations from environment settings.

Mock providers remain the default. Optional live providers initialize lazily.
"""

from functools import lru_cache

from ..core.config import get_settings
from .base import (
    LLMProvider,
    MessagingProvider,
    ObjectStorageProvider,
    SpeechEmotionProvider,
    TranscriptionProvider,
    WearableProvider,
)
from .llm.mock import MockLLMProvider
from .llm.bedrock import BedrockLLMProvider
from .messaging.mock import MockMessagingProvider
from .ser.mock import MockSpeechEmotionProvider
from .storage.mock import MockObjectStorageProvider
from .storage.s3 import S3ObjectStorageProvider
from .transcription.mock import MockTranscriptionProvider
from .transcription.aws import AWSTranscribeProvider
from .wearables.mock import MockWearableProvider


def _unsupported(kind: str, value: str) -> ValueError:
    return ValueError(
        f"{kind} provider '{value}' is not implemented yet. "
        f"Available for now: 'mock'."
    )


@lru_cache
def get_llm_provider() -> LLMProvider:
    name = get_settings().llm_provider
    if name == "mock":
        return MockLLMProvider()
    if name == "bedrock":
        return BedrockLLMProvider()
    raise ValueError(f"Unknown LLM provider '{name}'. Available: 'mock', 'bedrock'.")


@lru_cache
def get_transcription_provider() -> TranscriptionProvider:
    name = get_settings().stt_provider
    if name == "mock":
        return MockTranscriptionProvider()
    if name == "aws_transcribe":
        return AWSTranscribeProvider()
    raise _unsupported("Transcription", name)


@lru_cache
def get_ser_provider() -> SpeechEmotionProvider:
    name = get_settings().ser_provider
    if name == "mock":
        return MockSpeechEmotionProvider()
    raise _unsupported("SER", name)


@lru_cache
def get_wearable_provider() -> WearableProvider:
    name = get_settings().wearable_provider
    if name == "mock":
        return MockWearableProvider()
    raise _unsupported("Wearable", name)


@lru_cache
def get_object_storage_provider() -> ObjectStorageProvider:
    name = get_settings().object_storage_provider
    if name == "mock":
        return MockObjectStorageProvider()
    if name == "s3":
        return S3ObjectStorageProvider()
    raise _unsupported("Object storage", name)


@lru_cache
def get_messaging_provider() -> MessagingProvider:
    name = get_settings().messaging_provider
    if name == "mock":
        return MockMessagingProvider()
    raise _unsupported("Messaging", name)
