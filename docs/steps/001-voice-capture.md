# 001 Voice capture

The caregiver submits a short French voice report. The backend stores the audio in S3 and turns it into text with AWS Transcribe (batch, `fr-FR`). With `USE_CACHED_TRANSCRIPTS=true`, a fictional fixture transcript is returned instead, without calling Transcribe. Spec: [001 Voice capture](../../specs/features/001-voice-capture.md); detailed requirements and design in `.kiro/specs/voice-capture/`.

## What was set up

- `src/clover_v_sopra_steria_hackathon/aws.py`: `client(service, settings)`, the single factory for boto3 clients. Region from `AWS_DEFAULT_REGION`; explicit keys only when both `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are set, otherwise boto3's default chain (environment, profiles).
- `audio/` package:
  - `formats.py`: accepted formats (`mp3`, `mp4`, `m4a`, `wav`, `flac`, `ogg`, `webm`), the Transcribe `MediaFormat` (`m4a` is sent as `mp4`), 25 MB limit.
  - `fixtures.py`: loads fixture transcripts from `tests/fixtures/transcripts/` (`default.txt`, `chute.txt`, `refus-traitement.txt`; invented people only). Names are limited to `[a-z0-9_-]+`.
  - `service.py`: `VoiceService`. Live mode uploads the audio to `audio/<report_id>.<ext>` first, then starts a Transcribe job whose output goes to `transcripts/<report_id>.json` in the same bucket, polls every 3 s (timeout 180 s) and reads the JSON back with boto3. The audio stays in S3 when transcription fails, so it can be retried.
  - `routes.py`: `POST /api/reports/voice` and `POST /api/reports/{report_id}/transcribe`.
- `models.py`: `VoiceReportResponse` and `VoiceReportError`.
- Frontend: page `/report-voice` (record with the microphone or choose a file, then see the transcript; "Réessayer" button after a transcription failure), linked from the home page as "Enregistrer un rapport vocal". API calls in `frontend/src/lib/api.ts` (`submitVoiceReport`, `retryTranscription`).
- Tests: `tests/test_aws_factory.py`, `test_audio_formats_fixtures.py`, `test_voice_service.py`, `test_voice_api.py` (offline, fake AWS clients) and `test_voice_capture_live.py` (real AWS, marked `aws_live`).

Report IDs look like `rep-` followed by 32 hex characters. Each Transcribe job is named `karis-<report_id>-<8 hex>`, so a retry never collides with an earlier job.

## Configuration

Variables in the root `.env` (see `.env.example`):

| Variable | Use in this step |
| --- | --- |
| `GAMEDAY_BUCKET` | S3 bucket for the audio and the transcripts. Required in live mode (HTTP 500 if missing). Optional in cached mode: when set, the audio is still uploaded (best effort). |
| `USE_CACHED_TRANSCRIPTS` | `true` returns a fixture transcript and never calls Transcribe. Default `false`. |
| `TRANSCRIBE_LANGUAGE` | Transcribe `LanguageCode`. Default `fr-FR`. |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` | Credentials and region for S3 and Transcribe. If a key is empty, boto3's default chain is used (for example `AWS_PROFILE`). |

To switch to cached mode for one run only, export the variable in the shell that starts the backend (shell variables override `.env`). From the project root:

```bash
USE_CACHED_TRANSCRIPTS=true uv run clover-api
```

### IAM permissions

The IAM user or role behind the credentials needs these actions. Transcribe reads the audio and writes its output with the caller's permissions, so the S3 actions cover both the app and Transcribe.

- S3 on the bucket: `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` (on `arn:aws:s3:::<bucket>/*`), `s3:ListBucket` (on `arn:aws:s3:::<bucket>`; used by the retry endpoint).
- Transcribe: `transcribe:StartTranscriptionJob`, `transcribe:GetTranscriptionJob`, `transcribe:DeleteTranscriptionJob` (the delete action is only used by the live test cleanup).

