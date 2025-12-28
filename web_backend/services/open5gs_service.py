"""
Open5GS Service for the Open5G2GO Web Backend.

Provides high-level operations for subscriber management
by wrapping the Open5GS MongoDB client.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from opensurfcontrol.mongodb_client import Open5GSClient, get_client
from opensurfcontrol.mme_client import get_mme_parser
from opensurfcontrol.constants import (
    IMSI_PREFIX,
    DEFAULT_APN,
    DEFAULT_K,
    DEFAULT_OPC,
    DEFAULT_AMBR_UL,
    DEFAULT_AMBR_DL,
    PLMNID,
    MCC,
    MNC,
    TAC,
    NETWORK_NAME_SHORT,
    UE_POOL_START,
    UE_POOL_END,
)

logger = logging.getLogger(__name__)


class Open5GSService:
    """Service layer for Open5GS operations."""

    def __init__(self, client: Optional[Open5GSClient] = None):
        """
        Initialize the service.

        Args:
            client: Optional Open5GS client. Uses singleton if not provided.
        """
        self._client = client

    @property
    def client(self) -> Open5GSClient:
        """Get the Open5GS client, creating if needed."""
        if self._client is None:
            self._client = get_client()
        return self._client

    def _timestamp(self) -> str:
        """Get current timestamp string."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    async def list_subscribers(self) -> Dict[str, Any]:
        """
        List all provisioned subscribers.

        Returns:
            Dictionary with subscriber list and metadata.
        """
        try:
            subscribers = self.client.list_subscribers()

            # Transform to API format
            subscriber_list = []
            for sub in subscribers:
                subscriber_list.append({
                    "imsi": sub.get("imsi", ""),
                    "name": sub.get("device_name", f"Device-{sub.get('imsi', '')[-4:]}"),
                    "ip": self._get_subscriber_ip(sub),
                    "apn": self._get_subscriber_apn(sub),
                })

            return {
                "timestamp": self._timestamp(),
                "total": len(subscriber_list),
                "subscribers": subscriber_list
            }
        except Exception as e:
            logger.error(f"Error listing subscribers: {e}")
            return {"error": str(e), "timestamp": self._timestamp()}

    async def get_subscriber(self, imsi: str) -> Dict[str, Any]:
        """
        Get subscriber details by IMSI.

        Args:
            imsi: The 15-digit IMSI.

        Returns:
            Subscriber details or error.
        """
        try:
            subscriber = self.client.get_subscriber(imsi)

            if subscriber is None:
                return {
                    "success": False,
                    "error": f"Subscriber with IMSI {imsi} not found"
                }

            return {
                "success": True,
                "imsi": imsi,
                "data": subscriber
            }
        except Exception as e:
            logger.error(f"Error getting subscriber {imsi}: {e}")
            return {"success": False, "error": str(e)}

    async def add_subscriber(
        self,
        device_number: int,
        name: Optional[str] = None,
        apn: str = DEFAULT_APN,
        ip: Optional[str] = None,
        imsi: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add a new subscriber.

        Args:
            device_number: The device number (last 4 digits of IMSI).
            name: Optional device name.
            apn: Access Point Name.
            ip: Optional static IP address.
            imsi: Optional full IMSI (overrides device_number calculation).

        Returns:
            Result with subscriber details.
        """
        try:
            # Build IMSI from device number if not provided
            if imsi is None:
                imsi = f"{IMSI_PREFIX}{str(device_number).zfill(4)}"

            # Generate device name if not provided
            if name is None:
                name = f"Device-{str(device_number).zfill(4)}"

            # Calculate IP if not provided
            if ip is None:
                ip = self._calculate_ip(device_number)

            # Add subscriber
            subscriber = self.client.add_subscriber(
                imsi=imsi,
                k=DEFAULT_K,
                opc=DEFAULT_OPC,
                apn=apn,
                ip=ip,
                ambr_ul=DEFAULT_AMBR_UL,
                ambr_dl=DEFAULT_AMBR_DL,
                device_name=name,
            )

            return {
                "success": True,
                "timestamp": self._timestamp(),
                "subscriber": {
                    "imsi": imsi,
                    "name": name,
                    "ip": ip,
                    "apn": apn
                }
            }
        except Exception as e:
            logger.error(f"Error adding subscriber: {e}")
            return {
                "success": False,
                "timestamp": self._timestamp(),
                "error": str(e)
            }

    async def update_subscriber(
        self,
        imsi: str,
        ip: Optional[str] = None,
        apn: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update subscriber details.

        Args:
            imsi: The IMSI to update.
            ip: New IP address.
            apn: New APN.
            name: New device name.

        Returns:
            Update result.
        """
        try:
            # Build updates dictionary
            updates = {}
            changes = []

            if name is not None:
                updates["device_name"] = name
                changes.append(f"name → {name}")

            # For IP and APN, we need to update the slice/session configuration
            # This requires more complex updates to the nested structure
            if ip is not None or apn is not None:
                # Get current subscriber
                current = self.client.get_subscriber(imsi)
                if current is None:
                    return {
                        "success": False,
                        "error": f"Subscriber with IMSI {imsi} not found"
                    }

                # Update the slice configuration
                if "slice" in current and len(current["slice"]) > 0:
                    slice_config = current["slice"][0]
                    if "session" in slice_config and len(slice_config["session"]) > 0:
                        session = slice_config["session"][0]
                        if apn is not None:
                            session["name"] = apn
                            changes.append(f"apn → {apn}")
                        if ip is not None:
                            session["ue"] = {"addr": ip}
                            changes.append(f"ip → {ip}")
                        updates["slice"] = current["slice"]

            if not updates:
                return {
                    "success": False,
                    "error": "No valid updates provided"
                }

            success = self.client.update_subscriber(imsi, **updates)

            if success:
                return {
                    "success": True,
                    "imsi": imsi,
                    "changes": changes,
                    "message": f"Subscriber updated: {', '.join(changes)}"
                }
            else:
                return {
                    "success": False,
                    "error": "No changes made (subscriber may not exist)"
                }
        except Exception as e:
            logger.error(f"Error updating subscriber {imsi}: {e}")
            return {"success": False, "error": str(e)}

    async def delete_subscriber(self, imsi: str) -> Dict[str, Any]:
        """
        Delete a subscriber.

        Args:
            imsi: The IMSI to delete.

        Returns:
            Deletion result.
        """
        try:
            success = self.client.delete_subscriber(imsi)

            if success:
                return {
                    "success": True,
                    "message": f"Subscriber {imsi} deleted successfully"
                }
            else:
                return {
                    "success": False,
                    "error": f"Subscriber with IMSI {imsi} not found"
                }
        except Exception as e:
            logger.error(f"Error deleting subscriber {imsi}: {e}")
            return {"success": False, "error": str(e)}

    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get system status including eNodeB connections from MME logs.

        Returns:
            System status information.
        """
        try:
            status = self.client.get_system_status()
            health_ok = self.client.health_check()

            # Get eNodeB connection status from MME logs
            mme_parser = get_mme_parser()
            enodebs = mme_parser.get_connected_enodebs()
            enb_count = len(enodebs)

            return {
                "timestamp": self._timestamp(),
                "system_name": "Open5G2GO",
                "subscribers": {
                    "provisioned": status.get("total_subscribers", 0),
                    "registered": 0,  # Would need real-time tracking
                    "connected": 0    # Would need real-time tracking
                },
                "enodebs": {
                    "total": enb_count,
                    "list": enodebs
                },
                "health": {
                    "core_operational": health_ok,
                    "database_connected": status.get("connection") == "connected",
                    "has_active_connections": enb_count > 0,
                    "enodebs_connected": enb_count > 0
                }
            }
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e), "timestamp": self._timestamp()}

    async def get_network_config(self) -> Dict[str, Any]:
        """
        Get network configuration.

        Returns:
            Network configuration details.
        """
        return {
            "timestamp": self._timestamp(),
            "network_identity": {
                "plmnid": PLMNID,
                "mcc": MCC,
                "mnc": MNC,
                "network_name": NETWORK_NAME_SHORT,
                "tac": str(TAC)
            },
            "apns": {
                "total": 1,
                "list": [
                    {
                        "name": DEFAULT_APN,
                        "downlink_mbps": DEFAULT_AMBR_DL // 1000000,
                        "uplink_mbps": DEFAULT_AMBR_UL // 1000000
                    }
                ]
            },
            "ip_pool": {
                "start": UE_POOL_START,
                "end": UE_POOL_END
            }
        }

    async def get_active_connections(self) -> Dict[str, Any]:
        """
        Get active connections.

        Note: This requires real-time monitoring which is not yet implemented.
        Returns placeholder data for MVP.

        Returns:
            Active connections information.
        """
        return {
            "timestamp": self._timestamp(),
            "total_active": 0,
            "connections": [],
            "note": "Real-time connection tracking requires log parsing (Phase 2)"
        }

    def _get_subscriber_ip(self, subscriber: Dict[str, Any]) -> Optional[str]:
        """Extract IP address from subscriber document."""
        try:
            slice_data = subscriber.get("slice", [])
            if slice_data and len(slice_data) > 0:
                session = slice_data[0].get("session", [])
                if session and len(session) > 0:
                    ue = session[0].get("ue", {})
                    return ue.get("addr")
        except (KeyError, IndexError):
            pass
        return None

    def _get_subscriber_apn(self, subscriber: Dict[str, Any]) -> str:
        """Extract APN from subscriber document."""
        try:
            slice_data = subscriber.get("slice", [])
            if slice_data and len(slice_data) > 0:
                session = slice_data[0].get("session", [])
                if session and len(session) > 0:
                    return session[0].get("name", DEFAULT_APN)
        except (KeyError, IndexError):
            pass
        return DEFAULT_APN

    def _calculate_ip(self, device_number: int) -> str:
        """
        Calculate IP address for device number.

        Uses the 10.48.99.0/24 pool with device_number as last octet.
        """
        # Ensure device_number is within valid range (2-254)
        last_octet = max(2, min(254, device_number + 1))
        return f"10.48.99.{last_octet}"


# Singleton service instance
_service_instance: Optional[Open5GSService] = None


def get_open5gs_service() -> Open5GSService:
    """Get or create the singleton service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = Open5GSService()
    return _service_instance
