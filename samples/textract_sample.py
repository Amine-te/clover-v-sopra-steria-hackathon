"""Amazon Textract smoke test: extract text from a document/image.

Theme: "helpers for people who need care". The default document is a medical
prescription (ordonnance) — exactly the kind of paperwork a helper might need
to read for someone who can't.

For single-page JPEG/PNG/PDF, Textract's synchronous DetectDocumentText works
directly on bytes — no S3 round trip needed. This script sends the file and
prints + saves the detected lines.

Usage:
    python textract_sample.py                       # uses OCR/ordonnance.png
    python textract_sample.py --file path/to/doc.png

Note: synchronous DetectDocumentText supports JPEG, PNG, and single-page PDF/TIFF.
Multi-page PDFs require the asynchronous Start/GetDocumentTextDetection APIs
(which read from S3) — out of scope for this quick smoke test.
"""

import argparse
import os

import common

DEFAULT_FILE = common.input_path("OCR", "ordonnance.png")


def run(file_path: str = DEFAULT_FILE) -> str:
    """Run Textract on file_path, print progress, and return the extracted text."""
    if not os.path.isfile(file_path):
        common.fail(f"File not found: {file_path}")

    textract = common.client("textract")

    with open(file_path, "rb") as fh:
        document_bytes = fh.read()

    size_kb = len(document_bytes) / 1024
    print(f"File   : {file_path} ({size_kb:.1f} KB)")
    print(f"Region : {common.region()}\n")

    if size_kb > 10 * 1024:
        print(
            "[warn] Synchronous Textract accepts up to ~10 MB of bytes. "
            "Larger files need the async S3-based API."
        )

    print("[1/2] Calling DetectDocumentText ...")
    resp = textract.detect_document_text(Document={"Bytes": document_bytes})

    print("[2/2] Detected text lines:\n")
    lines = [b for b in resp.get("Blocks", []) if b["BlockType"] == "LINE"]
    if not lines:
        print("  (no text detected)")
    for block in lines:
        confidence = block.get("Confidence", 0)
        print(f"  [{confidence:5.1f}%] {block.get('Text', '')}")

    print(f"\nTotal lines: {len(lines)}")

    text = "\n".join(b.get("Text", "") for b in lines)
    out_path = common.write_output("textract_ordonnance.txt", text)
    print(f"Saved extracted text -> {out_path}")
    print("✅ Textract sample completed successfully.")
    return text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Amazon Textract smoke test")
    parser.add_argument(
        "--file",
        default=DEFAULT_FILE,
        help="path to a local image or single-page PDF (default: OCR/ordonnance.png)",
    )
    args = parser.parse_args()
    try:
        run(args.file)
    except Exception as err:  # noqa: BLE001
        common.handle_aws_error(err)
