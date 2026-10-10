# 011 Engagement signal (optional, last)

- **Status:** Draft
- **Owner:**
- **Needs:** 001

## Summary

Detects, from the caregiver's recordings, when they really do not feel like talking, and switches the app to a lighter mode. A secondary use of the audio, not a core function.

## Inputs and outputs

- In: audio features (speech rate, pauses, answer length, energy) compared with the caregiver's own baseline; skipped days.
- Out: `normal` or `low` engagement.

## Acceptance criteria

- **F011-AC1:** Given a baseline, when new audio is analyzed, then an engagement level is returned.
- **F011-AC2:** Given `low`, when the app responds, then it offers a minimal mode (tap-only, at most 2 questions).
- **F011-AC3:** The signal never makes claims about the caregiver's emotions or health.

## Open questions

- Notify a relief contact on repeated `low`?
