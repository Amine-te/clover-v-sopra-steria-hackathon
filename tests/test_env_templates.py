"""Environment template and secret hygiene checks (Requirement 7). Never reads real .env files."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from clover_v_sopra_steria_hackathon.config import Settings

ROOT = Path(__file__).resolve().parents[1]
BACKEND_TEMPLATE = ROOT / ".env.example"
FRONTEND_TEMPLATE = ROOT / "frontend" / ".env.local.example"
SAMPLES_TEMPLATE = ROOT / "samples" / ".env.example"
TEMPLATES = [BACKEND_TEMPLATE, FRONTEND_TEMPLATE, SAMPLES_TEMPLATE]
SECRET_FILES = [".env", "samples/.env", "frontend/.env.local"]
IGNORED_DIRS = ["frontend/node_modules/", "frontend/.next/", "frontend/out/"]
CREDENTIAL_FIELDS = {"aws_access_key_id", "aws_secret_access_key", "gameday_bucket"}
ASSIGNMENT = re.compile(r"^([A-Z_][A-Z0-9_]*)=(.*)$")


def parse(path):
    """Return [(name, value, previous_line)] for every assignment line."""
    lines = path.read_text(encoding="utf-8").splitlines()
    entries = []
    for index, line in enumerate(lines):
        match = ASSIGNMENT.match(line)
        if match:
            previous = lines[index - 1] if index else ""
            entries.append((match.group(1), match.group(2), previous))
    return entries


def test_backend_template_lists_every_variable_once_with_comment():
    entries = parse(BACKEND_TEMPLATE)
    names = [name for name, _, _ in entries]
    expected = {field.upper() for field in Settings.model_fields} | {"AWS_PROFILE"}
    assert expected <= set(names)
    assert len(names) == len(set(names))
    for name, _, previous in entries:
        assert previous.startswith("# ") and len(previous) > 2, f"{name} lacks a comment line"


def test_backend_template_defaults_match_settings():
    from_template = Settings(_env_file=BACKEND_TEMPLATE)
    defaults = Settings(_env_file=None)
    for field in Settings.model_fields:
        if field not in CREDENTIAL_FIELDS:
            assert getattr(from_template, field) == getattr(defaults, field), field


def test_frontend_template():
    entries = parse(FRONTEND_TEMPLATE)
    assert [(name, value) for name, value, _ in entries] == [
        ("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000"),
    ]
    assert entries[0][2].startswith("# ")


def test_samples_template_lists_sample_variables():
    names = {name for name, _, _ in parse(SAMPLES_TEMPLATE)}
    assert {
        "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION",
        "GAMEDAY_BUCKET", "BEDROCK_MODEL_ID",
    } <= names


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda p: str(p.relative_to(ROOT)))
def test_templates_hold_no_credential_shaped_values(template):
    text = template.read_text(encoding="utf-8")
    assert not re.search(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b", text)
    for name, value, _ in parse(template):
        if "SECRET" in name or name == "AWS_ACCESS_KEY_ID":
            assert not re.fullmatch(r"[A-Za-z0-9/+=]{40}", value), name
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text), "no email addresses in templates"


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


@pytest.mark.skipif(
    shutil.which("git") is None or _git("rev-parse", "--git-dir").returncode != 0,
    reason="git repository not available",
)
def test_gitignore_hides_secrets_but_not_templates():
    for path in SECRET_FILES + IGNORED_DIRS:
        assert _git("check-ignore", "-q", path).returncode == 0, f"{path} must be ignored"
    for template in TEMPLATES:
        rel = template.relative_to(ROOT).as_posix()
        assert _git("check-ignore", "-q", rel).returncode == 1, f"{rel} must not be ignored"
