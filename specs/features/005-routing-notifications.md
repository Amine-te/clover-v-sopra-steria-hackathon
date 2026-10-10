# 005 Routing and notifications

- **Status:** Draft
- **Owner:**
- **Needs:** 002, 004

## Summary

Sends each recipient the observations they should get, with wording written for them.

## Inputs and outputs

- In: new Observations, `contracts/routing-matrix.md`.
- Out: one message per recipient, delivered through the configured channel.

## Acceptance criteria

- **F005-AC1:** Given Observations, when routed, then each recipient gets exactly the categories the matrix allows.
- **F005-AC2:** Given an `urgent` Observation, when routed, then it is sent immediately to the matrix recipients.
- **F005-AC3:** Given `NOTIFY_CHANNEL=mock`, when messages are sent, then they appear in the UI and in a log.
- **F005-AC4:** Every sent message records the Observation IDs it came from.

## Open questions

- Real channel: SMS, email or Telegram (see `open-questions.md`, 2).
