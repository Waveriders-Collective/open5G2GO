"""
Open5GS Service for the Open5G2GO Web Backend.

Provides high-level operations for subscriber management
by wrapping the Open5GS MongoDB client.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

import yaml
from pathlib import Path

from opensurfcontrol.mongodb_client import Open5GSClient, get_client
from opensurfcontrol.mme_client import get_mme_parser
from opensurfcontrol.snmp_client import get_snmp_client
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


def load_enodeb_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load eNodeB configuration from YAML file.

    Args:
        config_path: Path to enodebs.yaml. If None, uses default locations.

    Returns:
        Dict containing eNodeB configuration.
    """
    if config_path is None:
        # Try common locations
        search_paths = [
            Path("/app/config/enodebs.yaml"),  # Docker container
            Path("config/enodebs.yaml"),        # Local dev
            Path("../config/enodebs.yaml"),     # From opensurfcontrol/
        ]

        for path in search_paths:
            if path.exists():
                config_path = str(path)
                break

    if config_path is None or not Path(config_path).exists():
        logger.warning("eNodeB config not found, using empty configuration")
        return {"enodebs": []}

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    return config or {}


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
            # Open5GS uses unified 'slice' schema for both 4G and 5G
            if ip is not None or apn is not None:
                # Get current subscriber
                current = self.client.get_subscriber(imsi)
                if current is None:
                    return {
                        "success": False,
                        "error": f"Subscriber with IMSI {imsi} not found"
                    }

                # Update the slice/session configuration
                if "slice" in current and len(current["slice"]) > 0:
                    slice_config = current["slice"][0]
                    if "session" in slice_config and len(slice_config["session"]) > 0:
                        session = slice_config["session"][0]
                        if apn is not None:
                            session["name"] = apn
                            changes.append(f"apn → {apn}")
                        if ip is not None:
                            session["ue"] = {"ipv4": ip}
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
        Get system status including eNodeB connections and UE sessions from MME logs.

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

            # Get UE session counts from MME logs
            ue_count = mme_parser.get_ue_count()
            session_count = mme_parser.get_session_count()

            return {
                "timestamp": self._timestamp(),
                "system_name": "Open5G2GO",
                "subscribers": {
                    "provisioned": status.get("total_subscribers", 0),
                    "registered": ue_count,
                    "connected": session_count
                },
                "enodebs": {
                    "total": enb_count,
                    "list": enodebs
                },
                "health": {
                    "core_operational": health_ok,
                    "database_connected": status.get("connection") == "connected",
                    "has_active_connections": session_count > 0,
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
        Get active UE connections from MME log parsing.

        Returns:
            Active connections information with session details.
        """
        try:
            mme_parser = get_mme_parser()
            sessions = mme_parser.get_ue_sessions()

            # Enrich sessions with subscriber info from MongoDB
            enriched_connections = []
            for session in sessions:
                imsi = session.get("imsi", "")

                # Try to get device name from MongoDB
                device_name = None
                try:
                    subscriber = self.client.get_subscriber(imsi)
                    if subscriber:
                        device_name = subscriber.get("device_name")
                        # Also get the configured IP
                        configured_ip = self._get_subscriber_ip(subscriber)
                        if configured_ip:
                            session["ip_address"] = configured_ip
                except Exception:
                    pass

                enriched_connections.append({
                    "imsi": imsi,
                    "device_name": device_name or f"Device-{imsi[-4:]}",
                    "ip_address": session.get("ip_address"),
                    "apn": session.get("apn", "internet"),
                    "state": session.get("state", "attached"),
                    "attached_at": session.get("attached_at"),
                    "enb_ue_s1ap_id": session.get("enb_ue_s1ap_id"),
                    "mme_ue_s1ap_id": session.get("mme_ue_s1ap_id"),
                })

            return {
                "timestamp": self._timestamp(),
                "total_active": len(enriched_connections),
                "connections": enriched_connections,
            }
        except Exception as e:
            logger.error(f"Error getting active connections: {e}")
            return {
                "timestamp": self._timestamp(),
                "total_active": 0,
                "connections": [],
                "error": str(e)
            }

    async def get_enodeb_status(self) -> Dict[str, Any]:
        """
        Get combined eNodeB status from S1AP connections and SNMP.

        Combines:
        - S1AP connection status from MME log parsing
        - SNMP monitoring data from Baicells eNodeBs (if configured)
        - eNodeB configuration from enodebs.yaml

        Returns:
            EnodebStatusResponse with s1ap and snmp status.
        """
        try:
            # Get S1AP connection status from MME logs
            mme_parser = get_mme_parser()
            s1ap_connections = mme_parser.get_connected_enodebs()
            s1ap_available = mme_parser.is_available()

            # Get connected IPs for matching
            connected_ips = {conn.get("ip") for conn in s1ap_connections}

            # Load eNodeB configuration
            config = load_enodeb_config()
            configured_enodebs = config.get("enodebs", [])
            snmp_config = config.get("snmp", {})
            snmp_enabled = snmp_config.get("enabled", False)

            # Get SNMP status if enabled
            snmp_client = get_snmp_client(community=snmp_config.get("community", "public"))
            snmp_available = snmp_enabled and snmp_client.is_available()
            snmp_statuses = {}

            if snmp_available:
                # Query SNMP for each eNodeB with an IP address
                ip_addresses = [
                    e.get("ip_address")
                    for e in configured_enodebs
                    if e.get("enabled", True) and e.get("ip_address")
                ]
                if ip_addresses:
                    snmp_statuses = await snmp_client.get_status_multiple(ip_addresses)

            # Build S1AP eNodeB list from config, with connection status
            s1ap_enodebs = []
            for enb_config in configured_enodebs:
                if not enb_config.get("enabled", True):
                    continue

                serial = enb_config.get("serial_number", "")
                config_ip = enb_config.get("ip_address", "")

                # Check if connected via S1AP
                is_connected = config_ip in connected_ips or (
                    len(connected_ips) > 0 and len(configured_enodebs) == 1
                )

                # Find matching S1AP connection to get connection details
                enb_ip = config_ip
                connected_at = None
                port = None
                sctp_streams = None

                for conn in s1ap_connections:
                    conn_ip = conn.get("ip")
                    if conn_ip == config_ip or (len(configured_enodebs) == 1):
                        enb_ip = conn_ip or config_ip
                        connected_at = conn.get("connected_at")
                        port = conn.get("port", 36412)
                        sctp_streams = conn.get("sctp_streams")
                        break

                s1ap_enodebs.append({
                    "serial_number": serial,
                    "config_name": enb_config.get("name", f"eNodeB-{serial[-4:]}"),
                    "location": enb_config.get("location", ""),
                    "ip_address": enb_ip,
                    "port": port,
                    "sctp_streams": sctp_streams,
                    "connected": is_connected,
                    "connected_at": connected_at,
                })

            # Build SNMP eNodeB list
            snmp_enodebs = []
            for enb_config in configured_enodebs:
                if not enb_config.get("enabled", True):
                    continue

                config_ip = enb_config.get("ip_address", "")
                serial = enb_config.get("serial_number", "")

                if config_ip and config_ip in snmp_statuses:
                    snmp_status = snmp_statuses[config_ip]
                    snmp_enodebs.append({
                        "serial_number": snmp_status.serial_number or serial,
                        "config_name": enb_config.get("name", f"eNodeB-{serial[-4:]}"),
                        "location": enb_config.get("location", ""),
                        "reachable": snmp_status.reachable,
                        "error": snmp_status.error,
                        **snmp_status.to_dict(),
                    })

            # Count SNMP reachable
            snmp_reachable_count = sum(
                1 for s in snmp_statuses.values() if s.reachable
            )

            return {
                "timestamp": self._timestamp(),
                "s1ap": {
                    "available": s1ap_available,
                    "connected_count": len(s1ap_connections),
                    "enodebs": s1ap_enodebs,
                    "raw_connections": s1ap_connections,  # Include raw data for debugging
                },
                "snmp": {
                    "available": snmp_available,
                    "enabled": snmp_enabled,
                    "reachable_count": snmp_reachable_count,
                    "configured_count": len([e for e in configured_enodebs if e.get("ip_address")]),
                    "enodebs": snmp_enodebs,
                },
                # Network identity from MME config (what the MME accepts)
                "network": {
                    "plmn": PLMNID,
                    "mcc": MCC,
                    "mnc": MNC,
                    "tac": TAC,
                    "network_name": NETWORK_NAME_SHORT,
                }
            }
        except Exception as e:
            logger.error(f"Error getting eNodeB status: {e}")
            return {
                "timestamp": self._timestamp(),
                "error": str(e),
                "s1ap": {
                    "available": False,
                    "connected_count": 0,
                    "enodebs": [],
                },
                "snmp": {
                    "available": False,
                    "enabled": False,
                    "reachable_count": 0,
                    "configured_count": 0,
                    "enodebs": [],
                },
            }

    def _get_subscriber_ip(self, subscriber: Dict[str, Any]) -> Optional[str]:
        """Extract IP address from subscriber document (Open5GS slice/session format)."""
        try:
            # Open5GS uses slice/session for both 4G and 5G
            slice_data = subscriber.get("slice", [])
            if slice_data and len(slice_data) > 0:
                session = slice_data[0].get("session", [])
                if session and len(session) > 0:
                    ue = session[0].get("ue", {})
                    return ue.get("ipv4") or ue.get("addr")
        except (KeyError, IndexError):
            pass
        return None

    def _get_subscriber_apn(self, subscriber: Dict[str, Any]) -> str:
        """Extract APN from subscriber document (Open5GS slice/session format)."""
        try:
            # Open5GS uses slice/session with 'name' field for APN
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
