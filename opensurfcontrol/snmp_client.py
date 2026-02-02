# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Waveriders Collective Inc.

"""
Baicells eNodeB SNMP Client

Queries Baicells LTE eNodeBs via SNMP to retrieve operational status,
performance metrics, and configuration data.

Requires:
- SNMP v2c enabled on eNodeB
- Docker host IP added to eNodeB SNMP allowed hosts
- Community string (default: "public")

Baicells MIB: enterprises.53058 (.1.3.6.1.4.1.53058)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# =============================================================================
# Baicells SNMP OID Definitions
# =============================================================================

BAICELLS_ENTERPRISE_OID = "1.3.6.1.4.1.53058"

# Basic Settings (.100)
OIDS = {
    # Device Identity
    "product_type": f"{BAICELLS_ENTERPRISE_OID}.100.1.0",
    "hardware_version": f"{BAICELLS_ENTERPRISE_OID}.100.2.0",
    "software_version": f"{BAICELLS_ENTERPRISE_OID}.100.3.0",
    "serial_number": f"{BAICELLS_ENTERPRISE_OID}.100.4.0",

    # Cell Status
    "cell_status": f"{BAICELLS_ENTERPRISE_OID}.100.5.0",
    "band_class": f"{BAICELLS_ENTERPRISE_OID}.100.6.0",
    "carrier_bw_mhz": f"{BAICELLS_ENTERPRISE_OID}.100.7.0",  # 25=5MHz, 50=10MHz, 75=15MHz, 100=20MHz
    "earfcn": f"{BAICELLS_ENTERPRISE_OID}.100.8.1.0",
    "pci": f"{BAICELLS_ENTERPRISE_OID}.100.12.1.0",
    "cell_id": f"{BAICELLS_ENTERPRISE_OID}.100.13.1.0",
    "tac": f"{BAICELLS_ENTERPRISE_OID}.100.15.0",
    "s1_link_status": f"{BAICELLS_ENTERPRISE_OID}.100.21.0",  # 0=Down, 1=Up

    # UE Connections
    "ue_connections": f"{BAICELLS_ENTERPRISE_OID}.100.11.1.0",
    "ue_connections_cell2": f"{BAICELLS_ENTERPRISE_OID}.100.11.2.0",

    # Network
    "mac_address": f"{BAICELLS_ENTERPRISE_OID}.120.1.0",
    "link_speed": f"{BAICELLS_ENTERPRISE_OID}.120.3.0",

    # OS
    "cpu0_utilization": f"{BAICELLS_ENTERPRISE_OID}.150.1.0",
    "cpu1_utilization": f"{BAICELLS_ENTERPRISE_OID}.150.2.0",

    # Alarms
    "alarm_count": f"{BAICELLS_ENTERPRISE_OID}.160.1.0",
    "sctp_alarm": f"{BAICELLS_ENTERPRISE_OID}.160.2.11112.0",  # 0=Clear, 1=Problem
    "cell_unavailable": f"{BAICELLS_ENTERPRISE_OID}.160.2.11184.0",  # 0=Clear, 1=Problem

    # Performance
    "erab_success_rate": f"{BAICELLS_ENTERPRISE_OID}.190.3.0",  # %
    "ho_s1_success_rate": f"{BAICELLS_ENTERPRISE_OID}.190.4.0",  # %
    "ho_success_rate": f"{BAICELLS_ENTERPRISE_OID}.190.5.0",  # %
    "rrc_success_rate": f"{BAICELLS_ENTERPRISE_OID}.190.6.0",  # %
    "ul_throughput": f"{BAICELLS_ENTERPRISE_OID}.190.7.1.0",  # kbps
    "dl_throughput": f"{BAICELLS_ENTERPRISE_OID}.190.8.1.0",  # kbps
    "ul_prb_utilization": f"{BAICELLS_ENTERPRISE_OID}.190.9.1.0",  # %
    "dl_prb_utilization": f"{BAICELLS_ENTERPRISE_OID}.190.10.1.0",  # %

    # LTE Settings
    "tx_power": f"{BAICELLS_ENTERPRISE_OID}.140.100.6.0",
    "enodeb_name": f"{BAICELLS_ENTERPRISE_OID}.140.100.7.0",
    "min_tx_power": f"{BAICELLS_ENTERPRISE_OID}.140.100.9.0",
    "max_tx_power": f"{BAICELLS_ENTERPRISE_OID}.140.100.10.0",

    # Control
    "rf_status": f"{BAICELLS_ENTERPRISE_OID}.270.1.1.0",  # 0=Off, 1=On
}

# Bandwidth mapping
BANDWIDTH_MAP = {
    25: "5 MHz",
    50: "10 MHz",
    75: "15 MHz",
    100: "20 MHz",
}


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class EnodebSNMPStatus:
    """eNodeB status retrieved via SNMP."""

    ip_address: str
    reachable: bool = False
    timestamp: Optional[str] = None
    error: Optional[str] = None

    # Device Identity
    serial_number: Optional[str] = None
    product_type: Optional[str] = None
    hardware_version: Optional[str] = None
    software_version: Optional[str] = None
    enodeb_name: Optional[str] = None
    mac_address: Optional[str] = None

    # Cell Configuration
    cell_status: Optional[str] = None
    band_class: Optional[int] = None
    bandwidth: Optional[str] = None
    earfcn: Optional[int] = None
    pci: Optional[int] = None
    cell_id: Optional[int] = None
    tac: Optional[int] = None

    # Connection Status
    s1_link_up: bool = False
    rf_enabled: bool = False
    ue_count: int = 0

    # Performance
    ul_throughput_kbps: Optional[int] = None
    dl_throughput_kbps: Optional[int] = None
    ul_prb_pct: Optional[int] = None
    dl_prb_pct: Optional[int] = None
    cpu_utilization: Optional[int] = None

    # KPIs
    erab_success_pct: Optional[int] = None
    rrc_success_pct: Optional[int] = None

    # Alarms
    alarm_count: int = 0
    sctp_alarm: bool = False
    cell_unavailable_alarm: bool = False

    # TX Power
    tx_power_dbm: Optional[int] = None
    min_tx_power_dbm: Optional[int] = None
    max_tx_power_dbm: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "ip_address": self.ip_address,
            "reachable": self.reachable,
            "timestamp": self.timestamp,
            "error": self.error,
            "identity": {
                "serial_number": self.serial_number,
                "product_type": self.product_type,
                "hardware_version": self.hardware_version,
                "software_version": self.software_version,
                "enodeb_name": self.enodeb_name,
                "mac_address": self.mac_address,
            },
            "cell": {
                "status": self.cell_status,
                "band_class": self.band_class,
                "bandwidth": self.bandwidth,
                "earfcn": self.earfcn,
                "pci": self.pci,
                "cell_id": self.cell_id,
                "tac": self.tac,
            },
            "connection": {
                "s1_link_up": self.s1_link_up,
                "rf_enabled": self.rf_enabled,
                "ue_count": self.ue_count,
            },
            "performance": {
                "ul_throughput_kbps": self.ul_throughput_kbps,
                "dl_throughput_kbps": self.dl_throughput_kbps,
                "ul_prb_pct": self.ul_prb_pct,
                "dl_prb_pct": self.dl_prb_pct,
                "cpu_utilization": self.cpu_utilization,
            },
            "kpis": {
                "erab_success_pct": self.erab_success_pct,
                "rrc_success_pct": self.rrc_success_pct,
            },
            "alarms": {
                "count": self.alarm_count,
                "sctp_failure": self.sctp_alarm,
                "cell_unavailable": self.cell_unavailable_alarm,
            },
            "tx_power": {
                "current_dbm": self.tx_power_dbm,
                "min_dbm": self.min_tx_power_dbm,
                "max_dbm": self.max_tx_power_dbm,
            },
        }


# =============================================================================
# SNMP Client
# =============================================================================

class BaicellsSNMPClient:
    """
    SNMP client for querying Baicells eNodeBs.

    Uses pysnmp for async SNMP v2c queries.
    """

    def __init__(
        self,
        community: str = "public",
        timeout: float = 5.0,
        retries: int = 2,
    ):
        """
        Initialize the SNMP client.

        Args:
            community: SNMP community string (default: public)
            timeout: Query timeout in seconds
            retries: Number of retry attempts
        """
        self.community = community
        self.timeout = timeout
        self.retries = retries
        self._available = self._check_pysnmp()

    def _check_pysnmp(self) -> bool:
        """Check if pysnmp is available."""
        try:
            from pysnmp.hlapi.asyncio import (
                getCmd, CommunityData, UdpTransportTarget,
                ContextData, ObjectType, ObjectIdentity
            )
            return True
        except ImportError:
            logger.warning("pysnmp not installed - SNMP monitoring disabled")
            return False

    def is_available(self) -> bool:
        """Check if SNMP client is available."""
        return self._available

    async def get_status(self, ip_address: str) -> EnodebSNMPStatus:
        """
        Query eNodeB status via SNMP.

        Args:
            ip_address: eNodeB IP address

        Returns:
            EnodebSNMPStatus with queried values
        """
        status = EnodebSNMPStatus(
            ip_address=ip_address,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        if not self._available:
            status.error = "pysnmp not installed"
            return status

        try:
            # Import pysnmp components
            from pysnmp.hlapi.asyncio import (
                getCmd, CommunityData, UdpTransportTarget,
                ContextData, ObjectType, ObjectIdentity, SnmpEngine
            )

            # Build list of OIDs to query
            oid_list = [
                ObjectType(ObjectIdentity(oid))
                for oid in OIDS.values()
            ]

            # Execute SNMP GET (pysnmp 6.x requires SnmpEngine as first arg)
            errorIndication, errorStatus, errorIndex, varBinds = await getCmd(
                SnmpEngine(),
                CommunityData(self.community),
                UdpTransportTarget(
                    (ip_address, 161),
                    timeout=self.timeout,
                    retries=self.retries,
                ),
                ContextData(),
                *oid_list
            )

            if errorIndication:
                status.error = str(errorIndication)
                logger.warning(f"SNMP error for {ip_address}: {errorIndication}")
                return status

            if errorStatus:
                status.error = f"{errorStatus.prettyPrint()} at {errorIndex}"
                logger.warning(f"SNMP status error for {ip_address}: {status.error}")
                return status

            # Parse results
            status.reachable = True
            results = {str(oid): value for oid, value in varBinds}

            # Map results to status fields
            self._parse_results(status, results)

            return status

        except asyncio.TimeoutError:
            status.error = "SNMP timeout - check eNodeB access control settings"
            logger.warning(f"SNMP timeout for {ip_address}")
            return status
        except Exception as e:
            status.error = str(e)
            logger.error(f"SNMP error for {ip_address}: {e}")
            return status

    def _parse_results(self, status: EnodebSNMPStatus, results: Dict[str, Any]) -> None:
        """Parse SNMP results into status object."""

        def get_value(key: str) -> Optional[Any]:
            """Get value from results by OID key."""
            oid = OIDS.get(key)
            if oid and oid in results:
                val = results[oid]
                # Handle NoSuchInstance/NoSuchObject
                if hasattr(val, 'prettyPrint'):
                    pretty = val.prettyPrint()
                    if 'NoSuch' in pretty:
                        return None
                    return pretty
                return val
            return None

        def get_int(key: str) -> Optional[int]:
            """Get integer value."""
            val = get_value(key)
            if val is not None:
                try:
                    return int(val)
                except (ValueError, TypeError):
                    pass
            return None

        def get_str(key: str) -> Optional[str]:
            """Get string value."""
            val = get_value(key)
            return str(val) if val is not None else None

        # Device Identity
        status.serial_number = get_str("serial_number")
        status.product_type = get_str("product_type")
        status.hardware_version = get_str("hardware_version")
        status.software_version = get_str("software_version")
        status.enodeb_name = get_str("enodeb_name")
        status.mac_address = get_str("mac_address")

        # Cell Configuration
        status.cell_status = get_str("cell_status")
        status.band_class = get_int("band_class")
        bw_raw = get_int("carrier_bw_mhz")
        if bw_raw:
            status.bandwidth = BANDWIDTH_MAP.get(bw_raw, f"{bw_raw} RBs")
        status.earfcn = get_int("earfcn")
        status.pci = get_int("pci")
        status.cell_id = get_int("cell_id")
        status.tac = get_int("tac")

        # Connection Status
        s1_val = get_int("s1_link_status")
        status.s1_link_up = s1_val == 1 if s1_val is not None else False
        rf_val = get_int("rf_status")
        status.rf_enabled = rf_val == 1 if rf_val is not None else False
        status.ue_count = get_int("ue_connections") or 0

        # Performance
        status.ul_throughput_kbps = get_int("ul_throughput")
        status.dl_throughput_kbps = get_int("dl_throughput")
        status.ul_prb_pct = get_int("ul_prb_utilization")
        status.dl_prb_pct = get_int("dl_prb_utilization")

        # CPU - average of both cores if available
        cpu0 = get_int("cpu0_utilization")
        cpu1 = get_int("cpu1_utilization")
        if cpu0 is not None and cpu1 is not None:
            status.cpu_utilization = (cpu0 + cpu1) // 2
        elif cpu0 is not None:
            status.cpu_utilization = cpu0

        # KPIs
        status.erab_success_pct = get_int("erab_success_rate")
        status.rrc_success_pct = get_int("rrc_success_rate")

        # Alarms
        status.alarm_count = get_int("alarm_count") or 0
        sctp = get_int("sctp_alarm")
        status.sctp_alarm = sctp == 1 if sctp is not None else False
        cell_unavail = get_int("cell_unavailable")
        status.cell_unavailable_alarm = cell_unavail == 1 if cell_unavail is not None else False

        # TX Power
        status.tx_power_dbm = get_int("tx_power")
        status.min_tx_power_dbm = get_int("min_tx_power")
        status.max_tx_power_dbm = get_int("max_tx_power")

    async def get_status_multiple(
        self,
        ip_addresses: List[str],
    ) -> Dict[str, EnodebSNMPStatus]:
        """
        Query multiple eNodeBs in parallel.

        Args:
            ip_addresses: List of eNodeB IP addresses

        Returns:
            Dictionary mapping IP -> EnodebSNMPStatus
        """
        tasks = [self.get_status(ip) for ip in ip_addresses]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            ip: result if isinstance(result, EnodebSNMPStatus)
            else EnodebSNMPStatus(ip_address=ip, error=str(result))
            for ip, result in zip(ip_addresses, results)
        }


# =============================================================================
# Module-level Singleton
# =============================================================================

_snmp_client: Optional[BaicellsSNMPClient] = None


def get_snmp_client(community: str = "public") -> BaicellsSNMPClient:
    """Get or create the singleton SNMP client instance."""
    global _snmp_client
    if _snmp_client is None:
        _snmp_client = BaicellsSNMPClient(community=community)
    return _snmp_client
