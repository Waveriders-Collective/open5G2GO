"""
Google SAS (Spectrum Access System) API Client

Provides integration with Google's CBRS Spectrum Access System Portal API
for monitoring eNodeB SAS registration and grant status.

Reference: https://developers.google.com/spectrum-access-system/
"""

import os
import yaml
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path

try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False
    AuthorizedSession = None

logger = logging.getLogger(__name__)


# =============================================================================
# Device and Grant State Enums (matching Google SAS API)
# =============================================================================

class DeviceState:
    """CBSD device registration states."""
    UNSPECIFIED = "DEVICE_STATE_UNSPECIFIED"
    RESERVED = "RESERVED"        # Created in portal, not yet registered
    REGISTERED = "REGISTERED"    # Active with SAS
    DEREGISTERED = "DEREGISTERED"  # Removed from SAS


class GrantState:
    """Grant authorization states."""
    UNSPECIFIED = "GRANT_STATE_UNSPECIFIED"
    GRANTED = "GRANT_STATE_GRANTED"      # Issued but device inactive
    AUTHORIZED = "GRANT_STATE_AUTHORIZED"  # Device actively transmitting
    SUSPENDED = "GRANT_STATE_SUSPENDED"    # Temporarily revoked
    TERMINATED = "GRANT_STATE_TERMINATED"  # Permanently revoked
    EXPIRED = "GRANT_STATE_EXPIRED"        # Time-limited authorization elapsed


# =============================================================================
# Configuration Loader
# =============================================================================

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
        return {
            "sas_customer_id": "",
            "grant_history_hours": 24,
            "sas_poll_interval_seconds": 120,
            "enodebs": []
        }

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    return config or {}


# =============================================================================
# Google SAS API Client
# =============================================================================

