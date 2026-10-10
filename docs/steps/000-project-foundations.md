# 000 Project foundations

Skeleton of Karis: no business logic yet, only the pieces every later feature plugs into. Specs: [000 Foundations](../../specs/features/000-foundations.md) and the skeleton part of [010 UI](../../specs/features/010-ui.md).

## What was set up

- Backend package `src/clover_v_sopra_steria_hackathon/`:
  - `config.py`: typed `Settings` read once from the environment and the root `.env` (`get_settings()`, cached). Defaults follow `specs/contracts/config.md`. Invalid values (for example `NOTIFY_CHANNEL=email`) stop the app with a `ConfigError` naming the variable. Only this module reads environment variables.
  - `models.py`: Pydantic models `Observation`, `WearableSample` (unset optional fields are omitted from JSON) and `SentMessage`. Unknown fields, wrong-case enum values and datetimes without a UTC offset are rejected.
  - `api.py`: FastAPI app with `GET /health`, CORS restricted to `CORS_ORIGINS`, and an empty `/api` router for future routes. Exposed as the `clover-api` script.
  - Empty module packages, each with a one-line docstring: `audio`, `extraction`, `store`, `routing`, `guardrails`, `reports`, `wearable`, `agent`, `signals`.
- New dependencies: `pydantic`, `pydantic-settings`, `strands-agents` (runtime); `hypothesis`, `httpx` (dev).
- Minimal Next.js frontend in `frontend/` (App Router, TypeScript strict, no CSS framework): one home page with the `Karis` heading and a health indicator that calls the backend. The full UI comes later.
- Environment templates: `.env.example` (backend, every variable with a comment) and `frontend/.env.local.example`. The existing root `.env` received the missing variables with their template defaults; existing values were not changed.
- `.gitignore` now also hides `frontend/.env.local`, `frontend/node_modules/`, `frontend/.next/` and `frontend/out/`.
- Offline unit tests: `tests/test_layout.py`, `test_config.py`, `test_models.py`, `test_models_properties.py` (hypothesis), `test_api.py`, `test_env_templates.py`. The existing live AWS tests are unchanged.

## Prerequisites

- Python 3.11 (pinned in `.python-version`; `uv` installs it if needed).
- [uv](https://docs.astral.sh/uv/) for the backend.
- Node.js 20.9 or newer.
- npm (comes with Node.js).

## Environment setup

Backend. If you do not have a root `.env` yet, copy the template, then open `.env` and replace the placeholders (`your-access-key-id`, `your-secret-access-key`, `your-bucket-name`) with your own values. Never commit `.env`.

From the project root:

```bash
cp .env.example .env
```

If `.env` already exists, compare it with `.env.example` and add any missing variable. Empty values fall back to the defaults.

Frontend. The only variable is `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`).

From `frontend/`:

```bash
cp .env.local.example .env.local
npm install
```

Backend dependencies install automatically on the first `uv run`. To install them explicitly, from the project root:

```bash
uv sync
```

## Run the backend

From the project root:

```bash
uv run clover-api
```

The API listens on `API_HOST:API_PORT` (default `http://127.0.0.1:8000`) and reloads when a Python file in the package is saved. Interactive API docs: `http://127.0.0.1:8000/docs`. Stop it with `Ctrl+C`.

## Run the frontend

From `frontend/`:

```bash
npm run dev
```

Open `http://localhost:3000`. Other scripts, from `frontend/`:

```bash
npm run lint
npm run build
```

`NEXT_PUBLIC_API_BASE_URL` is read at build time, so restart `npm run dev` (or rebuild) after changing it. If you change the frontend port, add the new origin to `CORS_ORIGINS` in the root `.env`.

## Run the tests

Unit tests (offline, no AWS calls; the live tests are reported as skipped). From the project root:

```bash
uv run pytest
```

The unit tests ignore your root `.env` and your shell's config variables, so they give the same result on every machine.

Live AWS tests (real, possibly billable calls). With your keys and `GAMEDAY_BUCKET` filled in the root `.env`, no extra setup is needed. From the project root:

```bash
uv run pytest --aws-live -v -s
```

`tests/conftest.py` picks credentials in this order: an `AWS_PROFILE` exported in your shell, then an AWS CLI profile named `hackathon` if it exists, then `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` from the shell or the root `.env`. The region comes from `AWS_REGION` if exported, else `AWS_DEFAULT_REGION` from `.env`. The bucket comes from `GAMEDAY_BUCKET` in the shell or `.env`.

## Verify connectivity

1. Start the backend (`uv run clover-api` from the project root).
2. From the project root, check the health endpoint:

   ```bash
   curl -s http://localhost:8000/health
   ```

   It returns `status` `ok`, the package version and the notification channel, for example `{"status":"ok","version":"0.1.0","notify_channel":"mock"}`.
3. Start the frontend (`npm run dev` from `frontend/`) and open `http://localhost:3000`. The home page shows "Connecté au serveur (version 0.1.0)".
4. Stop the backend and reload the page: it shows "Impossible de joindre le serveur à http://localhost:8000".

