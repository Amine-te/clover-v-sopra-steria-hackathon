# 002 Fact extraction

Turns a French transcript into a list of validated Observations about the cared-for person. It is the second piece of the end-to-end slice (record → transcript → **extract** → timeline). Spec: [002 Fact extraction](../../specs/features/002-extraction.md); detailed requirements and design in `.kiro/specs/extraction/`.

Extraction calls Amazon Bedrock (Claude Haiku 4.5, the `BEDROCK_MODEL_EXTRACT` model) once through the Converse API with a strict-JSON prompt, then post-processes the result: it assigns the authoritative fields from the request, enforces grounding, and validates every item against the Observation contract (`specs/contracts/observation.md`).

## What was set up

- `extraction/` package:
  - `prompt.py`: `SYSTEM_PROMPT` and `build_messages(transcript)`. The prompt instructs the model to return **only** a JSON array; each object has `category`, `value` (plain French factual words), `severity`, `confidence`, `transcript_span` (words copied verbatim from the transcript) and an optional `event_time`. It states facts only — never a diagnosis, cause, interpretation or treatment advice — and never invents fields.
  - `parse.py`: `extract_json_array(text)` recovers the array whether the model returns a bare array, a ```json fenced block, or an array embedded in prose (first `[` to its matching `]`, respecting quoted strings). Raises `ExtractionError` when nothing parses.
  - `service.py`: `ExtractionRequest`, `ExtractionError` (message + optional `aws_code`) and `ExtractionService(settings, bedrock=None, *, max_tokens=2000, temperature=0.0)`. `extract(req)` makes one Converse call (`temperature=0.0`, bounded `maxTokens`, `modelId` read only from `settings.bedrock_model_extract`) and post-processes each item.
  - `routes.py`: `POST /api/reports/extract`, a sync endpoint so the blocking Bedrock call runs in FastAPI's thread pool.
- `models.py`: `ExtractRequest` and `ExtractResponse` (both `extra="forbid"`).
- `api.py`: the extraction router is included under `/api` alongside the voice router; `GET /health` stays the only route outside `/api`.
- Frontend: on `/report-voice`, after a transcript is shown, an "Analyser les faits" button runs extraction with the fixed demo IDs (`subject-demo-1` / `caregiver-demo-1`) and lists the facts in French as `[severity] catégorie — value`. Loading and error text appear in the existing `aria-live="polite"` region. API call in `frontend/src/lib/api.ts` (`extractObservations`).
- Tests: `tests/test_extraction_parse.py`, `test_extraction_service.py`, `test_extraction_golden.py`, `test_extraction_api.py` (all offline, with a fake Bedrock client) and `test_extraction_live.py` (real Converse, marked `aws_live`).
- Fixtures: `tests/fixtures/transcripts/` now holds six fictional French transcripts (`default`, `chute`, `refus-traitement`, `agite-nuit`, `rien-a-signaler`, `vacances-informal`); `tests/fixtures/golden/` holds one golden case per fixture (expected categories, key facts, and a canned Converse response) used by the offline golden test.

### The strict-JSON prompt and the grounding rule

The model only proposes facts. The service owns everything that matters for correctness:

- **Authoritative fields come from the request, not the model:** `id = obs-<12 hex>` (unique within the result), `subject_id`, `reported_by`, `reported_at`, and `source = caregiver_voice`. `timestamp` is the model's `event_time` only when it is a valid timezone-aware datetime, otherwise `reported_at`.
- **Grounding is enforced in code:** every `caregiver_voice` observation whose `transcript_span` is not a substring of the transcript — compared case-insensitively after collapsing internal whitespace — is dropped. This guarantees F002-AC2 regardless of what the model returns.
- **Lenient per item, strict per field:** `confidence` is clamped to `[0, 1]`; an unknown `category` defaults to `logistics` and an unknown `severity` to `info`; each item is then validated against the Observation model and silently dropped if it still fails. The whole call only fails (`ExtractionError` → HTTP 502) when the response cannot be parsed into a JSON array or Bedrock itself errors.
- An empty transcript or an empty array returns `[]` without error.

Diagnosis avoidance lives in the prompt for now; the Bedrock Guardrail (feature 006) will wrap this later. The live test asserts no diagnosis keyword appears in any `value`.

## Configuration

Variables in the root `.env` (see `.env.example`):

| Variable | Use in this step |
| --- | --- |
| `BEDROCK_MODEL_EXTRACT` | Bedrock inference-profile ID for extraction. Default `us.anthropic.claude-haiku-4-5-20251001-v1:0`. |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` | Credentials and region for the `bedrock-runtime` client. If a key is empty, boto3's default chain is used (for example `AWS_PROFILE`). |

