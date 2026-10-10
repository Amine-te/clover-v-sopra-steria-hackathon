# Constitution

Rules every feature must respect. If a feature spec conflicts with this file, this file wins.

1. **Product.** Karis records facts about the cared-for person's state, in time order, and sends the right facts to the right people. It is not a personal journal.
2. **Facts, not diagnoses.** Observations describe what happened. Nothing the system stores or sends may state or suggest a diagnosis, treatment or prescription.
3. **Traceability.** Every stored fact links to the transcript words it came from and says who reported it.
4. **Low effort for the caregiver.** Voice first. At most 3 follow-up questions per report. No guilt messages for missed days.
5. **Deterministic routing.** Who receives what is decided by the routing matrix in code. The LLM only writes the wording.
6. **Fictional data only.** Demos, tests and fixtures use invented people. No real patient data anywhere.
7. **No secrets in git.** `.env`, access keys and shared passwords are never committed. Keys are rotated after game day.
8. **Fallbacks for the demo.** Each external dependency has a working fallback: cached transcripts for Transcribe, a mock channel for SMS, simulated bracelet data, a deterministic pipeline for the agent.
9. **Optional never blocks core.** The engagement signal and AgentCore deployment are built last and can be dropped without breaking anything else.
10. **Languages.** User-facing text is French. Code, specs and logs are English.
11. **AWS setup.** Region us-east-1. Model IDs come from configuration, never hard-coded in logic. Default models: Claude Haiku 4.5 for extraction and wording, Claude Sonnet 4 for the report.
