# Karis build docs

Each build step of Karis is documented in `docs/steps/`: what was set up, how to run it, and how to verify it.

## Steps

1. [000 Project foundations](steps/000-project-foundations.md): backend skeleton, config, shared models, minimal frontend, env templates.
2. [001 Voice capture](steps/001-voice-capture.md): S3 upload, French batch transcription, cached-transcript fallback, retry, `/report-voice` page.
3. [002 Fact extraction](steps/002-extraction.md): Bedrock Converse with Claude Haiku 4.5, strict-JSON prompt, code-enforced grounding, `POST /api/reports/extract`, "Analyser les faits" on `/report-voice`.
4. [004 Timeline store](steps/004-timeline-store.md): Observations stored as JSON in S3 (`observations/<subject>/<date>/<id>.json`), paginated time-ordered query with period/category/severity filters, deterministic 30-day generator and `clover-seed`, `POST /api/observations` and `GET /api/timeline`, "Enregistrer dans la chronologie" on `/report-voice` and a `/timeline` page.

## Convention

- One file per step: `docs/steps/NNN-<feature-name>.md`.
- `NNN` is a three-digit, zero-padded step number, incremented by 1 for each new step (`000`, `001`, `002`, ...).
- `<feature-name>` is lowercase kebab-case (for example `voice-capture`).
- The first line of a step doc is a level-1 heading with the step number and the feature name.
- Every new step doc needs a new entry in the list above, in ascending step order.
- Never write credential values in these docs. Refer to credentials by environment variable name or by the placeholders used in `.env.example`.
