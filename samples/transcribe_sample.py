"""Amazon Transcribe smoke test: audio file -> text.

Theme: "helpers for people who need care". The default audio is a spoken note
(e.g. someone describing how they feel or what help they need) that a helper
can turn into readable text.

Transcribe reads audio from S3, so this script:
  1. uploads the audio file to GAMEDAY_BUCKET,
  2. starts an asynchronous transcription job,
  3. polls until it finishes,
  4. downloads, prints, and saves the transcript.

Usage:
    python transcribe_sample.py                      # first file in audio/*.mp3
    python transcribe_sample.py --audio audio/clip.mp3
    python transcribe_sample.py --audio clip.wav --language en-US

Supported media formats include mp3, mp4, wav, flac, ogg, amr, webm.
"""

import argparse
import glob
import json
import os
import time
import urllib.request
import uuid

import common


def default_audio() -> str:
    """Return the first audio/*.mp3 file, or a sensible fallback path."""
    matches = sorted(glob.glob(common.input_path("audio", "*.mp3")))
    return matches[0] if matches else common.input_path("audio", "Enregistrement.mp3")


def run(audio_path: str = None, language: str = "fr-FR") -> str:
    """Transcribe audio_path, print progress, and return the transcript text."""
    audio_path = audio_path or default_audio()
    if not os.path.isfile(audio_path):
        common.fail(f"Audio file not found: {audio_path}")

    s3 = common.client("s3")
    transcribe = common.client("transcribe")
    bucket = common.bucket()

    ext = os.path.splitext(audio_path)[1].lstrip(".").lower() or "mp3"
    job_name = f"gameday-transcribe-{uuid.uuid4().hex[:8]}"
    key = f"gameday-samples/audio/{job_name}.{ext}"

    print(f"Audio  : {audio_path}")
    print(f"Bucket : {bucket}")
    print(f"Region : {common.region()}")
    print(f"Lang   : {language}")
    print(f"Job    : {job_name}\n")

    # 1. Upload audio
    print(f"[1/4] Uploading audio to s3://{bucket}/{key} ...")
    s3.upload_file(audio_path, bucket, key)

    # 2. Start job
    print("[2/4] Starting transcription job ...")
    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": f"s3://{bucket}/{key}"},
        MediaFormat=ext,
        LanguageCode=language,
    )

    # 3. Poll
    print("[3/4] Waiting for completion (polling every 5s) ...")
    while True:
        resp = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        status = resp["TranscriptionJob"]["TranscriptionJobStatus"]
        print(f"      status: {status}")
        if status in ("COMPLETED", "FAILED"):
            break
        time.sleep(5)

    if status == "FAILED":
        reason = resp["TranscriptionJob"].get("FailureReason", "unknown")
        common.fail(f"Transcription failed: {reason}")

    # 4. Fetch transcript (Transcribe returns a signed URL to a JSON result)
    print("[4/4] Downloading transcript ...")
    transcript_uri = resp["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
    with urllib.request.urlopen(transcript_uri) as r:  # noqa: S310 (AWS signed URL)
        data = json.loads(r.read().decode("utf-8"))

    text = data["results"]["transcripts"][0]["transcript"]
    print("\nTranscript:")
    print("-" * 60)
    print(text.strip() or "(empty)")
    print("-" * 60)

    out_path = common.write_output("transcribe_audio.txt", text)
    print(f"Saved transcript -> {out_path}")
    print("✅ Transcribe sample completed successfully.")
    return text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Amazon Transcribe smoke test")
    parser.add_argument(
        "--audio",
        default=None,
        help="path to a local audio file (default: first audio/*.mp3)",
    )
    parser.add_argument(
        "--language", default="fr-FR", help="language code (default: fr-FR)"
    )
    args = parser.parse_args()
    try:
        run(args.audio, args.language)
    except Exception as err:  # noqa: BLE001
        common.handle_aws_error(err)
