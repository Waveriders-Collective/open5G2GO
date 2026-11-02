"""Verify backend startup does not log database credentials."""

import asyncio
import importlib


def test_startup_logs_omit_database_credentials(monkeypatch, caplog):
    # Keep ambient development settings from affecting this isolated startup.
    monkeypatch.setenv("DEBUG", "false")
    backend = importlib.import_module("web_backend.main")
    username = "startup-log-test-user"
    password = "startup-log-test-password"
    uri = f"mongodb://{username}:{password}@localhost:27017"
    monkeypatch.setattr(backend.settings, "mongodb_uri", uri)

    async def startup_and_shutdown():
        async with backend.lifespan(backend.app):
            pass

    with caplog.at_level("INFO", logger="web_backend.main"):
        asyncio.run(startup_and_shutdown())

    assert "Starting " in caplog.text
    assert "Shutting down " in caplog.text
    assert username not in caplog.text
    assert password not in caplog.text
    assert uri not in caplog.text
