# 000 Foundations

- **Status:** Draft
- **Owner:**
- **Needs:** none

## Summary

Everything the other features rely on: working AWS access, confirmed models, the shared models from `contracts/`, and the package layout.

## Inputs and outputs

- In: AWS keys, the cloned sample scripts.
- Out: `config.py`, `models.py`, package layout from `architecture.md`, updated `.env.example`.

## Acceptance criteria

- **F000-AC1:** Given valid keys, when the four sample scripts run, then each succeeds.
- **F000-AC2:** Given the configured models, when one test call is made to each, then both Haiku 4.5 and Sonnet 4 answer (inference profile IDs resolved if needed).
- **F000-AC3:** Given `contracts/`, when `models.py` is imported, then Observation and WearableSample validate the examples in the contracts.
- **F000-AC4:** `.env.example` lists every variable in `contracts/config.md`.

## Open questions

- Inference profile IDs for Claude models (see `open-questions.md`, 4).
