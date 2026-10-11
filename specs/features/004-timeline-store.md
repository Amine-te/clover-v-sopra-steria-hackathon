# 004 Timeline store

- **Status:** Done
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

- ~~Is a local index needed, or is listing S3 fast enough?~~ **Resolved:** no index is needed for now. Queries list S3 under the subject (or day) prefix with pagination, then fetch and filter in memory — simple and fast enough for the hackathon's data volume. A per-subject index is noted as a future scaling step in `docs/steps/004-timeline-store.md`.
