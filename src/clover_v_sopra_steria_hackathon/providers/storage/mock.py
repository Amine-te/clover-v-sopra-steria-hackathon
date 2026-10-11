"""Deterministic local mock object storage (stand-in for S3).

Data lives only for the process lifetime — fine for tests and the local demo.
The registry returns a cached singleton so objects persist between calls
within a process.
"""

import hashlib
from pathlib import Path

from ..base import ObjectStorageProvider


class MockObjectStorageProvider:
    def __init__(self, root: str | Path = ".data/audio") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put_audio(self, *, data: bytes, content_type: str) -> str:
        digest = hashlib.sha256(data).hexdigest()[:16]
        key = f"mock-audio/{digest}"
        (self.root / key.replace("/", "_")).write_bytes(data)
        return key

    def get_bytes(self, *, object_key: str) -> bytes:
        try:
            return (self.root / object_key.replace("/", "_")).read_bytes()
        except FileNotFoundError:
            raise KeyError(f"Object not found: {object_key}") from None


# Satisfies the protocol statically.
_: ObjectStorageProvider = MockObjectStorageProvider()
