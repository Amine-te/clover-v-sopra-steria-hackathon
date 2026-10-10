"""JSON-array recovery from model output (Task 1): bare, fenced, prose, and unparseable."""
import pytest

from clover_v_sopra_steria_hackathon.extraction.parse import ExtractionError, extract_json_array
from clover_v_sopra_steria_hackathon.extraction.prompt import SYSTEM_PROMPT, build_messages

ITEM = '{"category": "sleep", "value": "a mal dormi", "severity": "info", "confidence": 0.8, "transcript_span": "a mal dormi"}'


def test_bare_array():
    result = extract_json_array(f"[{ITEM}]")
    assert len(result) == 1
    assert result[0]["category"] == "sleep"


def test_empty_bare_array():
    assert extract_json_array("[]") == []


def test_fenced_json_block():
    text = f"```json\n[{ITEM}]\n```"
    result = extract_json_array(text)
    assert result[0]["value"] == "a mal dormi"


def test_fenced_block_without_language():
    text = f"```\n[{ITEM}]\n```"
    assert len(extract_json_array(text)) == 1


def test_array_embedded_in_prose():
    text = f"Voici les faits trouvés :\n[{ITEM}]\nJ'espère que cela aide."
    result = extract_json_array(text)
    assert result[0]["transcript_span"] == "a mal dormi"


def test_nested_brackets_in_strings_are_respected():
    item = '{"category": "logistics", "value": "liste [a] et [b]", "severity": "info", "confidence": 0.5, "transcript_span": "liste"}'
    result = extract_json_array(f"prefix [{item}] suffix")
    assert result[0]["value"] == "liste [a] et [b]"


def test_non_object_elements_dropped():
    result = extract_json_array(f'["noise", 42, {ITEM}]')
    assert len(result) == 1
    assert result[0]["category"] == "sleep"


@pytest.mark.parametrize("text", ["", "   ", "no json here at all", "{not an array}", "[unclosed", None])
def test_unparseable_raises(text):
    with pytest.raises(ExtractionError):
        extract_json_array(text)


def test_object_not_array_raises():
    with pytest.raises(ExtractionError):
        extract_json_array('{"category": "sleep"}')


def test_prompt_forbids_diagnosis_and_requires_json_array():
    lowered = SYSTEM_PROMPT.lower()
    assert "json array" in lowered
    assert "diagnosis" in lowered
    assert "transcript_span" in SYSTEM_PROMPT


def test_build_messages_carries_transcript():
    messages = build_messages("Bonjour, elle a bien dormi.")
    assert messages[0]["role"] == "user"
    assert "elle a bien dormi" in messages[0]["content"][0]["text"]
