"""Check the FastAPI/Starlette/HTTPX stack against actual application routes."""

import importlib

from fastapi.testclient import TestClient


def test_health_and_openapi_work_with_installed_http_stack(monkeypatch):
    monkeypatch.setenv("DEBUG", "false")
    backend = importlib.import_module("web_backend.main")
    with TestClient(backend.app) as client:
        root = client.get("/")
        assert root.status_code == 200
        health = client.get(root.json()["health"])
        assert health.status_code == 200
        assert health.json()["status"] == "healthy"
        schema = client.get(backend.app.openapi_url)
        assert schema.status_code == 200
        assert root.json()["health"] in schema.json()["paths"]
