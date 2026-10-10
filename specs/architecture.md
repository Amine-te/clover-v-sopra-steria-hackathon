# Architecture (v0)

Summary of the technical architecture.

## Daily flow

```
Caregiver voice ──► S3 + AWS Transcribe (fr-FR) ──► transcript
                                                      │
                          Strands agent (tools wrap each step)
                           1. extract facts      Bedrock Haiku 4.5  → Observations
                           2. find gaps          checklist + Haiku  → ≤ 3 follow-ups → caregiver → re-extract
                           3. guardrail check    Bedrock Guardrails
                           4. route and write    routing matrix + Haiku → messages
                                                      │
                           ┌──────────────────────────┴───────────┐
                     Timeline store (S3 JSON)               Messages (mock SMS / email)
                           │
                     Timeline view (Next.js / React)
```

Extraction, gap questions, guardrail, and routing run in that order. Missing facts send the caregiver a short follow-up before anything is stored or sent.

## Report flow

```
Request (last n days or months)
  + Timeline store (observations in the period)
  + Bracelet data of the cared-for person (simulated at first)
        │
   Strands tool: merge by date (code) → summarize (Bedrock Sonnet 4) → guardrail → render HTML/PDF → doctor report
```

The report reads stored facts and bracelet data for the chosen period; it never needs the original audio.

## Which service does what

| Service | Used for |
| --- | --- |
| AWS Transcribe | French speech to text (fr-FR) |
| Bedrock, Claude Haiku 4.5 | Fact extraction, follow-up wording, message wording, agent decisions |
| Bedrock, Claude Sonnet 4 | Monthly/doctor report chronology |
| Bedrock Guardrails | Blocking diagnosis-like content on every LLM output |
| S3 | Audio files, observation JSON |
| Strands Agents | Orchestrates the steps as tools |
| AgentCore | Optional hosting of the agent (last) |
| Next.js (React) | Web UI |

## Package layout (target)

```
src/clover_v_sopra_steria_hackathon/
  config.py            settings from .env (contracts/config.md)
  models.py            Pydantic models from contracts/
  audio/               capture, S3 upload, Transcribe, cached-transcript fallback
  extraction/          extract_observations, checklist, find_gaps
  store/               timeline store, synthetic data generator
  routing/             matrix, message writing, notifier (mock + real)
  guardrails/          Bedrock Guardrail client and wrapper
  reports/             merge, summarize, render
  wearable/            simulated bracelet data
  agent/               Strands tools and agent, deterministic pipeline
  signals/             optional engagement signal
  api.py               backend entry point (serves the frontend)
frontend/
  (Next.js / React)    caregiver UI, timeline view, follow-ups, report download
tests/
  fixtures/            fictional transcripts and expected observations
```

The optional engagement signal would read the same audio as the daily flow and is not shown in the flow above.

## Build order

Milestones are ordered, not dated. Each one ends in something demoable.

1. **Foundations (000):** samples run, schemas agreed, model IDs confirmed. Everyone is blocked until this is done.
2. **First end-to-end slice (001, 002, 004, 010):** record audio → transcript → extract → timeline. UI can start on mock data in parallel.
3. **Completeness loop (003):** gap detection and follow-up questions on top of the slice.
4. **Routing and guardrails (005, 006):** recipient matrix, mock messages, guardrail on every output, end-of-day reminder.
5. **Doctor report (007):** generated from the 30-day synthetic timeline.
6. **Agent orchestration (009):** wrap the working steps as Strands tools; keep the deterministic pipeline as fallback.
7. **Optional (011, then 012):** engagement signal first, AgentCore deployment last.

Rule: a step is done only when its output can be shown live in the UI.
