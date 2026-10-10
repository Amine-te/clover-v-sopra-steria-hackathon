# 001 Voice capture and transcription

- **Status:** Implemented
- **Owner:**
- **Needs:** 000

## Summary

The caregiver records a short voice report; it is stored in S3 and transcribed to French text.

## Inputs and outputs

- In: audio recorded in the app.
- Out: transcript text and the S3 location of the audio.

## Acceptance criteria

- **F001-AC1:** Given a recording, when it is submitted, then the audio is in S3 and a Transcribe job (`fr-FR`) returns text.
- **F001-AC2:** Given `USE_CACHED_TRANSCRIPTS=true`, when a report is submitted, then a fixture transcript is returned without calling Transcribe.
- **F001-AC3:** Given a Transcribe failure, when it happens, then the caregiver sees a retry message and nothing is lost.

## Open questions

- Batch jobs only, or streaming later? **Decided:** batch transcription only (one Transcribe job per report, output written to the bucket and read back with boto3). Streaming may come later. See `docs/steps/001-voice-capture.md`.