Example inline policy (replace `<bucket>` with the value of `GAMEDAY_BUCKET`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "KarisAudioObjects",
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::<bucket>/*"
    },
    {
      "Sid": "KarisAudioList",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::<bucket>"
    },
    {
      "Sid": "KarisTranscribe",
      "Effect": "Allow",
      "Action": [
        "transcribe:StartTranscriptionJob",
        "transcribe:GetTranscriptionJob",
        "transcribe:DeleteTranscriptionJob"
      ],
      "Resource": "*"
    }
  ]
}
```

## Run the backend

From the project root:

```bash
uv run clover-api
```

The API listens on `http://127.0.0.1:8000`. Interactive docs, including the two new endpoints: `http://127.0.0.1:8000/docs`.

## Run the frontend

From `frontend/`:

```bash
npm run dev
```

Open `http://localhost:3000`, click "Enregistrer un rapport vocal", then either click "Commencer l'enregistrement" (the browser asks for the microphone; click "Arrêter et envoyer" when done) or choose a file and click "Envoyer le fichier". If the browser has no MediaRecorder or the microphone is refused, the page says so and the file upload still works.

## API reference

### `POST /api/reports/voice`

Multipart form: `audio` (required file) and `fixture` (optional, cached mode only, fixture name without `.txt`).

Live mode (backend started with `USE_CACHED_TRANSCRIPTS=false`). From the project root:

```bash
curl -s -F "audio=@samples/audio/Enregistrement.mp3;type=audio/mpeg" http://127.0.0.1:8000/api/reports/voice
```

```json
{"report_id":"rep-e47d20609de6228275c9eca6dbc3dce5","audio_s3_key":"audio/rep-e47d20609de6228275c9eca6dbc3dce5.mp3","transcript":"Aujourd'hui, papa est tombé et il s'est abîmé la hanche. On a pris rendez-vous avec le médecin généraliste, mais je pense que je vais devoir l'emmener à l'hôpital ce soir.","source":"transcribe"}
```

This takes about 10 to 20 seconds (the Transcribe job).

Cached mode (backend started with `USE_CACHED_TRANSCRIPTS=true`). From the project root:

```bash
curl -s -F "audio=@samples/audio/Enregistrement.mp3;type=audio/mpeg" http://127.0.0.1:8000/api/reports/voice
curl -s -F "audio=@samples/audio/Enregistrement.mp3;type=audio/mpeg" -F fixture=chute http://127.0.0.1:8000/api/reports/voice
```

Both return `"source":"cache"` and the text of `default.txt` or `chute.txt`. `audio_s3_key` is `null` when no bucket is set or the upload failed.

### `POST /api/reports/{report_id}/transcribe`

Runs Transcribe again on the audio already stored for this report (no new upload). Same response shapes as above. From the project root:

```bash
curl -s -X POST http://127.0.0.1:8000/api/reports/rep-e47d20609de6228275c9eca6dbc3dce5/transcribe
```

In cached mode it returns the default fixture.

### Errors

| Situation | HTTP | Body |
| --- | --- | --- |
| Extension not accepted (checked first) | 415 | `{"detail": "Format audio non pris en charge. Formats acceptés : flac, m4a, mp3, mp4, ogg, wav, webm."}` |
| Empty file | 400 | `{"detail": "Le fichier audio est vide."}` |
| Larger than 25 MB | 413 | `{"detail": "Le fichier audio dépasse 25 Mo."}` |
| Unknown fixture | 404 | `{"detail": "Transcription de démonstration introuvable."}` |
| Retry with no stored audio | 404 | `{"detail": "Aucun enregistrement trouvé pour ce rapport."}` |
| `report_id` not `rep-<32 hex>` | 422 | FastAPI validation error |
| `GAMEDAY_BUCKET` missing in live mode | 500 | `{"detail": "Configuration incomplète : GAMEDAY_BUCKET n'est pas défini."}` |
| Upload to S3 failed | 502 | `{"report_id": "...", "audio_s3_key": null, "detail": "L'enregistrement n'a pas pu être sauvegardé. Veuillez réessayer l'envoi.", "retryable": false}` |
| Transcribe failed or timed out | 502 | `{"report_id": "...", "audio_s3_key": "audio/...", "detail": "La transcription a échoué. Votre enregistrement est sauvegardé, vous pouvez réessayer.", "retryable": true}` |

## Run the tests

Unit tests (offline, fake AWS clients, no real waiting). From the project root:

```bash
uv run pytest
```

Live tests, including the real voice pipeline on `samples/audio/Enregistrement.mp3` (a few cents of Transcribe; the test deletes the audio, the transcript and the Transcribe job it created). From the project root:

```bash
uv run pytest --aws-live -v -s
```

To run only the new live test, from the project root:

```bash
uv run pytest --aws-live -s tests/test_voice_capture_live.py
```

## Verify

1. Start the backend in live mode (`uv run clover-api` from the project root) and run the live `curl` above: `source` is `transcribe` and the transcript is the French sentence about the fall.
2. From the project root, check the validation errors (415 for a non-audio file, 400 for an empty file):

   ```bash
   printf 'hello' > note.txt && curl -s -F "audio=@note.txt" http://127.0.0.1:8000/api/reports/voice
   : > empty.mp3 && curl -s -F "audio=@empty.mp3" http://127.0.0.1:8000/api/reports/voice
   rm note.txt empty.mp3
   ```

3. Stop the backend, start it in cached mode (`USE_CACHED_TRANSCRIPTS=true uv run clover-api`) and run the cached `curl`: `source` is `cache`.
4. Start the frontend (`npm run dev` from `frontend/`), open `http://localhost:3000/report-voice`, choose `samples/audio/Enregistrement.mp3` and click "Envoyer le fichier": the transcript appears under "Transcription".
5. Manual calls leave objects under `audio/` and `transcripts/` in the bucket and jobs named `karis-rep-…` in Transcribe. Delete them in the S3 and Transcribe consoles when you are done.

## Known gaps

- No authentication: anyone who can reach the API can upload audio and start (billable) Transcribe jobs. The API binds to `127.0.0.1` by default; keep it local until auth is added.
- Batch transcription only (no streaming); a report takes roughly 10 to 20 seconds.
- Nothing deletes old audio or transcripts from the bucket yet, and the Transcribe jobs of the app itself are not deleted.
- The request is synchronous: the browser waits for the whole Transcribe job (up to 180 s server-side, 240 s client-side timeout).
- Transcripts are not stored or turned into observations yet (features 002 and 004).
