"""Subscriber form handling: blank fields, error bodies and auto-assigned IPs."""

import importlib
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from opensurfcontrol.mongodb_client import SubscriberError
from web_backend.api.dependencies import get_service
from web_backend.services.open5gs_service import Open5GSService

IMSI = "315010000000011"


@pytest.fixture
def mongo():
    """Stand-in for the MongoDB client behind the service."""
    client = MagicMock()
    client.get_subscriber.return_value = None
    return client


@pytest.fixture
def api(monkeypatch, mongo):
    monkeypatch.setenv("DEBUG", "false")
    backend = importlib.import_module("web_backend.main")
    backend.app.dependency_overrides[get_service] = lambda: Open5GSService(client=mongo)
    with TestClient(backend.app) as client:
        yield client
    backend.app.dependency_overrides.clear()


def test_blank_ip_is_auto_assigned(api, mongo):
    # Issue #28: the Add Device form sent ip: "" and got a 422.
    response = api.post("/api/v1/subscribers", json={"imsi": IMSI, "name": "CAM-01", "ip": ""})
    assert response.status_code == 201
    assert mongo.add_subscriber.call_args.kwargs["ip"] == "10.48.99.11"


def test_blank_update_fields_are_ignored(api, mongo):
    mongo.update_subscriber.return_value = True
    response = api.put(f"/api/v1/subscribers/{IMSI}", json={"name": "CAM-02", "ip": ""})
    assert response.status_code == 200
    assert mongo.update_subscriber.call_args.kwargs == {"device_name": "CAM-02"}


def test_validation_errors_are_readable_and_do_not_echo_input(api):
    response = api.post("/api/v1/subscribers", json={"imsi": IMSI, "name": "CAM-01", "ip": "not-an-ip"})
    assert response.status_code == 422
    body = response.json()
    assert body == {"error": "ip: invalid format"}
    assert "not-an-ip" not in response.text


def test_service_errors_are_returned_at_top_level(api, mongo):
    mongo.add_subscriber.side_effect = SubscriberError(
        "IP address 10.48.99.11 is already assigned to IMSI 315010000000012"
    )
    response = api.post("/api/v1/subscribers", json={"imsi": IMSI, "name": "CAM-01"})
    assert response.status_code == 400
    assert response.json()["error"].startswith("IP address 10.48.99.11 is already assigned")
    assert "detail" not in response.json()


def test_not_found_is_returned_at_top_level(api):
    response = api.get(f"/api/v1/subscribers/{IMSI}")
    assert response.status_code == 404
    assert "not found" in response.json()["error"]


def test_unexpected_errors_do_not_reach_clients(api, mongo):
    secret = "mongodb://user:hunter2@db.internal:27017"
    mongo.add_subscriber.side_effect = RuntimeError(f"cannot reach {secret}")
    response = api.post("/api/v1/subscribers", json={"imsi": IMSI, "name": "CAM-01"})
    assert response.status_code == 400
    assert "hunter2" not in response.text
    assert "backend logs" in response.json()["error"]


@pytest.mark.parametrize(
    ("suffix", "expected"),
    [
        (11, "10.48.99.11"),  # Issue #8: was .12
        (2, "10.48.99.2"),
        (254, "10.48.99.254"),
        # .1 is the UPF gateway, so 0000 and 0001 share .2 with 0002
        (1, "10.48.99.2"),
        # Four-digit vendor suffixes clamp to the top of the pool
        (4821, "10.48.99.254"),
    ],
)
def test_auto_assigned_ip_matches_imsi_suffix(suffix, expected):
    assert Open5GSService(client=MagicMock())._calculate_ip(suffix) == expected
