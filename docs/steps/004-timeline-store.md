# 004 Timeline store

Persists Observations as individual JSON objects in S3 and reads them back in time order, filtered by period, category and severity. It is the last piece of the end-to-end slice (record → transcript → extract → **timeline**): the `/report-voice` page can now save extracted facts, and a new `/timeline` page lists them. Spec: [004 Timeline store](../../specs/features/004-timeline-store.md); detailed requirements and design in `.kiro/specs/timeline-store/`.

The step also ships a deterministic generator that produces 30 days of fictional Observations and matching WearableSamples for demos and tests.

## What was set up

- `store/` package:
  - `keys.py`: `observation_key(obs)`, `subject_prefix(subject_id)`, `day_prefixes(subject_id, start, end)`. The key layout is `observations/<subject_id>/<YYYY-MM-DD>/<id>.json`, where the date segment is the Observation's `timestamp` converted to **UTC**. `day_prefixes` returns the inclusive list of UTC day prefixes in a range.
  - `service.py`: `TimelineStore(settings, s3=None)`, `Period(start, end)` and `StoreError(message, aws_code=None)`.
    - `save(obs)` writes one JSON object (`obs.model_dump_json()`, `Content-Type: application/json`) at its key and returns the key; `save_many(iterable)` returns every key written. A re-save of the same `id`/day overwrites idempotently.
    - `query(subject_id, period=None, category=None, severity=None)` lists objects (paginated `list_objects_v2`), fetches and parses each, filters by inclusive period bounds and the optional category/severity, and returns the Observations sorted by `timestamp` ascending. When a `Period` has both bounds it lists only the day prefixes in range; otherwise it lists the whole subject prefix.
    - A stored object that is not valid Observation JSON is skipped and logged in English — one bad write never breaks a query.
    - The S3 client is built through the `aws.py` factory and can be injected for tests. `ClientError`/`BotoCoreError` are wrapped in `StoreError` carrying the AWS error code; a missing `GAMEDAY_BUCKET` raises `ConfigError`.
  - `generator.py`: `generate(subject_id, reporter_id, days=30, end=None, seed=42) -> SyntheticData` and `seed_store(store, data)`. The generator is deterministic for a given seed (`random.Random(seed)`), produces several Observations per day across categories and severities (including some `watch`/`urgent` `mobility_falls`/`pain`) and four WearableSamples per day (heart rate, sleep state, SpO₂, steps). Every person and identifier is invented.
  - `seed.py`: the `clover-seed` console entry; builds a `TimelineStore` from `get_settings()` and writes the generated demo observations. Importing the module has no side effects.
  - `routes.py`: `POST /api/observations` and `GET /api/timeline` (sync endpoints, so the blocking S3 calls run in FastAPI's thread pool). The `get_store` dependency is overridable in tests.
- `api.py`: the store router is included under `/api` alongside the voice and extraction routers; `GET /health` stays the only route outside `/api`.
- `pyproject.toml`: adds the `clover-seed` script entry.
- Frontend:
  - `src/lib/api.ts`: `saveObservations(list)` and `getTimeline(params)`.
  - `/report-voice`: after extraction, an "Enregistrer dans la chronologie" button POSTs the observations and confirms "N fait(s) enregistré(s)." in the existing `aria-live="polite"` region, then links to the timeline.
  - `src/app/timeline/page.tsx`: on load, GET `/api/timeline?subject_id=subject-demo-1` and renders a French `<ol>` of "date — [severity] catégorie : value"; loading and errors appear in an `aria-live` region.
  - Home page links to `/timeline`.
- Tests: `tests/test_store_keys.py`, `test_store_service.py`, `test_generator.py`, `test_timeline_api.py` (all offline, with a fake in-memory S3 or a stub store) and `tests/test_timeline_store_live.py` (real round trip, marked `aws_live`).

## S3 key layout

```
observations/<subject_id>/<YYYY-MM-DD>/<id>.json
```

- `<subject_id>`: the cared-for person (fictional, e.g. `subject-demo-1`).
- `<YYYY-MM-DD>`: the Observation's `timestamp` in **UTC**. An observation at `2026-10-11T00:30:00+02:00` lands under `2026-10-10/` because that is `22:30` UTC the previous day.
- `<id>`: the Observation `id`.

The body is the Observation's JSON (aware datetimes serialized as ISO 8601 with offset).

## Configuration

| Variable | Use in this step |
| --- | --- |
| `GAMEDAY_BUCKET` | S3 bucket that stores the observation objects. Required for save and query. |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` | Credentials and region for the `s3` client. If a key is empty, boto3's default chain is used (for example `AWS_PROFILE`). |

### IAM permissions

The credentials behind the API and the seed/live tooling need, on `GAMEDAY_BUCKET` and its objects:

- `s3:PutObject` — save observations.
- `s3:GetObject` — read them back in a query.
- `s3:ListBucket` — list objects under a subject or day prefix (paginated).
- `s3:DeleteObject` — clean up objects created by the live test and manual checks.

## Run the backend

From the project root:

```bash
uv run clover-api
```

The API listens on `http://127.0.0.1:8000`. Interactive docs including the new endpoints: `http://127.0.0.1:8000/docs`.

## Run the frontend

From `frontend/`:

```bash
npm run dev
```

Open `http://localhost:3000/report-voice`, obtain a transcript, click "Analyser les faits" then "Enregistrer dans la chronologie", and open `http://localhost:3000/timeline` to see the saved facts in time order.

## API reference

### `POST /api/observations`

JSON body: a list of Observations (each validated against `specs/contracts/observation.md`; unknown fields are rejected). Returns `{saved, keys}`.

```bash
curl -s -X POST http://127.0.0.1:8000/api/observations \
  -H "Content-Type: application/json" \
  -d '[{"id":"obs-demo-1","timestamp":"2026-10-10T08:30:00+02:00","reported_at":"2026-10-10T20:05:00+02:00","subject_id":"subject-demo-1","category":"medication","value":"Traitement du matin non pris","severity":"watch","source":"caregiver_voice","reported_by":"caregiver-demo-1","confidence":0.9,"transcript_span":"il a refusé son traitement"}]'
```

```json
{"saved":1,"keys":["observations/subject-demo-1/2026-10-10/obs-demo-1.json"]}
```

### `GET /api/timeline`

Query parameters: `subject_id` (required), `start`, `end` (ISO 8601 aware datetimes), `category`, `severity` (enum values from the Observation contract). Returns `{observations, count}` ordered by `timestamp`.

```bash
curl -s "http://127.0.0.1:8000/api/timeline?subject_id=subject-demo-1"
curl -s "http://127.0.0.1:8000/api/timeline?subject_id=subject-demo-1&start=2026-10-01T00:00:00%2B00:00&end=2026-10-31T23:59:59%2B00:00&category=medication&severity=watch"
```

### Errors

| Situation | HTTP | Body |
| --- | --- | --- |
| Missing `subject_id` | 422 | FastAPI validation error |
| Bad `start`/`end` datetime or bad `category`/`severity` enum | 422 | FastAPI validation error |
| `GAMEDAY_BUCKET` unset | 500 | `{"detail": "Configuration incomplète : GAMEDAY_BUCKET n'est pas défini."}` |
| S3 operation failed | 502 | `{"detail": "L'accès à la chronologie a échoué. Veuillez réessayer."}` |

## Seed demo data

The generator produces 30 days of fictional observations and wearable samples. To write the observations into `GAMEDAY_BUCKET`:

```bash
uv run clover-seed
```

It prints how many observations were written and the subject (`subject-demo-1` by default). The data is deterministic for the default seed, so re-running overwrites the same keys. To use the generator in memory without writing, call `generate()` directly.

## Run the tests

Unit tests (offline, fake S3, no network). From the project root:

```bash
uv run pytest
```

Live round trip (real bucket; creates and then deletes a handful of objects under a unique `subject-live-<uuid>`). From the project root:

```bash
uv run pytest --aws-live -s tests/test_timeline_store_live.py
```

## Verify

1. Start the backend (`uv run clover-api`) and run the `POST /api/observations` curl above, then `GET /api/timeline?subject_id=subject-demo-1`: the saved facts come back ordered by `timestamp`.
2. Send `GET /api/timeline` without `subject_id` and confirm HTTP 422.
3. Delete the demo objects afterward (via `clover-seed`'s cleanup is not automatic, so remove them with the AWS CLI or a short script using the same credentials) so the bucket stays tidy.
4. Start the frontend, open `/report-voice`, extract and save facts, then open `/timeline` and confirm the list renders in time order.

## Known gaps

- **Listing, not an index.** A query lists S3 and fetches every object under the subject (or day) prefix, then filters in memory. This is simple and fast enough for the hackathon's data volume, but it does not scale to very large histories; a per-subject index (e.g. DynamoDB) would be the next step. This resolves the feature's open question — no index is needed yet.
- The generator writes observations only; `seed_store` does not persist WearableSamples (the wearable store is feature 011).
- `clover-seed` does not clean up after itself; it is meant for an obviously-fictional demo subject.
- No authentication: anyone who can reach the API can read or write the timeline. The API binds to `127.0.0.1` by default; keep it local until auth is added.
