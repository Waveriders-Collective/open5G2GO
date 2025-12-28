"""
Unit tests for opensurfcontrol.server module.

Tests the MCP server tools for Open5GS subscriber management.
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch, AsyncMock

from opensurfcontrol.server import (
    open5gs_list_subscribers,
    open5gs_get_system_status,
    open5gs_get_active_connections,
    open5gs_get_network_config,
    open5gs_add_subscriber,
    open5gs_get_subscriber,
    open5gs_delete_subscriber,
    open5gs_update_subscriber,
    BaseInput,
    AddSubscriberInput,
    GetSubscriberInput,
    DeleteSubscriberInput,
    UpdateSubscriberInput,
    ResponseFormat,
    _build_imsi,
    _generate_device_name,
    _format_subscriber_for_list,
)
from opensurfcontrol.constants import IMSI_PREFIX, DEFAULT_APN


# ============================================================================
# Helper Function Tests
# ============================================================================

class TestHelperFunctions:
    """Tests for helper functions."""

    def test_build_imsi(self):
        """Test IMSI building from device number."""
        assert _build_imsi("0001") == f"{IMSI_PREFIX}0001"
        assert _build_imsi("9999") == f"{IMSI_PREFIX}9999"

    def test_generate_device_name(self):
        """Test device name generation."""
        assert _generate_device_name("0001") == "DEVICE-0001"
        assert _generate_device_name("9999") == "DEVICE-9999"

    def test_format_subscriber_for_list(self):
        """Test subscriber formatting for list display."""
        subscriber = {
            "imsi": "315010000000001",
            "device_name": "CAM-01",
            "slice": [{
                "session": [{
                    "name": "internet",
                    "ue": {"addr": "10.48.99.10"}
                }]
            }]
        }

        formatted = _format_subscriber_for_list(subscriber)

        assert formatted["imsi"] == "315010000000001"
        assert formatted["name"] == "CAM-01"
        assert formatted["service"] == "internet"
        assert formatted["ip"] == "10.48.99.10"

    def test_format_subscriber_for_list_no_ip(self):
        """Test subscriber formatting without static IP."""
        subscriber = {
            "imsi": "315010000000001",
            "device_name": "CAM-01",
            "slice": [{
                "session": [{
                    "name": "internet"
                }]
            }]
        }

        formatted = _format_subscriber_for_list(subscriber)

        assert formatted["ip"] == "DHCP"


# ============================================================================
# Pydantic Model Tests
# ============================================================================

class TestPydanticModels:
    """Tests for Pydantic input models."""

    def test_add_subscriber_input_valid(self):
        """Test valid AddSubscriberInput."""
        params = AddSubscriberInput(
            device_number="1",
            device_name="CAM-01",
            apn="internet"
        )
        assert params.device_number == "0001"  # Zero-padded
        assert params.device_name == "CAM-01"

    def test_add_subscriber_input_device_number_padding(self):
        """Test device number is zero-padded."""
        params = AddSubscriberInput(device_number="42")
        assert params.device_number == "0042"

    def test_add_subscriber_input_invalid_device_number(self):
        """Test invalid device number."""
        with pytest.raises(ValueError):
            AddSubscriberInput(device_number="0")  # Less than 1

    def test_get_subscriber_input_valid(self):
        """Test valid GetSubscriberInput."""
        params = GetSubscriberInput(imsi="315010000000001")
        assert params.imsi == "315010000000001"

    def test_get_subscriber_input_invalid_imsi(self):
        """Test invalid IMSI (wrong length)."""
        with pytest.raises(ValueError):
            GetSubscriberInput(imsi="12345")  # Too short


# ============================================================================
# MCP Tool Tests
# ============================================================================

class TestListSubscribers:
    """Tests for open5gs_list_subscribers tool."""

    @pytest.mark.asyncio
    @patch('opensurfcontrol.server.get_client')
    async def test_list_subscribers_markdown(self, mock_get_client):
        """Test listing subscribers in markdown format."""
        mock_client = Mock()
        mock_client.list_subscribers.return_value = [
            {
                "imsi": "315010000000001",
                "device_name": "CAM-01",
                "slice": [{"session": [{"name": "internet", "ue": {"addr": "10.48.99.10"}}]}]
            }
        ]
        mock_get_client.return_value = mock_client

        params = BaseInput(response_format=ResponseFormat.MARKDOWN)
        result = await open5gs_list_subscribers(params)

        assert "Open5GS Subscriber List" in result
        assert "CAM-01" in result

    @pytest.mark.asyncio
    @patch('opensurfcontrol.server.get_client')
    async def test_list_subscribers_json(self, mock_get_client):
        """Test listing subscribers in JSON format."""
        mock_client = Mock()
        mock_client.list_subscribers.return_value = [
            {
                "imsi": "315010000000001",
                "device_name": "CAM-01",
                "slice": [{"session": [{"name": "internet"}]}]
            }
        ]
        mock_get_client.return_value = mock_client

        params = BaseInput(response_format=ResponseFormat.JSON)
        result = await open5gs_list_subscribers(params)

        data = json.loads(result)
        assert data["total"] == 1
        assert data["subscribers"][0]["imsi"] == "315010000000001"

    @pytest.mark.asyncio
    @patch('opensurfcontrol.server.get_client')
    async def test_list_subscribers_empty(self, mock_get_client):
        """Test listing subscribers when none exist."""
        mock_client = Mock()
        mock_client.list_subscribers.return_value = []
        mock_get_client.return_value = mock_client

        params = BaseInput(response_format=ResponseFormat.JSON)
        result = await open5gs_list_subscribers(params)

        data = json.loads(result)
        assert data["total"] == 0
        assert data["subscribers"] == []


class TestGetSystemStatus:
    """Tests for open5gs_get_system_status tool."""

    @pytest.mark.asyncio
    @patch('opensurfcontrol.server.get_client')
    async def test_get_system_status_healthy(self, mock_get_client):
        """Test system status when healthy."""
        mock_client = Mock()
        mock_client.get_system_status.return_value = {
            "total_subscribers": 5,
            "core_status": "healthy"
        }
        mock_get_client.return_value = mock_client

        params = BaseInput(response_format=ResponseFormat.JSON)
        result = await open5gs_get_system_status(params)

        data = json.loads(result)
        assert data["subscribers"]["provisioned"] == 5
        assert data["health"]["core_operational"] is True


class TestGetActiveConnections:
    """Tests for open5gs_get_active_connections tool."""

    @pytest.mark.asyncio
    async def test_get_active_connections_placeholder(self):
        """Test active connections returns placeholder (MVP)."""
        params = BaseInput(response_format=ResponseFormat.JSON)
        result = await open5gs_get_active_connections(params)

        data = json.loads(result)
        assert data["total_active"] == 0
        assert "log parsing" in data["note"]


class TestGetNetworkConfig:
    """Tests for open5gs_get_network_config tool."""

    @pytest.mark.asyncio
    async def test_get_network_config_markdown(self):
        """Test network config in markdown format."""
        params = BaseInput(response_format=ResponseFormat.MARKDOWN)
        result = await open5gs_get_network_config(params)

        assert "Open5GS Network Configuration" in result
        assert "315010" in result  # PLMNID

    @pytest.mark.asyncio
    async def test_get_network_config_json(self):
        """Test network config in JSON format."""
        params = BaseInput(response_format=ResponseFormat.JSON)
        result = await open5gs_get_network_config(params)

        data = json.loads(result)
        assert data["network_identity"]["plmnid"] == "315010"
        assert data["network_identity"]["mcc"] == "315"
        assert data["network_identity"]["mnc"] == "010"


class TestAddSubscriber:
    """Tests for open5gs_add_subscriber tool."""

    @pytest.mark.asyncio
    @patch('opensurfcontrol.server.get_client')
    async def test_add_subscriber_success(self, mock_get_client):
        """Test successful subscriber addition."""
        mock_client = Mock()
        mock_client.add_subscriber.return_value = {
            "imsi": "315010000000001",
            "device_name": "CAM-01"
        }
        mock_get_client.return_value = mock_client

        params = AddSubscriberInput(
            device_number="1",
            device_name="CAM-01",
            apn="internet"
        )
        result = await open5gs_add_subscriber(params)

        data = json.loads(result)
        assert data["success"] is True
        assert data["subscriber"]["name"] == "CAM-01"

    @pytest.mark.asyncio
    @patch('opensurfcontrol.server.get_client')
    async def test_add_subscriber_with_static_ip(self, mock_get_client):
        """Test adding subscriber with static IP."""
        mock_client = Mock()
        mock_client.add_subscriber.return_value = {
            "imsi": "315010000000001",
            "device_name": "CAM-01"
        }
        mock_get_client.return_value = mock_client

        params = AddSubscriberInput(
            device_number="1",
            device_name="CAM-01",
            ip="10.48.99.10"
        )
        result = await open5gs_add_subscriber(params)

        data = json.loads(result)
        assert data["success"] is True
        assert data["subscriber"]["ip"] == "10.48.99.10"


class TestGetSubscriber:
    """Tests for open5gs_get_subscriber tool."""

    @pytest.mark.asyncio
    @patch('opensurfcontrol.server.get_client')
    async def test_get_subscriber_found(self, mock_get_client):
        """Test getting an existing subscriber."""
        mock_client = Mock()
        mock_client.get_subscriber.return_value = {
            "imsi": "315010000000001",
            "device_name": "CAM-01",
            "slice": [{"session": [{"name": "internet"}]}]
        }
        mock_get_client.return_value = mock_client

        params = GetSubscriberInput(imsi="315010000000001")
        result = await open5gs_get_subscriber(params)

        data = json.loads(result)
        assert data["success"] is True
        assert data["name"] == "CAM-01"

    @pytest.mark.asyncio
    @patch('opensurfcontrol.server.get_client')
    async def test_get_subscriber_not_found(self, mock_get_client):
        """Test getting a non-existent subscriber."""
        mock_client = Mock()
        mock_client.get_subscriber.return_value = None
        mock_get_client.return_value = mock_client

        params = GetSubscriberInput(imsi="315010000000999")
        result = await open5gs_get_subscriber(params)

        data = json.loads(result)
        assert data["success"] is False
        assert "not found" in data["error"]


class TestDeleteSubscriber:
    """Tests for open5gs_delete_subscriber tool."""

    @pytest.mark.asyncio
    @patch('opensurfcontrol.server.get_client')
    async def test_delete_subscriber_success(self, mock_get_client):
        """Test successful subscriber deletion."""
        mock_client = Mock()
        mock_client.get_subscriber.return_value = {"imsi": "315010000000001"}
        mock_client.delete_subscriber.return_value = True
        mock_get_client.return_value = mock_client

        params = DeleteSubscriberInput(imsi="315010000000001")
        result = await open5gs_delete_subscriber(params)

        data = json.loads(result)
        assert data["success"] is True

    @pytest.mark.asyncio
    @patch('opensurfcontrol.server.get_client')
    async def test_delete_subscriber_not_found(self, mock_get_client):
        """Test deleting a non-existent subscriber."""
        mock_client = Mock()
        mock_client.get_subscriber.return_value = None
        mock_get_client.return_value = mock_client

        params = DeleteSubscriberInput(imsi="315010000000999")
        result = await open5gs_delete_subscriber(params)

        data = json.loads(result)
        assert data["success"] is False
        assert "not found" in data["error"]


class TestUpdateSubscriber:
    """Tests for open5gs_update_subscriber tool."""

    @pytest.mark.asyncio
    @patch('opensurfcontrol.server.get_client')
    async def test_update_subscriber_success(self, mock_get_client):
        """Test successful subscriber update."""
        mock_client = Mock()
        mock_client.get_subscriber.return_value = {"imsi": "315010000000001"}
        mock_client.update_subscriber.return_value = True
        mock_get_client.return_value = mock_client

        params = UpdateSubscriberInput(
            imsi="315010000000001",
            device_name="CAM-01-Updated"
        )
        result = await open5gs_update_subscriber(params)

        data = json.loads(result)
        assert data["success"] is True
        assert "CAM-01-Updated" in str(data["changes"])

    @pytest.mark.asyncio
    async def test_update_subscriber_no_fields(self):
        """Test update with no fields provided."""
        params = UpdateSubscriberInput(imsi="315010000000001")
        result = await open5gs_update_subscriber(params)

        data = json.loads(result)
        assert data["success"] is False
        assert "must be provided" in data["error"]
