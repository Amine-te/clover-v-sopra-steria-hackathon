# 007 Doctor report

- **Status:** Draft
- **Owner:**
- **Needs:** 004, 006

## Summary

Builds a factual, chronological report for the last n days or months from stored Observations and the cared-for person's bracelet data.

## Inputs and outputs

- In: a period, Observations, wearable samples (`contracts/wearable-sample.md`).
- Out: an HTML and PDF report.

## Acceptance criteria

- **F007-AC1:** Given a period, when the report runs, then it uses only Observations and wearable samples inside it.
- **F007-AC2:** Given the data, when summarized, then the text is a factual chronology with no diagnosis (guardrail applied).
- **F007-AC3:** Every line in the report links back to Observation IDs or to wearable data.
- **F007-AC4:** Given the 30-day synthetic data, when requested, then HTML and PDF files are produced.

## Open questions

- Charts for sleep and heart rate in the first version?
