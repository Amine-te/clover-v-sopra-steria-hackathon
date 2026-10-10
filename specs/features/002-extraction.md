# 002 Fact extraction

- **Status:** Done
- **Owner:**
- **Needs:** 000

## Summary

Turns a transcript into a list of Observations about the cared-for person.

## Inputs and outputs

- In: transcript text, report time, caregiver and subject IDs.
- Out: a list of Observations (`contracts/observation.md`).

## Acceptance criteria

- **F002-AC1:** Given a fixture transcript, when extraction runs, then the output is valid JSON matching the Observation contract.
- **F002-AC2:** Given a transcript, when extraction runs, then every Observation has a `transcript_span` found in the transcript.
- **F002-AC3:** Given a transcript with venting or emotion, when extraction runs, then no Observation states a diagnosis or interpretation.
- **F002-AC4:** Fixtures in `tests/fixtures/` cover at least 6 fictional transcripts of varied quality.

## Decisions

- Single Converse call returning a JSON array (not one call per category): cheaper and keeps every fact in one context. Grounding and validation are enforced in code, so a single call does not weaken correctness.
