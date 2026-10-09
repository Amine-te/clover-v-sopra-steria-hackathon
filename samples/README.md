# Game Day service samples

Small, self-contained scripts to confirm your AWS credentials work with the
GenAI services used on game day: **S3, Bedrock, Transcribe, Textract**.

Run these first — if they pass, your AK/SK and permissions are set up correctly
and you can start building.

---

## 1. Prerequisites

- Python 3.9+ and the AWS CLI — see [`../docs/IAM_SETUP.md`](../docs/IAM_SETUP.md)
  for install links and prerequisites
- AK/SK created per [`../docs/IAM_SETUP.md`](../docs/IAM_SETUP.md)
- Bedrock model access enabled in the Bedrock console (for the Bedrock sample)

> 🔒 Never commit `.env` or your keys to any repository. See the warning in
> [`../docs/IAM_SETUP.md`](../docs/IAM_SETUP.md).

## 2. Install

```bash
# From the samples/ folder
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
```

## 3. Configure credentials

Copy the example env file and fill in your values:

```bash
# Windows PowerShell:
Copy-Item .env.example .env
# macOS/Linux:
# cp .env.example .env
```

Then edit `.env`:

```
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
GAMEDAY_BUCKET=my-gameday-bucket-team-rocket-8f3a
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
```

> `.env` is git-ignored. Never commit real keys.
> Alternatively, skip `.env` and use an AWS CLI profile:
> `set AWS_PROFILE=gameday` (Windows) / `export AWS_PROFILE=gameday` (macOS/Linux).
> You still need `GAMEDAY_BUCKET` set as an env var in that case.

---

## 4. Run the samples

> **Theme: "helpers for people who need care."** The sample inputs reflect it —
> a prescription (`OCR/ordonnance.png`) and a spoken note (`audio/*.mp3`).
> Every run writes its results to **`samples/output/`**.

### Run everything at once (master script)
```bash
python run_all.py                 # S3 -> Textract -> Transcribe -> Bedrock
python run_all.py --skip s3       # skip one or more steps (repeatable)
```
`run_all.py` runs each service in turn, then feeds the prescription OCR and the
voice-note transcript into Bedrock to produce a clear, caring summary a helper
could act on. Results land in `samples/output/`:
- `textract_ordonnance.txt` — extracted prescription text
- `transcribe_audio.txt` — the transcript
- `bedrock_summary.txt` — the generated helper summary
- `summary.md` — a combined report with status + all three outputs

Each step is independent: if one fails, the script reports it and keeps going.

### S3 — ensure bucket + upload / list / download / delete
```bash
python s3_sample.py
python s3_sample.py --keep        # keep the test object
```
Creates `GAMEDAY_BUCKET` if it doesn't exist, then confirms read/write access.

### Bedrock — invoke a foundation model
```bash
python bedrock_sample.py --list                       # see available models
python bedrock_sample.py                               # default prompt + model
python bedrock_sample.py --model amazon.nova-lite-v1:0 --prompt "Write a haiku"
```
Uses the Bedrock **Converse** API, so the same code works across Claude, Nova,
Titan, Llama, etc. If you get `AccessDeniedException`, enable **Model access**
in the Bedrock console.

### Transcribe — audio to text
```bash
python transcribe_sample.py                           # first file in audio/*.mp3 (fr-FR)
python transcribe_sample.py --audio audio/clip.mp3
python transcribe_sample.py --audio clip.wav --language en-US
```
Defaults to the first `audio/*.mp3` file and French (`fr-FR`). Uploads the audio
to S3, runs an async job, polls, prints and saves the transcript. Supported
formats: mp3, mp4, wav, flac, ogg, amr, webm.

### Textract — document/image to text
```bash
python textract_sample.py                             # uses OCR/ordonnance.png
python textract_sample.py --file path/to/doc.png
```
Defaults to the prescription in `OCR/ordonnance.png`. Sends a local
JPEG/PNG/single-page PDF to Textract's synchronous `DetectDocumentText`, prints
each detected line with its confidence, and saves the text.

---

## 5. What each script needs

| Script | AWS actions used | Default input |
| --- | --- | --- |
| `run_all.py` | all of the below | `OCR/ordonnance.png` + `audio/*.mp3` |
| `s3_sample.py` | `s3:CreateBucket/PutObject/GetObject/DeleteObject/ListBucket` | — |
| `bedrock_sample.py` | `bedrock:ListFoundationModels`, `bedrock:InvokeModel` (Converse) | model access enabled |
| `transcribe_sample.py` | `transcribe:Start/Get/ListTranscriptionJob` + S3 put/get | first `audio/*.mp3` |
| `textract_sample.py` | `textract:DetectDocumentText` | `OCR/ordonnance.png` |

All of these are covered by the AWS managed policies attached in
[`../docs/IAM_SETUP.md`](../docs/IAM_SETUP.md)
(`AmazonBedrockFullAccess`, `AmazonTranscribeFullAccess`,
`AmazonTextractFullAccess`, `AmazonS3FullAccess`).

---

## 6. Troubleshooting

- **`UnrecognizedClientException` / `InvalidClientTokenId`** — your AK/SK is
  wrong or not loaded. Check `.env`.
- **`AccessDeniedException`** — the IAM policy is missing an action, or (Bedrock)
  model access isn't enabled.
- **`NoSuchBucket`** — `GAMEDAY_BUCKET` is wrong, or the bucket is in a different
  region than `AWS_DEFAULT_REGION`.
- **Bedrock model not found** — run `python bedrock_sample.py --list` and pick an
  id that's actually available in your region.
