# 008 Daily check-in reminder

- **Status:** Draft
- **Owner:**
- **Needs:** 003, 004

## Summary

A friendly end-of-day notification inviting the caregiver to say how the day went, mentioning what is still missing from today's timeline.

## Inputs and outputs

- In: configured time, today's Observations.
- Out: one notification, at most one gentle retry.

## Acceptance criteria

- **F008-AC1:** Given no report today, when `CHECKIN_TIME` arrives, then a short friendly message is sent.
- **F008-AC2:** Given a report already made today, when `CHECKIN_TIME` arrives, then nothing is sent.
- **F008-AC3:** Given unanswered, when an hour has passed, then at most one reminder follows and no more.
- **F008-AC4:** A "send reminder now" button triggers it for demos.

## Open questions

- Scheduler: APScheduler for the demo, EventBridge as target.
