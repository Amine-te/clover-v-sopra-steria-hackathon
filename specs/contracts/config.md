# Contract: Configuration

All settings come from environment variables (`.env`, never committed) read once in `config.py`.

| Variable | Purpose | Default |
| --- | --- | --- |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Credentials | none |
| `AWS_DEFAULT_REGION` | Region | `us-east-1` |
| `GAMEDAY_BUCKET` | S3 bucket for audio and facts | none |
| `BEDROCK_MODEL_EXTRACT` | Model for extraction, follow-ups, message wording | Claude Haiku 4.5 |
| `BEDROCK_MODEL_REPORT` | Model for the report chronology | Claude Sonnet 4 |
| `GUARDRAIL_ID`, `GUARDRAIL_VERSION` | Bedrock Guardrail | none |
| `TRANSCRIBE_LANGUAGE` | Transcribe language code | `fr-FR` |
| `NOTIFY_CHANNEL` | `mock`, `sns`, `ses` or `telegram` | `mock` |
| `USE_CACHED_TRANSCRIPTS` | Skip Transcribe and use fixtures | `false` |
| `CHECKIN_TIME` | Daily reminder time, local | `20:00` |

`.env.example` must list every variable above with placeholder values.
