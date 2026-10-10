"""Package layout checks (Requirement 1)."""
import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "src" / "clover_v_sopra_steria_hackathon"
MODULE_PACKAGES = [
    "audio", "extraction", "store", "routing", "guardrails",
    "reports", "wearable", "agent", "signals",
]

# Imports each module with every outbound socket connection blocked.
_IMPORT_SCRIPT = """
import importlib, socket, sys
def _blocked(*args, **kwargs):
    raise RuntimeError("network access attempted during import")
socket.socket.connect = _blocked
socket.create_connection = _blocked
for name in sys.argv[1:]:
    importlib.import_module(name)
"""


@pytest.mark.parametrize("filename", ["config.py", "models.py", "api.py"])
def test_core_modules_at_package_root(filename):
    assert (PACKAGE_DIR / filename).is_file()


@pytest.mark.parametrize("name", MODULE_PACKAGES)
def test_module_package_has_one_line_docstring(name):
    init = PACKAGE_DIR / name / "__init__.py"
    assert init.is_file()
    docstring = ast.get_docstring(ast.parse(init.read_text(encoding="utf-8")))
    assert docstring and docstring.strip()
    assert "\n" not in docstring.strip()
    assert len(docstring.strip()) <= 120


def test_packages_import_without_env_or_network(tmp_path):
    env = {
        key: value for key, value in os.environ.items()
        if not key.startswith("AWS_") and key not in {"GAMEDAY_BUCKET", "BEDROCK_MODEL_ID"}
    }
    modules = [f"clover_v_sopra_steria_hackathon.{name}" for name in MODULE_PACKAGES]
    modules += ["clover_v_sopra_steria_hackathon.models", "clover_v_sopra_steria_hackathon.config"]
    result = subprocess.run(
        [sys.executable, "-c", _IMPORT_SCRIPT, *modules],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert sys.version_info[:2] == (3, 11)
