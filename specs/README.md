# Karis specs

Spec-driven development (SDD) for the Karis hackathon project. Specs are the source of truth; code in `src/clover_v_sopra_steria_hackathon/` implements them.

## Workflow

1. **Spec first.** No feature is coded before its spec is `Ready`.
2. **Contracts rule.** `contracts/` holds the shared data shapes. Changing one means updating every feature that uses it, in the same change.
3. **Keep features minimal.** A feature file stays short (summary, inputs/outputs, a few acceptance criteria) until the team marks it `Ready`. Detail is added only when it is needed to build.
4. **Tests trace to specs.** Name tests after acceptance criteria, e.g. `test_f002_ac1_...`.
5. **Mocks are first-class.** Every external dependency has a fallback (see `constitution.md`).

## Status

`Draft` (minimal, may change) → `Ready` (agreed, safe to build) → `Done` (implemented and tested)

## Layout

```
specs/
  README.md             this file
  constitution.md       rules that apply to every feature
  architecture.md       how the pieces fit, package layout
  open-questions.md     decisions the team still has to make
  contracts/            shared data shapes
    observation.md
    routing-matrix.md
    wearable-sample.md
    config.md
  features/             one file per feature, numbered in build order
    _template.md
    000-foundations.md ... 012-agentcore-deploy.md
```

## Feature index

| # | Feature | Workstream | Needs | Owner | Status |
| --- | --- | --- | --- | --- | --- |
| 000 | Foundations | A | none | | Draft |
| 001 | Voice capture and transcription | B | 000 | | Draft |
| 002 | Fact extraction | C | 000 | | Draft |
| 003 | Completeness follow-ups | C | 002 | | Draft |
| 004 | Timeline store | D | 000 | | Draft |
| 005 | Routing and notifications | E | 002, 004 | | Draft |
| 006 | Guardrails | F | 000 | | Draft |
| 007 | Doctor report | G | 004 | | Draft |
| 008 | Daily check-in reminder | E | 003, 004 | | Draft |
| 009 | Agent orchestration | H | 001, 002, 003, 005 | | Draft |
| 010 | UI | I | 000 (mocks first) | | Draft |
| 011 | Engagement signal (optional) | J | 001 | | Draft |
| 012 | AgentCore deployment (optional) | K | 009 | | Draft |

## Using this folder

Copy `specs/` to the repo root. Fill the Owner column in the team meeting. The full architecture document with the build order is in `specs/architecture.md`.
