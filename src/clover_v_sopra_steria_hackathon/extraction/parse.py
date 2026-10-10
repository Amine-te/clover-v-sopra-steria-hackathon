"""Pull a JSON array of observation objects out of the model's text output.

The model is asked for a bare array, but it may wrap it in a ```json fence or in prose; this
module recovers the array from any of those shapes and raises ExtractionError when none parses.
"""

from __future__ import annotations

import json
from typing import Optional


class ExtractionError(Exception):
    """Extraction failed. Carries a human message and, for AWS failures, the AWS error code."""

    def __init__(self, message: str, *, aws_code: Optional[str] = None) -> None:
        super().__init__(message)
        self.aws_code = aws_code


def _coerce_array(value: object, source: str) -> list[dict]:
    if not isinstance(value, list):
        raise ExtractionError(f"model output ({source}) is not a JSON array")
    return [item for item in value if isinstance(item, dict)]


def _find_array_span(text: str) -> Optional[str]:
    """Return the substring from the first '[' to its matching ']', respecting strings."""
    start = text.find("[")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def extract_json_array(text: str) -> list[dict]:
    """Parse a JSON array from `text`, handling a bare array, a code fence or array-in-prose.

    Returns the list of object items (non-object elements are dropped). Raises ExtractionError
    when no JSON array can be recovered.
    """
    if text is None:
        raise ExtractionError("model returned no output text")
    stripped = text.strip()
    if not stripped:
        raise ExtractionError("model returned empty output text")

    # 1. Bare JSON array.
    try:
        return _coerce_array(json.loads(stripped), "bare")
    except json.JSONDecodeError:
        pass

    # 2. First '[' ... matching ']' anywhere in the text (covers code fences and prose).
    span = _find_array_span(stripped)
    if span is not None:
        try:
            return _coerce_array(json.loads(span), "embedded")
        except json.JSONDecodeError:
            pass

    raise ExtractionError("could not parse a JSON array from the model output")