## Manual AWS configuration (still to do by the user)

These steps are done in the AWS console or terminal, not in code. Everything here uses region **us-east-1 (N. Virginia)**.

### 1. Make sure the Claude models are usable

Karis uses two Claude models through Bedrock "inference profiles" (IDs starting with `us.`):

- Claude Haiku 4.5: `us.anthropic.claude-haiku-4-5-20251001-v1:0` (`BEDROCK_MODEL_EXTRACT`)
- Claude Sonnet 4: `us.anthropic.claude-sonnet-4-20250514-v1:0` (`BEDROCK_MODEL_REPORT`)

1. Sign in to the AWS console and select the region **US East (N. Virginia) us-east-1** at the top right.
2. Open the **Amazon Bedrock** service (type "Bedrock" in the search bar).
3. In the left menu, open **Model catalog**.
4. Search for **Claude Haiku 4.5**, open it and click **Open in playground**. Type a short message and send it.
5. Do the same for **Claude Sonnet 4**.
6. If AWS asks you to fill in an **Anthropic use-case form** the first time, fill it in and submit it. Approval is usually quick.
7. If you see an error saying you are not allowed to use the model or to submit the form (common on shared hackathon accounts), ask the hackathon organizers to enable the two models for your account.

### 2. Give your IAM user permission to call the models

Your access keys belong to an IAM user. That user needs permission to call the two models. Calling an inference profile requires permission on the profile **and** on the underlying model in every US region the profile can use, hence the `*` region in the foundation-model ARNs.

1. Find your account ID: in the console, click your user name at the top right; the 12-digit number is the account ID. Or, from the project root:

   ```bash
   aws sts get-caller-identity --query Account --output text
   ```

2. In the console, open **IAM**, then **Users**, then your user, then **Add permissions**, **Create inline policy**, and choose the **JSON** tab.
3. Paste the policy below, replacing `<ACCOUNT_ID>` (twice) with your account ID. Click **Next**, name it `KarisBedrockInvoke`, and click **Create policy**.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "KarisInvokeClaude",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1:<ACCOUNT_ID>:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0",
        "arn:aws:bedrock:us-east-1:<ACCOUNT_ID>:inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-sonnet-4-20250514-v1:0"
      ]
    }
  ]
}
```

If you cannot edit IAM yourself (shared account), send this policy to the hackathon organizers. The `list-inference-profiles` command in step 3 also needs `bedrock:ListInferenceProfiles`; it is optional.

### 3. Test that both models answer

List the Claude inference profiles available to you. From the project root:

```bash
aws bedrock list-inference-profiles --region us-east-1 --query "inferenceProfileSummaries[?contains(inferenceProfileId, 'anthropic.claude')].[inferenceProfileId,status]" --output table
```

Both IDs above should appear as `ACTIVE`. Then call each model with the sample script. It reads its credentials from `samples/.env`. From `samples/`:

```bash
uv run --with python-dotenv python bedrock_sample.py --model us.anthropic.claude-haiku-4-5-20251001-v1:0 --prompt "Dis bonjour en une phrase."
uv run --with python-dotenv python bedrock_sample.py --model us.anthropic.claude-sonnet-4-20250514-v1:0 --prompt "Dis bonjour en une phrase."
```

Each command should print a short French greeting. If it fails:

| Error message contains | What it means | Fix |
| --- | --- | --- |
| `not authorized to perform: bedrock:InvokeModel` | IAM policy missing or wrong | Redo step 2; check the account ID and both ARN types |
| `You don't have access to the model` | Model not enabled for the account | Redo step 1 (playground and use-case form), or ask the organizers |
| `on-demand throughput isn't supported` | A bare model ID was used | Use the `us.` inference profile ID |
| `model identifier is invalid` or `ResourceNotFoundException` | Typo or wrong region | Check the ID and that the region is `us-east-1` |
| `UnrecognizedClientException` or `security token ... invalid` | Wrong or expired access keys | Fix the keys in `samples/.env` (and the root `.env`) |
| `ThrottlingException` | Too many requests | Wait a minute and retry |

### 4. Set up the live tests

Nothing to configure if your keys and `GAMEDAY_BUCKET` are in the root `.env`: the live tests read them from there. From the project root:

```bash
uv run pytest --aws-live -v -s
```

Optional: if you prefer an AWS CLI profile, run `aws configure --profile hackathon`; the tests use it automatically when it exists.

The live Bedrock test uses `amazon.nova-pro-v1:0` by default; to test Claude instead, also export `BEDROCK_TEST_MODEL=us.anthropic.claude-haiku-4-5-20251001-v1:0`.

### 5. Later only (not needed now)

- Bedrock Guardrail: created in feature 006; then fill `GUARDRAIL_ID` and `GUARDRAIL_VERSION` in `.env`.
- Real notification channels (SNS, SES or Telegram): set up in feature 005. Until then keep `NOTIFY_CHANNEL=mock`.
