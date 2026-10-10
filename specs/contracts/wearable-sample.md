# Contract: Wearable sample

One reading from the cared-for person's bracelet. Simulated at first (no real device integration).

| Field | Type | Notes |
| --- | --- | --- |
| `timestamp` | ISO 8601 datetime | |
| `subject_id` | string | Same as in Observation |
| `heart_rate_bpm` | integer | Optional |
| `sleep_state` | enum | `awake`, `light`, `deep`; optional |
| `spo2_pct` | number | Blood oxygen %; optional |
| `steps` | integer | Step count for the reading window; optional |

## Rules

- The simulator produces consistent data for the same 30-day demo period as the synthetic observations.
- Wearable data is stored and shown as measured facts, separate from caregiver-reported ones.
- A reading with no optional fields is valid. Omit fields that have no value rather than setting them to null.
- `source` in any derived Observation is always `wearable`.
