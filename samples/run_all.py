"""Master script — run every game day service sample end to end.

Theme: "helpers for people who need care".

Pipeline:
  1. S3        — ensure the bucket works (create if missing, round-trip a file).
  2. Textract  — read the prescription in OCR/ordonnance.png.
  3. Transcribe— turn the spoken note in audio/*.mp3 into text.
  4. Bedrock   — combine both into a clear, caring summary a helper can act on.

Every step's output is written to samples/output/, and a combined
output/summary.md ties it all together.

Usage:
    python run_all.py
    python run_all.py --skip transcribe        # skip one or more steps
    python run_all.py --skip s3 --skip bedrock

Each step runs independently; if one fails the script reports it and keeps going
so you can see which services are working.
"""

import argparse
import datetime
import os
import traceback

import common

# Reusable step functions from the individual samples.
import s3_sample
import textract_sample
import transcribe_sample
import bedrock_sample

STEPS = ["s3", "textract", "transcribe", "bedrock"]

HELPER_PROMPT = """Tu es un assistant bienveillant qui aide une personne \
dépendante (ou son aidant). À partir de l'ordonnance et de la note vocale \
ci-dessous, rédige un résumé clair et rassurant en français, facile à lire.

Inclure :
- Les médicaments et comment les prendre (si présents dans l'ordonnance).
- Ce que la personne demande ou ressent (d'après la note vocale).
- Une courte liste d'actions concrètes pour l'aidant.

N'invente aucune information médicale qui n'est pas dans les textes fournis.

=== ORDONNANCE (OCR) ===
{ocr}

=== NOTE VOCALE (transcription) ===
{transcript}
"""


def banner(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def main(skip):
    results = {}
    errors = {}

    # 1. S3 ---------------------------------------------------------------
    if "s3" not in skip:
        banner("STEP 1/4 — S3 (bucket + object round-trip)")
        try:
            s3_sample.main(keep=False)
            results["s3"] = "OK"
        except Exception as err:  # noqa: BLE001
            errors["s3"] = err
            print(f"[FAILED] S3 step: {err}")

    # 2. Textract ---------------------------------------------------------
    ocr_text = ""
    if "textract" not in skip:
        banner("STEP 2/4 — Textract (read the prescription)")
        try:
            ocr_text = textract_sample.run()
            results["textract"] = ocr_text
        except Exception as err:  # noqa: BLE001
            errors["textract"] = err
            print(f"[FAILED] Textract step: {err}")

    # 3. Transcribe -------------------------------------------------------
    transcript = ""
    if "transcribe" not in skip:
        banner("STEP 3/4 — Transcribe (read the voice note)")
        try:
            transcript = transcribe_sample.run()
            results["transcribe"] = transcript
        except Exception as err:  # noqa: BLE001
            errors["transcribe"] = err
            print(f"[FAILED] Transcribe step: {err}")

    # 4. Bedrock ----------------------------------------------------------
    summary = ""
    if "bedrock" not in skip:
        banner("STEP 4/4 — Bedrock (caring summary for the helper)")
        if not ocr_text and not transcript:
            print("[skip] No OCR or transcript text available to summarize.")
        else:
            model_id = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
            prompt = HELPER_PROMPT.format(
                ocr=ocr_text or "(aucune ordonnance disponible)",
                transcript=transcript or "(aucune note vocale disponible)",
            )
            try:
                summary = bedrock_sample.invoke(
                    model_id, prompt, max_tokens=600, save_as="bedrock_summary.txt"
                )
                results["bedrock"] = summary
            except Exception as err:  # noqa: BLE001
                errors["bedrock"] = err
                print(f"[FAILED] Bedrock step: {err}")

    # Combined report -----------------------------------------------------
    write_summary(ocr_text, transcript, summary, results, errors)

    # Final status --------------------------------------------------------
    banner("DONE")
    for step in STEPS:
        if step in skip:
            print(f"  {step:<11} skipped")
        elif step in errors:
            print(f"  {step:<11} ❌ FAILED")
        elif step in results:
            print(f"  {step:<11} ✅ OK")
    print(f"\nAll outputs are in: {common.output_dir()}")

    return 1 if errors else 0


def write_summary(ocr_text, transcript, summary, results, errors):
    now = datetime.datetime.utcnow().isoformat() + "Z"
    lines = [
        "# Game Day — Helper assistant run",
        "",
        f"_Generated {now}_",
        "",
        "## Status",
        "",
    ]
    for step in STEPS:
        if step in errors:
            lines.append(f"- **{step}**: ❌ failed — {errors[step]}")
        elif step in results:
            lines.append(f"- **{step}**: ✅ ok")
        else:
            lines.append(f"- **{step}**: skipped")

    lines += ["", "## Prescription (Textract OCR)", "", "```",
              ocr_text or "(none)", "```", ""]
    lines += ["## Voice note (Transcribe)", "", "```",
              transcript or "(none)", "```", ""]
    lines += ["## Caring summary (Bedrock)", "", summary or "(none)", ""]

    path = common.write_output("summary.md", "\n".join(lines))
    print(f"\nCombined report -> {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run all game day service samples")
    parser.add_argument(
        "--skip",
        action="append",
        default=[],
        choices=STEPS,
        help="skip a step (repeatable), e.g. --skip s3 --skip bedrock",
    )
    args = parser.parse_args()
    try:
        raise SystemExit(main(set(args.skip)))
    except Exception as err:  # noqa: BLE001
        common.handle_aws_error(err)