class GoogleSASClient:
    """
    Client for Google Spectrum Access System Portal API.

    Provides methods to query CBSD device status and grant information
    from the Google SAS Portal.

    Authentication requires a Google Cloud service account with SAS Portal
    API access. Set GOOGLE_APPLICATION_CREDENTIALS environment variable
    to point to the service account JSON key file.
    """

    BASE_URL = "https://sasportal.googleapis.com/v1alpha1"
    SCOPES = ["https://www.googleapis.com/auth/sasportal"]

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the SAS client.

        Args:
            config_path: Path to enodebs.yaml configuration file.
        """
        self.config = load_enodeb_config(config_path)
        self.customer_id = self.config.get("sas_customer_id", "")
        self.enodebs = self.config.get("enodebs", [])
        self.session: Optional[AuthorizedSession] = None
        self._initialized = False

        # Filter to enabled eNodeBs only
        self.enodebs = [e for e in self.enodebs if e.get("enabled", True)]

    def _initialize_session(self) -> bool:
        """
        Initialize the authenticated session with Google API.

        Returns:
            True if session initialized successfully, False otherwise.
        """
        if not GOOGLE_AUTH_AVAILABLE:
            logger.warning("google-auth library not installed. SAS features disabled.")
            return False

        if self._initialized and self.session:
            return True

        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if not creds_path:
            logger.warning("GOOGLE_APPLICATION_CREDENTIALS not set. SAS features disabled.")
            return False

        if not Path(creds_path).exists():
            logger.warning(f"Service account file not found: {creds_path}")
            return False

        try:
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=self.SCOPES
            )
            self.session = AuthorizedSession(credentials)
            self._initialized = True
            logger.info("Google SAS API session initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Google SAS session: {e}")
            return False

    def is_available(self) -> bool:
        """Check if SAS API is available and configured."""
        return (
            GOOGLE_AUTH_AVAILABLE and
            bool(self.customer_id) and
            bool(self.enodebs) and
            bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        )

    def list_devices(self) -> List[Dict[str, Any]]:
        """
        List all CBSD devices under the customer account.

        Returns:
            List of device dictionaries from SAS Portal.
        """
        if not self._initialize_session():
            return []

        try:
            url = f"{self.BASE_URL}/{self.customer_id}/devices"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json().get("devices", [])
        except Exception as e:
            logger.error(f"Failed to list SAS devices: {e}")
            return []

    def get_device_by_serial(self, serial_number: str) -> Optional[Dict[str, Any]]:
        """
        Find a device by its serial number.

        Args:
            serial_number: Manufacturer serial number.

        Returns:
            Device dictionary if found, None otherwise.
        """
        devices = self.list_devices()
        for device in devices:
            if device.get("serialNumber") == serial_number:
                return device
        return None

    def get_device_status(self, serial_number: str) -> Dict[str, Any]:
        """
        Get formatted status for a specific eNodeB.

        Args:
            serial_number: eNodeB serial number.

        Returns:
            Formatted device status dictionary.
        """
        device = self.get_device_by_serial(serial_number)

        if not device:
            return {
                "serial_number": serial_number,
                "sas_state": "NOT_FOUND",
                "error": f"Device {serial_number} not found in SAS Portal"
            }

        return self._format_device_status(device)

    def _format_device_status(self, device: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format raw SAS device data for display.

        Args:
            device: Raw device dictionary from SAS API.

        Returns:
            Formatted status dictionary.
        """
        grants = device.get("grants", [])
        active_grant = self._get_active_grant(grants)

        return {
            "serial_number": device.get("serialNumber", ""),
            "fcc_id": device.get("fccId", ""),
            "sas_state": device.get("state", DeviceState.UNSPECIFIED),
            "display_name": device.get("displayName", ""),
            "active_grant": active_grant,
            "grants": [self._format_grant(g) for g in grants],
            "grant_count": len(grants),
        }

    def _format_grant(self, grant: Dict[str, Any]) -> Dict[str, Any]:
        """Format a single grant for display."""
        freq_range = grant.get("frequencyRange", {})

        return {
            "grant_id": grant.get("grantId", ""),
            "state": grant.get("state", GrantState.UNSPECIFIED),
            "frequency_mhz": {
                "low": freq_range.get("lowFrequencyMhz"),
                "high": freq_range.get("highFrequencyMhz"),
            },
            "max_eirp_dbm": grant.get("maxEirp"),
            "channel_type": grant.get("channelType", ""),  # GAA or PAL
            "expire_time": grant.get("expireTime"),
            "suspended": grant.get("state") == GrantState.SUSPENDED,
            "move_list": grant.get("moveList", []),
        }

    def _get_active_grant(self, grants: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find the currently active (AUTHORIZED) grant.

        Args:
            grants: List of grant dictionaries.

        Returns:
            Active grant if found, None otherwise.
        """
        for grant in grants:
            if grant.get("state") == GrantState.AUTHORIZED:
                return self._format_grant(grant)
        return None

    def get_all_enodeb_status(self) -> List[Dict[str, Any]]:
        """
        Get SAS status for all configured eNodeBs.

        Returns:
            List of status dictionaries, one per configured eNodeB.
        """
        results = []

        for enb_config in self.enodebs:
            serial = enb_config.get("serial_number", "")
            status = self.get_device_status(serial)

            # Merge config data with SAS status
            status["config_name"] = enb_config.get("name", f"eNodeB-{serial[-4:]}")
            status["location"] = enb_config.get("location", "")

            results.append(status)

        return results

    def get_status_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all eNodeB SAS status.

        Returns:
            Summary dictionary with counts and overall status.
        """
        if not self.is_available():
            return {
                "available": False,
                "message": "SAS API not configured",
                "total": 0,
                "registered": 0,
                "authorized": 0,
                "enodebs": []
            }

        statuses = self.get_all_enodeb_status()

        registered = sum(1 for s in statuses if s.get("sas_state") == DeviceState.REGISTERED)
        authorized = sum(1 for s in statuses if s.get("active_grant") is not None)

        return {
            "available": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total": len(statuses),
            "registered": registered,
            "authorized": authorized,
            "enodebs": statuses
        }


# =============================================================================
# Module-level Singleton
# =============================================================================

_sas_client: Optional[GoogleSASClient] = None


def get_sas_client() -> GoogleSASClient:
    """Get or create the singleton SAS client instance."""
    global _sas_client
    if _sas_client is None:
        _sas_client = GoogleSASClient()
    return _sas_client
