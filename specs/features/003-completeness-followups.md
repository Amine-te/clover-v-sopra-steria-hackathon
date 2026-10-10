# 003 Completeness follow-ups

- **Status:** Draft
- **Owner:**
- **Needs:** 002

## Summary

Compares what was reported with a daily checklist and asks the caregiver for the most important missing facts.

## Inputs and outputs

- In: today's Observations.
- Out: up to 3 follow-up questions; new Observations from the answers.

## Acceptance criteria

- **F003-AC1:** Given today's Observations, when gaps are checked, then the missing checklist categories are returned.
- **F003-AC2:** Given more than 3 gaps, when questions are asked, then at most 3 are asked, highest priority first.
- **F003-AC3:** Given an answer, when it is received, then it is extracted into Observations.
- **F003-AC4:** Given the caregiver skips, when they do, then the report completes without the missing facts.

## Defaults

- **Daily checklist categories (default):** `sleep`, `meals_hydration`, `medication`, `mood_behavior`. Confirm with team before marking `Ready` (see `open-questions.md`, 10).
- **Answer modality (default):** in-app text or tap. Voice re-transcription is optional and built on top of this.

## Open questions

- Confirm the priority order when more than 3 gaps exist (higher severity first, or by checklist order?).
