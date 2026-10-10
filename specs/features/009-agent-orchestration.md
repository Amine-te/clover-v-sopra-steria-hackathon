# 009 Agent orchestration

- **Status:** Draft
- **Owner:**
- **Needs:** 001, 002, 003, 005

## Summary

A Strands agent that runs the daily flow by calling each step as a tool.

## Inputs and outputs

- In: a new voice report.
- Out: stored Observations and sent messages.

## Acceptance criteria

- **F009-AC1:** Given a report, when the agent runs, then it calls transcribe, extract, find gaps, guardrail, store and route as tools.
- **F009-AC2:** Given the agent misbehaves, when the fallback flag is set, then a deterministic pipeline runs the same steps in order.
- **F009-AC3:** Given the same fixture, when run through either path, then the stored Observations are equivalent.

## Defaults

- **Agent model:** Claude Haiku 4.5 (`BEDROCK_MODEL_EXTRACT`). Same model as extraction and wording — no second model needed for agent decisions.

## Open questions

- None at this stage. Revisit if the agent proves too slow with Haiku.