### IAM permissions

The IAM user or role behind the credentials needs `bedrock:InvokeModel` (and `bedrock:InvokeModelWithResponseStream`) on both the inference profile and the underlying foundation model ARN for Claude Haiku 4.5. This is the same `KarisBedrockInvoke` policy described in [000 Project foundations](000-project-foundations.md) under "Manual AWS configuration". Example (replace `<ACCOUNT_ID>`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "KarisBedrockInvoke",
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      "Resource": [
        "arn:aws:bedrock:us-east-1:<ACCOUNT_ID>:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0"
      ]
    }
  ]
}
```

Claude Haiku 4.5 must also be enabled in **Model access** in the Bedrock console (region us-east-1). If the live test fails with `AccessDeniedException` or `You don't have access to the model`, redo the Bedrock model-access and IAM steps in [000 Project foundations](000-project-foundations.md).

## Run the backend

From the project root:

```bash
uv run clover-api
```

The API listens on `http://127.0.0.1:8000`. Interactive docs, including the new endpoint: `http://127.0.0.1:8000/docs`.

## Run the frontend

From `frontend/`:

```bash
npm run dev
```

Open `http://localhost:3000/report-voice`, obtain a transcript (record, upload, or cached mode), then click "Analyser les faits": the extracted facts appear under "Faits extraits".

## API reference

### `POST /api/reports/extract`

JSON body: `transcript` (required, non-empty after trimming), `subject_id` (required), `reported_by` (required), `reported_at` (optional ISO 8601 aware datetime; defaults to now in UTC). Unknown fields are rejected (422).

```bash
curl -s -X POST http://127.0.0.1:8000/api/reports/extract \
  -H "Content-Type: application/json" \
  -d '{"transcript":"Ce matin maman a bien dormi et elle a pris ses médicaments du matin.","subject_id":"subject-demo-1","reported_by":"caregiver-demo-1"}'
```

```json
{"observations":[{"id":"obs-9090f4577f9b","timestamp":"2026-10-10T23:43:15.215301Z","reported_at":"2026-10-10T23:43:15.215301Z","subject_id":"subject-demo-1","category":"sleep","value":"A bien dormi ce matin","severity":"info","source":"caregiver_voice","reported_by":"caregiver-demo-1","confidence":0.95,"transcript_span":"Ce matin maman a bien dormi"},{"id":"obs-043cd53636a3","timestamp":"2026-10-10T23:43:15.215301Z","reported_at":"2026-10-10T23:43:15.215301Z","subject_id":"subject-demo-1","category":"medication","value":"A pris ses médicaments du matin","severity":"info","source":"caregiver_voice","reported_by":"caregiver-demo-1","confidence":0.95,"transcript_span":"elle a pris ses médicaments du matin"}],"count":2}
```

### Errors

| Situation | HTTP | Body |
| --- | --- | --- |
| Empty or whitespace-only transcript | 422 | `{"detail": "Le texte de la transcription est vide."}` |
| Missing required field or unknown field | 422 | FastAPI validation error |
| Model, parsing or Bedrock error | 502 | `{"detail": "L'extraction des faits a échoué. Veuillez réessayer."}` |

## Run the tests

Unit tests (offline, fake Bedrock client, no network). From the project root:

```bash
uv run pytest
```

Live test, the real Converse call with Claude Haiku 4.5 on the `default` fixture (a fraction of a cent). From the project root:

```bash
uv run pytest --aws-live -s tests/test_extraction_live.py
```

## Verify

1. Start the backend (`uv run clover-api`) and run the `curl` above: the response is a `{observations, count}` object and every `transcript_span` is a substring of the transcript you sent.
2. Send an empty transcript and confirm HTTP 422 with the French detail:

   ```bash
   curl -s -w "\nHTTP %{http_code}\n" -X POST http://127.0.0.1:8000/api/reports/extract \
     -H "Content-Type: application/json" \
     -d '{"transcript":"   ","subject_id":"subject-demo-1","reported_by":"caregiver-demo-1"}'
   ```

3. Start the frontend (`npm run dev` from `frontend/`), open `/report-voice`, obtain a transcript and click "Analyser les faits": the facts render under "Faits extraits".

## Known gaps

- Diagnosis avoidance relies on the prompt and the grounding rule only; the Bedrock Guardrail that will wrap this is deferred to feature 006.
- Observations are not stored yet (feature 004) and gap questions are not asked (feature 003); this step only returns the facts.
- Extraction is a single synchronous Converse call; there is no retry or batching, and the request waits for the model (client timeout 60 s).
- No authentication: anyone who can reach the API can trigger (billable) Bedrock calls. The API binds to `127.0.0.1` by default; keep it local until auth is added.
