# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Waveriders Collective Inc.

"""
Unit tests for opensurfcontrol.mongodb_client module.

Tests the Open5GS MongoDB adapter for subscriber management.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from opensurfcontrol.mongodb_client import (
    Open5GSClient,
    get_client,
    MongoDBConnectionError,
    SubscriberError,
    ValidationError,
    _validate_imsi,
    _validate_hex_key,
)
from opensurfcontrol.constants import (
    DEFAULT_K,
    DEFAULT_OPC,
    DEFAULT_APN,
    DEFAULT_AMBR_UL,
    DEFAULT_AMBR_DL,
    IMSI_PREFIX,
)


# ============================================================================
# Validation Tests
# ============================================================================

class TestIMSIValidation:
    """Tests for IMSI validation."""

    def test_valid_imsi(self):
        """Valid 15-digit IMSI should pass validation."""
        _validate_imsi("315010000000001")  # Should not raise

    def test_imsi_not_string(self):
        """Non-string IMSI should raise ValidationError."""
        with pytest.raises(ValidationError, match="must be a string"):
            _validate_imsi(315010000000001)

    def test_imsi_non_numeric(self):
        """IMSI with non-numeric characters should raise ValidationError."""
        with pytest.raises(ValidationError, match="only digits"):
            _validate_imsi("31501000000000A")

    def test_imsi_wrong_length(self):
        """IMSI with wrong length should raise ValidationError."""
        with pytest.raises(ValidationError, match="exactly 15 digits"):
            _validate_imsi("31501000000")


class TestHexKeyValidation:
    """Tests for hex key (K/OPc) validation."""

    def test_valid_hex_key(self):
        """Valid 32-character hex key should pass validation."""
        _validate_hex_key("465B5CE8B199B49FAA5F0A2EE238A6BC", "K")

    def test_hex_key_not_string(self):
        """Non-string key should raise ValidationError."""
        with pytest.raises(ValidationError, match="must be a string"):
            _validate_hex_key(12345, "K")

    def test_hex_key_wrong_length(self):
        """Key with wrong length should raise ValidationError."""
        with pytest.raises(ValidationError, match="exactly 32 characters"):
            _validate_hex_key("ABCD", "K")

    def test_hex_key_invalid_chars(self):
        """Key with non-hex characters should raise ValidationError."""
        with pytest.raises(ValidationError, match="hex characters"):
            _validate_hex_key("GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG", "K")


# ============================================================================
# Open5GSClient Tests
# ============================================================================

class TestOpen5GSClient:
    """Tests for Open5GSClient class."""

    @patch('opensurfcontrol.mongodb_client.MongoClient')
    def test_connect_success(self, mock_mongo_client):
        """Test successful MongoDB connection."""
        mock_client = MagicMock()
        mock_client.admin.command.return_value = {'ok': 1}
        mock_mongo_client.return_value = mock_client

        client = Open5GSClient(uri="mongodb://localhost:27017")
        client.connect()

        mock_mongo_client.assert_called_once()
        mock_client.admin.command.assert_called_once_with('ping')

    @patch('opensurfcontrol.mongodb_client.MongoClient')
    def test_connect_failure(self, mock_mongo_client):
        """Test MongoDB connection failure."""
        from pymongo.errors import ConnectionFailure
        mock_mongo_client.side_effect = ConnectionFailure("Connection refused")

        client = Open5GSClient(uri="mongodb://localhost:27017")

        with pytest.raises(MongoDBConnectionError):
            client.connect()

    @patch('opensurfcontrol.mongodb_client.MongoClient')
    def test_list_subscribers(self, mock_mongo_client):
        """Test listing subscribers."""
        mock_collection = Mock()
        mock_collection.find.return_value = [
            {"imsi": "315010000000001", "device_name": "CAM-01"},
            {"imsi": "315010000000002", "device_name": "CAM-02"},
        ]
        mock_db = Mock()
        mock_db.subscribers = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_client.admin.command.return_value = {'ok': 1}
        mock_mongo_client.return_value = mock_client

        client = Open5GSClient()
        client.connect()
        subscribers = client.list_subscribers()

        assert len(subscribers) == 2
        assert subscribers[0]["imsi"] == "315010000000001"
        mock_collection.find.assert_called_once_with({}, {"_id": 0})

    @patch('opensurfcontrol.mongodb_client.MongoClient')
    def test_get_subscriber_found(self, mock_mongo_client):
        """Test getting an existing subscriber."""
        mock_collection = Mock()
        mock_collection.find_one.return_value = {
            "imsi": "315010000000001",
            "device_name": "CAM-01"
        }
        mock_db = Mock()
        mock_db.subscribers = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_client.admin.command.return_value = {'ok': 1}
        mock_mongo_client.return_value = mock_client

        client = Open5GSClient()
        client.connect()
        subscriber = client.get_subscriber("315010000000001")

        assert subscriber is not None
        assert subscriber["imsi"] == "315010000000001"

    @patch('opensurfcontrol.mongodb_client.MongoClient')
    def test_get_subscriber_not_found(self, mock_mongo_client):
        """Test getting a non-existent subscriber."""
        mock_collection = Mock()
        mock_collection.find_one.return_value = None
        mock_db = Mock()
        mock_db.subscribers = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_client.admin.command.return_value = {'ok': 1}
        mock_mongo_client.return_value = mock_client

        client = Open5GSClient()
        client.connect()
        subscriber = client.get_subscriber("315010000000999")

        assert subscriber is None

    @patch('opensurfcontrol.mongodb_client.MongoClient')
    def test_add_subscriber(self, mock_mongo_client):
        """Test adding a new subscriber."""
        mock_collection = Mock()
        mock_collection.update_one.return_value = Mock(upserted_id="123")
        mock_db = Mock()
        mock_db.subscribers = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_client.admin.command.return_value = {'ok': 1}
        mock_mongo_client.return_value = mock_client

        client = Open5GSClient()
        client.connect()
        subscriber = client.add_subscriber(
            imsi="315010000000001",
            k=DEFAULT_K,
            opc=DEFAULT_OPC,
            apn="internet",
            ip="10.48.99.10",
            device_name="CAM-01"
        )

        assert subscriber["imsi"] == "315010000000001"
        assert subscriber["device_name"] == "CAM-01"
        mock_collection.update_one.assert_called_once()

    @patch('opensurfcontrol.mongodb_client.MongoClient')
    def test_add_subscriber_with_defaults(self, mock_mongo_client):
        """Test adding a subscriber with default K/OPc."""
        mock_collection = Mock()
        mock_collection.update_one.return_value = Mock(upserted_id="123")
        mock_db = Mock()
        mock_db.subscribers = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_client.admin.command.return_value = {'ok': 1}
        mock_mongo_client.return_value = mock_client

        client = Open5GSClient()
        client.connect()
        subscriber = client.add_subscriber(
            imsi="315010000000001",
            device_name="CAM-01"
        )

        # Should use default K/OPc
        assert subscriber["security"]["k"] == DEFAULT_K
        assert subscriber["security"]["opc"] == DEFAULT_OPC

    @patch('opensurfcontrol.mongodb_client.MongoClient')
    def test_delete_subscriber_success(self, mock_mongo_client):
        """Test deleting an existing subscriber."""
        mock_collection = Mock()
        mock_collection.delete_one.return_value = Mock(deleted_count=1)
        mock_db = Mock()
        mock_db.subscribers = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_client.admin.command.return_value = {'ok': 1}
        mock_mongo_client.return_value = mock_client

        client = Open5GSClient()
        client.connect()
        deleted = client.delete_subscriber("315010000000001")

        assert deleted is True
        mock_collection.delete_one.assert_called_once_with({"imsi": "315010000000001"})

    @patch('opensurfcontrol.mongodb_client.MongoClient')
    def test_delete_subscriber_not_found(self, mock_mongo_client):
        """Test deleting a non-existent subscriber."""
        mock_collection = Mock()
        mock_collection.delete_one.return_value = Mock(deleted_count=0)
        mock_db = Mock()
        mock_db.subscribers = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_client.admin.command.return_value = {'ok': 1}
        mock_mongo_client.return_value = mock_client

        client = Open5GSClient()
        client.connect()
        deleted = client.delete_subscriber("315010000000999")

        assert deleted is False

    @patch('opensurfcontrol.mongodb_client.MongoClient')
    def test_update_subscriber_allowed_fields(self, mock_mongo_client):
        """Test updating subscriber with allowed fields."""
        mock_collection = Mock()
        mock_collection.update_one.return_value = Mock(modified_count=1)
        mock_db = Mock()
        mock_db.subscribers = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_client.admin.command.return_value = {'ok': 1}
        mock_mongo_client.return_value = mock_client

        client = Open5GSClient()
        client.connect()
        updated = client.update_subscriber(
            "315010000000001",
            device_name="CAM-01-Updated"
        )

        assert updated is True

    @patch('opensurfcontrol.mongodb_client.MongoClient')
    def test_update_subscriber_filtered_fields(self, mock_mongo_client):
        """Test that security fields are filtered from updates."""
        mock_collection = Mock()
        mock_db = Mock()
        mock_db.subscribers = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_client.admin.command.return_value = {'ok': 1}
        mock_mongo_client.return_value = mock_client

        client = Open5GSClient()
        client.connect()

        # Try to update security fields (should be filtered)
        updated = client.update_subscriber(
            "315010000000001",
            security={"k": "MALICIOUSKEY"}  # Should be filtered
        )

        # Should return False because no valid fields were provided
        assert updated is False

    @patch('opensurfcontrol.mongodb_client.MongoClient')
    def test_get_system_status(self, mock_mongo_client):
        """Test getting system status."""
        mock_collection = Mock()
        mock_collection.count_documents.return_value = 5
        mock_db = Mock()
        mock_db.subscribers = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_client.admin.command.return_value = {'ok': 1}
        mock_mongo_client.return_value = mock_client

        client = Open5GSClient()
        client.connect()
        status = client.get_system_status()

        assert status["total_subscribers"] == 5
        assert status["core_status"] == "healthy"

    def test_build_imsi(self):
        """Test IMSI building from device number."""
        client = Open5GSClient()
        imsi = client.build_imsi("0001")
        assert imsi == f"{IMSI_PREFIX}0001"

        imsi = client.build_imsi("1")
        assert imsi == f"{IMSI_PREFIX}0001"

    @patch('opensurfcontrol.mongodb_client.MongoClient')
    def test_health_check_healthy(self, mock_mongo_client):
        """Test health check when MongoDB is healthy."""
        mock_client = MagicMock()
        mock_client.admin.command.return_value = {'ok': 1}
        mock_mongo_client.return_value = mock_client

        client = Open5GSClient()
        client.connect()
        assert client.health_check() is True

    @patch('opensurfcontrol.mongodb_client.MongoClient')
    def test_context_manager(self, mock_mongo_client):
        """Test using client as context manager."""
        mock_client = MagicMock()
        mock_client.admin.command.return_value = {'ok': 1}
        mock_mongo_client.return_value = mock_client

        with Open5GSClient() as client:
            assert client._client is not None

        mock_client.close.assert_called_once()


# ============================================================================
# Singleton Tests
# ============================================================================

class TestGetClient:
    """Tests for get_client singleton function."""

    @patch('opensurfcontrol.mongodb_client._client_instance', None)
    @patch('opensurfcontrol.mongodb_client.Open5GSClient')
    def test_get_client_creates_singleton(self, mock_client_class):
        """Test that get_client creates a singleton instance."""
        mock_instance = Mock()
        mock_client_class.return_value = mock_instance

        client1 = get_client()
        client2 = get_client()

        # Should return the same instance
        assert client1 is client2
