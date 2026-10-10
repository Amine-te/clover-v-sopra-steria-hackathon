"""Audio formats and fixture transcripts (Requirements 3.3 to 3.5)."""
import pytest

from clover_v_sopra_steria_hackathon.audio import fixtures
from clover_v_sopra_steria_hackathon.audio.fixtures import FixtureNotFoundError, load_fixture
from clover_v_sopra_steria_hackathon.audio.formats import (
    ALLOWED_FORMATS,
    MAX_AUDIO_BYTES,
    media_format,
)


def test_allowed_formats():
    assert ALLOWED_FORMATS == {"mp3", "mp4", "m4a", "wav", "flac", "ogg", "webm"}


def test_max_size_is_25_mb():
    assert MAX_AUDIO_BYTES == 25 * 1024 * 1024


@pytest.mark.parametrize(
    ("ext", "expected"),
    [("mp3", "mp3"), ("m4a", "mp4"), (".M4A", "mp4"), ("webm", "webm"), ("WAV", "wav")],
)
def test_media_format(ext, expected):
    assert media_format(ext) == expected


@pytest.mark.parametrize("ext", ["txt", "amr", "", "exe"])
def test_media_format_rejects_unknown(ext):
    with pytest.raises(ValueError):
        media_format(ext)


def test_default_fixture():
    assert load_fixture() == load_fixture("default")
    assert load_fixture(None).startswith("Bonsoir")


def test_named_fixture():
    assert "glissé" in load_fixture("chute")


def test_unknown_fixture():
    with pytest.raises(FixtureNotFoundError):
        load_fixture("does-not-exist")


@pytest.mark.parametrize("name", ["../config", "../../.env", "default.txt", "a/b", "Default", "/etc/passwd"])
def test_unsafe_names_rejected(name):
    with pytest.raises(FixtureNotFoundError):
        load_fixture(name)


def test_at_least_three_french_fixtures_covering_topics():
    files = sorted(fixtures.FIXTURES_DIR.glob("*.txt"))
    assert len(files) >= 3
    text = " ".join(path.read_text(encoding="utf-8").lower() for path in files)
    for word in ("dormi", "mangé", "comprimé", "tombé", "humeur"):
        assert word in text
