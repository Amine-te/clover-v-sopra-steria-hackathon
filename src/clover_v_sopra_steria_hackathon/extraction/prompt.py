"""The strict-JSON Converse prompt that turns a French caregiver transcript into fact objects."""

from __future__ import annotations

# Categories the model may use; the service re-validates against the Observation contract.
_CATEGORIES = (
    "sleep, meals_hydration, medication, mood_behavior, mobility_falls, "
    "pain, vitals, incident, appointment, logistics"
)

SYSTEM_PROMPT = f"""You extract factual observations about a cared-for person from a French caregiver's spoken report.

Return ONLY a JSON array (no prose, no markdown, no code fence). Each element is an object with:
- "category": exactly one of [{_CATEGORIES}].
- "value": the observed fact, in plain French factual words (a short sentence or phrase).
- "severity": one of "info", "watch", "urgent".
- "confidence": a number between 0 and 1.
- "transcript_span": the exact words copied verbatim from the transcript the fact comes from.
- "event_time": OPTIONAL, ISO 8601 (e.g. "2026-10-10T08:30:00+02:00"), only when the transcript states a precise time.

Rules:
- State FACTS ONLY. Never output a diagnosis, a cause, an interpretation, or treatment/medical advice.
- Report what was observed or said, not what it might mean. Do not infer illnesses or conditions.
- "transcript_span" must be an exact substring of the transcript, copied word for word.
- Omit any field you are unsure about; never invent information that is not in the transcript.
- Use "urgent" only for clearly serious events (for example a fall with injury), "watch" for things worth monitoring, "info" otherwise.
- If the transcript reports nothing worth recording, return an empty array: [].
"""


def build_messages(transcript: str) -> list:
    """Return the Converse `messages` list carrying the transcript to analyse."""
    return [
        {
            "role": "user",
            "content": [{"text": f"Transcript (French):\n{transcript}"}],
        }
    ]
