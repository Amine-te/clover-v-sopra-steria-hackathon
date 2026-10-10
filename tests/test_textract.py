"""Synchronous OCR for the existing PNG sample."""
import pytest

pytestmark = pytest.mark.aws_live


def test_textract_detect_document_text(aws_session, document_path):
    client = aws_session.client("textract")
    image_bytes = document_path.read_bytes()
    assert len(image_bytes) <= 5 * 1024 * 1024, "Synchronous Textract input must be <= 5 MB"
    response = client.detect_document_text(Document={"Bytes": image_bytes})
    lines = [b["Text"] for b in response.get("Blocks", []) if b.get("BlockType") == "LINE"]
    print("OCR lines:", *lines[:30], sep="\n")
    assert lines, "Textract returned no text lines"
