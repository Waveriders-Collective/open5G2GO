"""
MongoDB adapter for Open5GS subscriber management.

This module provides the Open5GSClient class that interfaces with Open5GS MongoDB
to manage subscriber data. It replaces the SSH-based Attocore adapter.
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from typing import List, Optional, Dict, Any
import os
import logging
import re
import threading

from .constants import (
    MONGODB_URI,
    MONGODB_DATABASE,
    IMSI_PREFIX,
    DEFAULT_APN,
    DEFAULT_K,
    DEFAULT_OPC,
    DEFAULT_AMBR_UL,
    DEFAULT_AMBR_DL,
    DEFAULT_QCI,
    DEFAULT_ARP_PRIORITY,
)

logger = logging.getLogger(__name__)


class Open5GSClientError(Exception):
    """Base exception for Open5GS client errors."""
    pass


class MongoDBConnectionError(Open5GSClientError):
    """Raised when MongoDB connection fails."""
    pass


class SubscriberError(Open5GSClientError):
    """Raised when subscriber operations fail."""
    pass


class ValidationError(Open5GSClientError):
    """Raised when input validation fails."""
    pass


# Whitelist of fields that can be updated via update_subscriber
ALLOWED_UPDATE_FIELDS = frozenset(['device_name', 'slice', 'ambr'])


def _validate_imsi(imsi: str) -> None:
    """
    Validate IMSI format.

    Args:
        imsi: The IMSI to validate.

    Raises:
        ValidationError: If IMSI format is invalid.
    """
    if not isinstance(imsi, str):
        raise ValidationError("IMSI must be a string")
    if not imsi.isdigit():
        raise ValidationError("IMSI must contain only digits")
    if len(imsi) != 15:
        raise ValidationError(f"IMSI must be exactly 15 digits, got {len(imsi)}")


def _validate_hex_key(key: str, name: str) -> None:
    """
    Validate authentication key format (32-character hex string).

    Args:
        key: The key to validate.
        name: Name of the key for error messages.

    Raises:
        ValidationError: If key format is invalid.
    """
    if not isinstance(key, str):
        raise ValidationError(f"{name} must be a string")
    if len(key) != 32:
        raise ValidationError(f"{name} must be exactly 32 characters, got {len(key)}")
    if not re.match(r'^[0-9A-Fa-f]+$', key):
        raise ValidationError(f"{name} must contain only hex characters (0-9, A-F)")


class Open5GSClient:
    """MongoDB adapter for Open5GS subscriber management."""

    def __init__(self, uri: Optional[str] = None):
        """
        Initialize the Open5GS client.

        Args:
            uri: MongoDB connection URI. Defaults to MONGODB_URI from environment.
        """
        self.uri = uri or os.getenv("MONGODB_URI", MONGODB_URI)
        self._client: Optional[MongoClient] = None
        self._db = None
        self._subscribers = None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False

    def connect(self) -> None:
        """Establish connection to MongoDB."""
        try:
            self._client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            # Test connection
            self._client.admin.command('ping')
            self._db = self._client[MONGODB_DATABASE]
            self._subscribers = self._db.subscribers
            logger.info(f"Connected to MongoDB at {self.uri}")
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise MongoDBConnectionError(f"Failed to connect to MongoDB: {e}")

    def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._subscribers = None
            logger.info("Disconnected from MongoDB")

    def _ensure_connected(self) -> None:
        """Ensure MongoDB connection is established."""
        if self._client is None:
            self.connect()

    @property
    def subscribers(self):
        """Get subscribers collection, connecting if needed."""
        self._ensure_connected()
        return self._subscribers

    def list_subscribers(self) -> List[Dict[str, Any]]:
        """
        List all provisioned subscribers.

        Returns:
            List of subscriber documents.
        """
        try:
            return list(self.subscribers.find({}, {"_id": 0}))
        except OperationFailure as e:
            logger.error(f"Failed to list subscribers: {e}")
            raise SubscriberError(f"Failed to list subscribers: {e}")

    def get_subscriber(self, imsi: str) -> Optional[Dict[str, Any]]:
        """
        Get subscriber by IMSI.

        Args:
            imsi: The 15-digit IMSI.

        Returns:
            Subscriber document or None if not found.

        Raises:
            ValidationError: If IMSI format is invalid.
        """
        _validate_imsi(imsi)
        try:
            return self.subscribers.find_one({"imsi": imsi}, {"_id": 0})
        except OperationFailure as e:
            logger.error(f"Failed to get subscriber {imsi}: {e}")
            raise SubscriberError(f"Failed to get subscriber: {e}")

    def add_subscriber(
        self,
        imsi: str,
        k: Optional[str] = None,
        opc: Optional[str] = None,
        apn: str = DEFAULT_APN,
        ip: Optional[str] = None,
        ambr_ul: int = DEFAULT_AMBR_UL,
        ambr_dl: int = DEFAULT_AMBR_DL,
        device_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add new subscriber with QoS settings.

        Args:
            imsi: The 15-digit IMSI.
            k: Authentication key (32-char hex). Uses DEFAULT_K if not provided.
            opc: Operator key (32-char hex). Uses DEFAULT_OPC if not provided.
            apn: Access Point Name. Defaults to "internet".
            ip: Static IP address (optional).
            ambr_ul: Uplink AMBR in bps.
            ambr_dl: Downlink AMBR in bps.
            device_name: Optional friendly name for the device.

        Returns:
            The created subscriber document.

        Raises:
            ValidationError: If input validation fails.
            SubscriberError: If database operation fails.
        """
        # Validate IMSI
        _validate_imsi(imsi)

        # Use defaults and validate keys
        k = k or DEFAULT_K
        opc = opc or DEFAULT_OPC
        _validate_hex_key(k, "Authentication key (k)")
        _validate_hex_key(opc, "Operator key (opc)")

        # Build session configuration
        session_config: Dict[str, Any] = {
            "name": apn,
            "type": 3,  # IPv4
            "qos": {
                "index": DEFAULT_QCI,
                "arp": {
                    "priority_level": DEFAULT_ARP_PRIORITY,
                    "pre_emption_capability": 1,
                    "pre_emption_vulnerability": 1
                }
            },
            "ambr": {
                "uplink": {"value": ambr_ul // 1000, "unit": 0},
                "downlink": {"value": ambr_dl // 1000, "unit": 0}
            }
        }

        # Add static IP if provided
        if ip:
            session_config["ue"] = {"addr": ip}

        subscriber = {
            "imsi": imsi,
            "security": {
                "k": k,
                "amf": "8000",
                "op": None,
                "opc": opc
            },
            "ambr": {
                "uplink": {"value": ambr_ul // 1000, "unit": 0},
                "downlink": {"value": ambr_dl // 1000, "unit": 0}
            },
            "slice": [{
                "sst": 1,
                "default_indicator": True,
                "session": [session_config]
            }]
        }

        # Add device name as custom field if provided
        if device_name:
            subscriber["device_name"] = device_name

        try:
            self.subscribers.update_one(
                {"imsi": imsi},
                {"$set": subscriber},
                upsert=True
            )
            logger.info(f"Added/updated subscriber: {imsi}")
            return subscriber
        except OperationFailure as e:
            logger.error(f"Failed to add subscriber {imsi}: {e}")
            raise SubscriberError(f"Failed to add subscriber: {e}")

    def update_subscriber(self, imsi: str, **updates) -> bool:
        """
        Update subscriber fields.

        Only whitelisted fields can be updated for security:
        - device_name: The friendly device name
        - slice: Network slice configuration
        - ambr: Aggregate Maximum Bit Rate

        Security fields (imsi, security.k, security.opc) cannot be modified.

        Args:
            imsi: The IMSI to update.
            **updates: Field updates to apply (only whitelisted fields).

        Returns:
            True if subscriber was modified, False otherwise.

        Raises:
            ValidationError: If IMSI format is invalid.
            SubscriberError: If database operation fails.
        """
        _validate_imsi(imsi)

        # Filter updates to only allow whitelisted fields
        validated_updates = {
            k: v for k, v in updates.items()
            if k in ALLOWED_UPDATE_FIELDS
        }

        if not validated_updates:
            logger.warning(f"No valid fields to update for {imsi}. "
                          f"Allowed fields: {ALLOWED_UPDATE_FIELDS}")
            return False

        # Log any filtered fields
        filtered_fields = set(updates.keys()) - set(validated_updates.keys())
        if filtered_fields:
            logger.warning(f"Filtered out non-whitelisted fields: {filtered_fields}")

        try:
            result = self.subscribers.update_one(
                {"imsi": imsi},
                {"$set": validated_updates}
            )
            if result.modified_count > 0:
                logger.info(f"Updated subscriber: {imsi}")
                return True
            return False
        except OperationFailure as e:
            logger.error(f"Failed to update subscriber {imsi}: {e}")
            raise SubscriberError(f"Failed to update subscriber: {e}")

    def delete_subscriber(self, imsi: str) -> bool:
        """
        Remove subscriber.

        Args:
            imsi: The IMSI to delete.

        Returns:
            True if subscriber was deleted, False otherwise.

        Raises:
            ValidationError: If IMSI format is invalid.
            SubscriberError: If database operation fails.
        """
        _validate_imsi(imsi)
        try:
            result = self.subscribers.delete_one({"imsi": imsi})
            if result.deleted_count > 0:
                logger.info(f"Deleted subscriber: {imsi}")
                return True
            return False
        except OperationFailure as e:
            logger.error(f"Failed to delete subscriber {imsi}: {e}")
            raise SubscriberError(f"Failed to delete subscriber: {e}")

    def get_subscriber_count(self) -> int:
        """Get total number of subscribers."""
        try:
            return self.subscribers.count_documents({})
        except OperationFailure as e:
            logger.error(f"Failed to count subscribers: {e}")
            raise SubscriberError(f"Failed to count subscribers: {e}")

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get system status including subscriber counts.

        Returns:
            Dictionary with system status information.
        """
        try:
            total = self.get_subscriber_count()
            return {
                "total_subscribers": total,
                "core_status": "healthy",
                "database": MONGODB_DATABASE,
                "connection": "connected"
            }
        except Exception as e:
            return {
                "total_subscribers": 0,
                "core_status": "error",
                "database": MONGODB_DATABASE,
                "connection": "disconnected",
                "error": str(e)
            }

    def build_imsi(self, device_number: str) -> str:
        """
        Build full IMSI from device number.

        The user enters only the last 4 digits, and we prepend the IMSI prefix.

        Args:
            device_number: Last 4 digits of IMSI (e.g., "0001").

        Returns:
            Full 15-digit IMSI (e.g., "315010000000001").
        """
        # Pad device number to 4 digits
        padded = device_number.zfill(4)
        return f"{IMSI_PREFIX}{padded}"

    def health_check(self) -> bool:
        """
        Check if MongoDB connection is healthy.

        Returns:
            True if connection is healthy, False otherwise.
        """
        try:
            self._ensure_connected()
            self._client.admin.command('ping')
            return True
        except Exception:
            return False


# Thread-safe singleton implementation
_client_instance: Optional[Open5GSClient] = None
_client_lock = threading.Lock()


def get_client() -> Open5GSClient:
    """
    Get or create the singleton Open5GS client instance.

    Thread-safe implementation using double-checked locking.
    """
    global _client_instance
    if _client_instance is None:
        with _client_lock:
            # Double-check after acquiring lock
            if _client_instance is None:
                _client_instance = Open5GSClient()
    return _client_instance
