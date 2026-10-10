# Karis build docs

Each build step of Karis is documented in `docs/steps/`: what was set up, how to run it, and how to verify it.

## Steps

1. [000 Project foundations](steps/000-project-foundations.md): backend skeleton, config, shared models, minimal frontend, env templates.

## Convention

- One file per step: `docs/steps/NNN-<feature-name>.md`.
- `NNN` is a three-digit, zero-padded step number, incremented by 1 for each new step (`000`, `001`, `002`, ...).
- `<feature-name>` is lowercase kebab-case (for example `voice-capture`).
- The first line of a step doc is a level-1 heading with the step number and the feature name.
- Every new step doc needs a new entry in the list above, in ascending step order.
- Never write credential values in these docs. Refer to credentials by environment variable name or by the placeholders used in `.env.example`.
