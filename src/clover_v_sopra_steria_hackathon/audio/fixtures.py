"""Fictional French transcripts returned in cached mode (USE_CACHED_TRANSCRIPTS=true)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

# src/clover_v_sopra_steria_hackathon/audio/fixtures.py -> parents[3] is the repository root.
FIXTURES_DIR = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "transcripts"
DEFAULT_FIXTURE = "default"

# Plain names only: no dots or slashes, so a name can never leave FIXTURES_DIR.
_NAME_PATTERN = re.compile(r"^[a-z0-9_-]+$")


class FixtureNotFoundError(Exception):
    """Raised when a fixture name is invalid or matches no transcript file."""

    def __init__(self, name: str) -> None:
        super().__init__(f"fixture transcript not found: {name!r}")
        self.name = name


def load_fixture(name: Optional[str] = None) -> str:
    """Return the text of `<name>.txt` (default `default.txt`), stripped of surrounding whitespace."""
    name = DEFAULT_FIXTURE if name is None or not name.strip() else name.strip()
    if not _NAME_PATTERN.fullmatch(name):
        raise FixtureNotFoundError(name)
    path = FIXTURES_DIR / f"{name}.txt"
    if not path.is_file():
        raise FixtureNotFoundError(name)
    return path.read_text(encoding="utf-8").strip()
