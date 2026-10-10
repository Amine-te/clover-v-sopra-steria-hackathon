"""FastAPI skeleton tests (Requirement 4), using the in-process TestClient only."""
import importlib
import os
import subprocess
import sys
import time
from importlib.metadata import version

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from clover_v_sopra_steria_hackathon.config import Settings

ALLOWED = "http://localhost:3000"
OTHER_ALLOWED = "https://karis.example.com:8443"
DISALLOWED = "http://localhost:3001"
DOC_PATHS = {"/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}

# Imports the API module with every outbound socket connection blocked and no .env file.
_IMPORT_SCRIPT = """
import socket
def _blocked(*args, **kwargs):
    raise RuntimeError("network access attempted during import")
socket.socket.connect = _blocked
socket.create_connection = _blocked
from clover_v_sopra_steria_hackathon.config import Settings
Settings.model_config["env_file"] = None
from clover_v_sopra_steria_hackathon.api import app
assert app is not None
"""


@pytest.fixture
def api_module():
    # Imported lazily so the module-level app is built under the isolated settings.
    return importlib.import_module("clover_v_sopra_steria_hackathon.api")


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("NOTIFY_CHANNEL", "telegram")
    monkeypatch.setenv("CORS_ORIGINS", f"{ALLOWED}, {OTHER_ALLOWED}")
    return Settings(_env_file=None)


@pytest.fixture
def client(api_module, settings):
    return TestClient(api_module.create_app(settings))


def test_health_shape(client, settings):
    start = time.perf_counter()
    response = client.get("/health")
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    assert elapsed < 0.5
    body = response.json()
    assert body == {
        "status": "ok",
        "version": version("clover-v-sopra-steria-hackathon"),
        "notify_channel": settings.notify_channel,
    }
    assert body["version"]


def test_module_level_app_serves_health(api_module):
    response = TestClient(api_module.app).get("/health")
    assert response.status_code == 200
    assert set(response.json()) == {"status", "version", "notify_channel"}
    assert response.json()["status"] == "ok"


@pytest.mark.parametrize("origin", [ALLOWED, OTHER_ALLOWED])
def test_allowed_origin_echoed(client, origin):
    response = client.get("/health", headers={"Origin": origin})
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-origin"] != "*"


@pytest.mark.parametrize("origin", [DISALLOWED, "https://localhost:3000", "http://evil.example.com"])
def test_disallowed_origin_has_no_cors_header(client, origin):
    response = client.get("/health", headers={"Origin": origin})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize(("path", "method"), [("/health", "GET"), ("/api/anything", "POST")])
def test_preflight_allowed(client, path, method):
    response = client.options(
        path,
        headers={"Origin": ALLOWED, "Access-Control-Request-Method": method},
    )
    assert 200 <= response.status_code < 300
    assert response.headers["access-control-allow-origin"] == ALLOWED
    assert method in response.headers["access-control-allow-methods"]


def test_preflight_disallowed_origin(client):
    response = client.options(
        "/health",
        headers={"Origin": DISALLOWED, "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in response.headers


def test_unknown_path_returns_json_404(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert "detail" in response.json()


def test_only_health_outside_api_prefix(api_module, settings):
    app = api_module.create_app(settings)
    # Top-level routes plus every schema route (covers routes nested in included routers).
    top_level = {getattr(route, "path", None) for route in app.routes} - {None}
    paths = (top_level | set(app.openapi()["paths"])) - DOC_PATHS
    outside = {path for path in paths if path != "/api" and not path.startswith("/api/")}
    assert outside == {"/health"}
    assert all(
        isinstance(route, APIRoute) for route in app.routes if getattr(route, "path", None) in paths
    )


def test_import_makes_no_network_call(tmp_path):
    env = {
        key: value for key, value in os.environ.items()
        if not key.startswith("AWS_") and key.lower() not in Settings.model_fields
    }
    result = subprocess.run(
        [sys.executable, "-c", _IMPORT_SCRIPT],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
