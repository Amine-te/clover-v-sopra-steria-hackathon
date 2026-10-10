# 004 Timeline store

- **Status:** Draft
- **Owner:**
- **Needs:** 000

## Summary

Stores Observations and returns them in time order for the UI, routing and reports.

## Inputs and outputs

- In: Observations.
- Out: queries by period, category and severity.

## Acceptance criteria

- **F004-AC1:** Given Observations, when saved, then each is stored as one JSON object in S3.
- **F004-AC2:** Given a period, when queried, then Observations come back ordered by `timestamp`.
- **F004-AC3:** A generator produces 30 days of fictional Observations and matching wearable samples for demos and tests.

## Open questions

- Is a local index needed, or is listing S3 fast enough?
