# Contract: Routing matrix

Decides who receives which observations. Implemented as data in `routing/`, not in prompts. The LLM only writes the wording of each message.

| Category | Auxiliary | Family | Doctor | Caregiver |
| --- | --- | --- | --- | --- |
| `sleep`, `meals_hydration` | yes | daily summary | monthly report | yes |
| `medication` (issue) | immediately | immediately | yes | yes |
| `mobility_falls`, `incident` | immediately | immediately | yes | yes |
| `mood_behavior` | yes | filtered summary | monthly report | yes |
| `pain`, `vitals` | yes | summary | monthly report | yes |
| `appointment` | yes | yes | no | yes |
| `logistics` | yes | no | no | yes |

## Rules

- `severity: urgent` always overrides the table: everyone marked "yes" or higher is notified immediately.
- "Filtered summary" means no raw caregiver words and no frustration or exhaustion content.
- Every sent message records the observation IDs it was built from.
- Draft table: confirm the cells with the team before marking feature 005 `Ready`.

## Recipients

`auxiliary`, `family`, `doctor`, `caregiver`. Contact details are fictional in demos and stored in config.
