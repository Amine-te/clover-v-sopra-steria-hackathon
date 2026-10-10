# Contract: Observation

One fact about the cared-for person. Stored as one JSON object. Implemented as a Pydantic model in `models.py`.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Unique |
| `timestamp` | ISO 8601 datetime | When it happened (not when it was reported) |
| `reported_at` | ISO 8601 datetime | When the report was made |
| `subject_id` | string | The cared-for person (fictional) |
| `category` | enum | `sleep`, `meals_hydration`, `medication`, `mood_behavior`, `mobility_falls`, `pain`, `vitals`, `incident`, `appointment`, `logistics` |
| `value` | string | What was observed, in plain factual words |
| `severity` | enum | `info`, `watch`, `urgent` |
| `source` | enum | `caregiver_voice`, `wearable`, `auxiliary_report` |
| `reported_by` | string | Who said it |
| `confidence` | number 0 to 1 | Certainty of the extraction |
| `transcript_span` | string | Exact words the fact came from; empty for wearable facts |

## Rules

- `value` states facts only. No diagnosis, cause or advice (see `constitution.md`, rule 2).
- Unknown values are omitted, not guessed.
- A fact heard in the transcript always keeps its `transcript_span`.

## Example (fictional)

```json
{
  "id": "obs-0001",
  "timestamp": "2026-10-10T08:30:00+02:00",
  "reported_at": "2026-10-10T20:05:00+02:00",
  "subject_id": "subject-demo-1",
  "category": "medication",
  "value": "Morning treatment not taken",
  "severity": "watch",
  "source": "caregiver_voice",
  "reported_by": "caregiver-demo-1",
  "confidence": 0.9,
  "transcript_span": "il a refusé son traitement ce matin"
}
```
