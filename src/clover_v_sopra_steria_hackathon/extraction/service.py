"""Turn a transcript into validated Observations via one Bedrock Converse call plus post-processing.

The model proposes facts; this service owns the authoritative fields (ids, subject, reporter,
times, source), enforces grounding (every caregiver_voice span must be in the transcript) and
drops anything that does not validate against the Observation contract. It never trusts the
model for identity or provenance.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from botocore.exceptions import BotoCoreError, ClientError
from pydantic import ValidationError

from .. import aws
from ..config import Settings
from ..models import Category, Observation, Severity
from .parse import ExtractionError, extract_json_array
from .prompt import SYSTEM_PROMPT, build_messages

__all__ = ["ExtractionError", "ExtractionRequest", "ExtractionService"]

logger = logging.getLogger(__name__)

_AWS_ERRORS = (ClientError, BotoCoreError)
_VALID_CATEGORIES = set(Category.__args__)
_VALID_SEVERITIES = set(Severity.__args__)
_DEFAULT_SEVERITY = "info"
_DEFAULT_CATEGORY = "logistics"
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class ExtractionRequest:
    """The inputs to one extraction: the transcript and the authoritative identity fields."""

    transcript: str
    subject_id: str
    reported_by: str
    reported_at: datetime  # timezone-aware


def _normalize(text: str) -> str:
    """Lower-case and collapse internal whitespace, for substring grounding checks."""
    return _WHITESPACE.sub(" ", text).strip().lower()


def _error_code(exc: Exception) -> str:
    if isinstance(exc, ClientError):
        return str(exc.response.get("Error", {}).get("Code", "ClientError"))
    return type(exc).__name__


class ExtractionService:
    """Holds the Bedrock client and settings; `extract` returns the validated Observations."""

    def __init__(
        self,
        settings: Settings,
        bedrock: Any = None,
        *,
        max_tokens: int = 2000,
        temperature: float = 0.0,
    ) -> None:
        self.settings = settings
        self.bedrock = bedrock if bedrock is not None else aws.client("bedrock-runtime", settings)
        self.max_tokens = max_tokens
        self.temperature = temperature

    def extract(self, req: ExtractionRequest) -> list[Observation]:
        """Return the Observations found in the transcript (empty when there is nothing to report)."""
        if not req.transcript.strip():
            return []
        text = self._converse(req.transcript)
        items = extract_json_array(text)
        return self._postprocess(items, req)

    # Internals

    def _converse(self, transcript: str) -> str:
        try:
            response = self.bedrock.converse(
                modelId=self.settings.bedrock_model_extract,
                system=[{"text": SYSTEM_PROMPT}],
                messages=build_messages(transcript),
                inferenceConfig={"maxTokens": self.max_tokens, "temperature": self.temperature},
            )
        except _AWS_ERRORS as exc:
            code = _error_code(exc)
            logger.error("Bedrock Converse failed during extraction: %s", code)
            raise ExtractionError(f"Bedrock error: {code}", aws_code=code) from exc
        content = response.get("output", {}).get("message", {}).get("content", [])
        return "".join(block.get("text", "") for block in content if isinstance(block, dict))

    def _postprocess(self, items: list[dict], req: ExtractionRequest) -> list[Observation]:
        normalized_transcript = _normalize(req.transcript)
        observations: list[Observation] = []
        for raw in items:
            span = str(raw.get("transcript_span", "") or "")
            if not self._is_grounded(span, normalized_transcript):
                logger.debug("Dropped ungrounded observation span")
                continue
            fields = {
                "id": f"obs-{uuid4().hex[:12]}",
                "timestamp": self._resolve_timestamp(raw.get("event_time"), req.reported_at),
                "reported_at": req.reported_at,
                "subject_id": req.subject_id,
                "category": self._valid_category(raw.get("category")),
                "value": str(raw.get("value", "") or ""),
                "severity": self._valid_severity(raw.get("severity")),
                "source": "caregiver_voice",
                "reported_by": req.reported_by,
                "confidence": self._clamp_confidence(raw.get("confidence")),
                "transcript_span": span,
            }
            try:
                observations.append(Observation.model_validate(fields))
            except ValidationError:
                logger.debug("Dropped observation that failed contract validation")
        return observations

    @staticmethod
    def _is_grounded(span: str, normalized_transcript: str) -> bool:
        if not span.strip():
            return False
        return _normalize(span) in normalized_transcript

    @staticmethod
    def _resolve_timestamp(event_time: Any, reported_at: datetime) -> datetime:
        if isinstance(event_time, str) and event_time.strip():
            try:
                parsed = datetime.fromisoformat(event_time.strip())
            except ValueError:
                return reported_at
            if parsed.tzinfo is not None:
                return parsed
        return reported_at

    @staticmethod
    def _valid_category(value: Any) -> str:
        return value if value in _VALID_CATEGORIES else _DEFAULT_CATEGORY

    @staticmethod
    def _valid_severity(value: Any) -> str:
        return value if value in _VALID_SEVERITIES else _DEFAULT_SEVERITY

    @staticmethod
    def _clamp_confidence(value: Any) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.5
        return max(0.0, min(1.0, number))
