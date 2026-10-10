# 006 Guardrails

- **Status:** Draft
- **Owner:**
- **Needs:** 000

## Summary

Blocks diagnosis-like content in everything the LLM produces before it is stored or sent.

## Inputs and outputs

- In: any LLM output.
- Out: the output unchanged, or neutral replacement text plus a flag.

## Acceptance criteria

- **F006-AC1:** Given a Bedrock Guardrail with a denied topic for diagnosis and treatment, when it is configured, then its ID and version are in config.
- **F006-AC2:** Given output containing a diagnosis, when checked, then it is replaced with neutral wording and flagged.
- **F006-AC3:** Given adversarial inputs (e.g. the caregiver names a disease stage), when processed, then no stored fact or message states a diagnosis.

## Open questions

- Block, or mask only the offending part?
