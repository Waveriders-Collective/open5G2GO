# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Waveriders Collective Inc.

"""
Open5GS AMF Log Parser

Parses AMF logs to extract NGAP connection status for gNodeBs
and UE (device) session tracking in 5G SA mode.

This provides real-time visibility into:
- Which gNodeBs are connected to the Open5GS 5G core
- Which UEs are registered and attached
- Active PDU sessions (data connectivity)

Log location (Docker): /var/log/open5gs/amf.log
"""

import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class NGAPConnection:
    """Represents an NGAP connection from a gNodeB."""
    gnb_id: str
    ip_address: str
    port: int
    connected_at: Optional[datetime] = None
    is_connected: bool = True
    sctp_streams: Optional[int] = None


@dataclass
class UE5GSession:
    """Represents a UE (device) session in 5G SA mode."""
    imsi: str
    dnn: str = "internet"
    ran_ue_ngap_id: Optional[int] = None
    amf_ue_ngap_id: Optional[int] = None
    attached_at: Optional[datetime] = None
    state: str = "registering"  # registering, registered, deregistered

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "imsi": self.imsi,
            "dnn": self.dnn,
            "ran_ue_ngap_id": self.ran_ue_ngap_id,
            "amf_ue_ngap_id": self.amf_ue_ngap_id,
            "attached_at": self.attached_at.isoformat() if self.attached_at else None,
            "state": self.state,
        }


# =============================================================================
# Log Patterns - gNodeB NGAP
# =============================================================================

# Pattern: gNB-N2 accepted[10.0.1.14]:3223
NGAP_ACCEPTED_PATTERN = re.compile(
    r"gNB-N2 accepted\[(\d+\.\d+\.\d+\.\d+)\]:(\d+)"
)

# Pattern: [Added] Number of gNBs is now 1
GNB_COUNT_PATTERN = re.compile(
    r"\[Added\] Number of gNBs is now (\d+)"
)

# Pattern: gNB-N2[10.0.1.14] connection refused!!!
NGAP_REFUSED_PATTERN = re.compile(
    r"gNB-N2\[(\d+\.\d+\.\d+\.\d+)\] connection refused"
)

# Pattern: timestamp MM/DD HH:MM:SS.mmm
TIMESTAMP_PATTERN = re.compile(
    r"(\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d{3})"
)

# Pattern: gNB-N2[10.48.0.159] max_num_of_ostreams : 10
SCTP_STREAMS_PATTERN = re.compile(
    r"gNB-N2\[(\d+\.\d+\.\d+\.\d+)\] max_num_of_ostreams\s*:\s*(\d+)"
)


# =============================================================================
# Log Patterns - UE Session Tracking (5G)
# =============================================================================

# Pattern: [Added] Number of gNB-UEs is now 1
GNB_UE_COUNT_PATTERN = re.compile(
    r"\[(Added|Removed)\] Number of gNB-UEs is now (\d+)"
)

# Pattern: [Added] Number of AMF-Sessions is now 1
AMF_SESSION_COUNT_PATTERN = re.compile(
    r"\[(Added|Removed)\] Number of AMF-Sessions is now (\d+)"
)

# Pattern: [imsi-999700308170001] Registration complete (or Registration request)
# Also handles legacy format: [315010000000010] Registration accept
REGISTRATION_EVENT_PATTERN = re.compile(
    r"\[(?:imsi-)?(\d{15})\]\s+(Registration request|Registration accept|Registration complete)"
)

# Pattern: [imsi-999700308170001] Deregistration request
# Also handles legacy format: [315010000000010] De-registration request
DEREGISTRATION_EVENT_PATTERN = re.compile(
    r"\[(?:imsi-)?(\d{15})\]\s+De-?registration request"
)

# Pattern: IMSI[315010000000010] or imsi-999700308170001 in brackets
IMSI_PATTERN = re.compile(
    r"(?:IMSI\[(\d{15})\]|\[imsi-(\d{15})\])"
)

# Pattern: RAN_UE_NGAP_ID[167] AMF_UE_NGAP_ID[36]
UE_CONTEXT_PATTERN = re.compile(
    r"RAN_UE_NGAP_ID\[(\d+)\]\s+AMF_UE_NGAP_ID\[(\d+)\]"
)


# =============================================================================
# AMF Log Parser
# =============================================================================

class AMFLogParser:
    """
    Parser for Open5GS AMF logs to extract NGAP and UE session status.

    Parses log files to determine:
    - Which gNodeBs are currently connected (NGAP)
    - Which UEs are registered
    - Active PDU sessions
    """

    DEFAULT_LOG_PATH = "/var/log/open5gs/amf.log"

    def __init__(self, log_path: Optional[str] = None):
        """Initialize the AMF log parser."""
        self.log_path = Path(log_path or self.DEFAULT_LOG_PATH)
        self._connections: Dict[str, NGAPConnection] = {}
        self._ue_sessions: Dict[str, UE5GSession] = {}
        self._gnb_ue_count: int = 0
        self._amf_session_count: int = 0
        self._last_parse_time: Optional[datetime] = None

    def is_available(self) -> bool:
        """Check if AMF log file is accessible."""
        return self.log_path.exists() and self.log_path.is_file()

    def _extract_timestamp(self, line: str) -> Optional[datetime]:
        """Extract timestamp from log line."""
        match = TIMESTAMP_PATTERN.search(line)
        if match:
            try:
                ts_str = match.group(1)
                now = datetime.now(timezone.utc)
                parsed = datetime.strptime(ts_str, "%m/%d %H:%M:%S.%f")
                return parsed.replace(year=now.year, tzinfo=timezone.utc)
            except ValueError:
                pass
        return None

    def _read_log_lines(self, lines_to_read: int = 2000) -> List[str]:
        """Read the last N lines from the log file."""
        if not self.is_available():
            logger.warning(f"AMF log not found at {self.log_path}")
            return []

        try:
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
                return lines[-lines_to_read:] if len(lines) > lines_to_read else lines
        except Exception as e:
            logger.error(f"Error reading AMF logs: {e}")
            return []

    def parse_logs(self, lines_to_read: int = 2000) -> Dict[str, NGAPConnection]:
        """
        Parse recent AMF logs for NGAP connections.

        Returns:
            Dictionary of IP -> NGAPConnection for connected gNodeBs.
        """
        lines = self._read_log_lines(lines_to_read)
        if not lines:
            return {}

        try:
            connections: Dict[str, NGAPConnection] = {}
            refused_ips: set = set()

            for line in lines:
                accepted_match = NGAP_ACCEPTED_PATTERN.search(line)
                if accepted_match:
                    ip = accepted_match.group(1)
                    port = int(accepted_match.group(2))
                    timestamp = self._extract_timestamp(line)

                    connections[ip] = NGAPConnection(
                        gnb_id=f"gNB-{ip.replace('.', '-')}",
                        ip_address=ip,
                        port=port,
                        connected_at=timestamp,
                        is_connected=True
                    )
                    refused_ips.discard(ip)

                streams_match = SCTP_STREAMS_PATTERN.search(line)
                if streams_match:
                    ip = streams_match.group(1)
                    streams = int(streams_match.group(2))
                    if ip in connections:
                        connections[ip].sctp_streams = streams

                refused_match = NGAP_REFUSED_PATTERN.search(line)
                if refused_match:
                    ip = refused_match.group(1)
                    refused_ips.add(ip)
                    if ip in connections:
                        connections[ip].is_connected = False

            self._connections = {
                ip: conn for ip, conn in connections.items()
                if conn.is_connected and ip not in refused_ips
            }

            self._last_parse_time = datetime.now(timezone.utc)
            return self._connections

        except Exception as e:
            logger.error(f"Error parsing AMF logs: {e}")
            return {}

    def parse_ue_sessions(self, lines_to_read: int = 2000) -> Dict[str, UE5GSession]:
        """
        Parse AMF logs for UE session tracking in 5G SA mode.

        Returns:
            Dictionary of IMSI -> UE5GSession for registered UEs.
        """
        lines = self._read_log_lines(lines_to_read)
        if not lines:
            return {}

        try:
            sessions: Dict[str, UE5GSession] = {}
            pending_context: Dict[str, tuple] = {}
            last_gnb_ue_count = 0
            last_session_count = 0

            for line in lines:
                timestamp = self._extract_timestamp(line)

                context_match = UE_CONTEXT_PATTERN.search(line)
                imsi_match = IMSI_PATTERN.search(line)

                if context_match and imsi_match:
                    imsi = imsi_match.group(1) or imsi_match.group(2)
                    ran_id = int(context_match.group(1))
                    amf_id = int(context_match.group(2))
                    pending_context[imsi] = (ran_id, amf_id)

                reg_match = REGISTRATION_EVENT_PATTERN.search(line)
                if reg_match:
                    imsi = reg_match.group(1)
                    event_type = reg_match.group(2)

                    if imsi not in sessions:
                        sessions[imsi] = UE5GSession(imsi=imsi)

                    if event_type == "Registration request":
                        sessions[imsi].state = "registering"
                    elif event_type in ("Registration accept", "Registration complete"):
                        sessions[imsi].state = "registered"
                        sessions[imsi].attached_at = timestamp

                    if imsi in pending_context:
                        ran_id, amf_id = pending_context[imsi]
                        sessions[imsi].ran_ue_ngap_id = ran_id
                        sessions[imsi].amf_ue_ngap_id = amf_id

                dereg_match = DEREGISTRATION_EVENT_PATTERN.search(line)
                if dereg_match:
                    imsi = dereg_match.group(1)
                    if imsi in sessions:
                        sessions[imsi].state = "deregistered"

                gnb_ue_match = GNB_UE_COUNT_PATTERN.search(line)
                if gnb_ue_match:
                    last_gnb_ue_count = int(gnb_ue_match.group(2))

                session_match = AMF_SESSION_COUNT_PATTERN.search(line)
                if session_match:
                    last_session_count = int(session_match.group(2))

            self._gnb_ue_count = last_gnb_ue_count
            self._amf_session_count = last_session_count

            self._ue_sessions = {
                imsi: session for imsi, session in sessions.items()
                if session.state == "registered"
            }

            return self._ue_sessions

        except Exception as e:
            logger.error(f"Error parsing UE sessions: {e}")
            return {}

    def get_connected_gnodebs(self) -> List[Dict[str, Any]]:
        """Get list of currently connected gNodeBs."""
        connections = self.parse_logs()

        return [
            {
                "id": conn.gnb_id,
                "ip": conn.ip_address,
                "port": conn.port,
                "name": f"gNodeB @ {conn.ip_address}",
                "connected": conn.is_connected,
                "connected_at": conn.connected_at.isoformat() if conn.connected_at else None,
                "sctp_streams": conn.sctp_streams,
            }
            for conn in connections.values()
            if conn.is_connected
        ]

    def get_gnb_count(self) -> int:
        """Get count of connected gNodeBs."""
        connections = self.parse_logs()
        return len([c for c in connections.values() if c.is_connected])

    def get_ue_sessions(self) -> List[Dict[str, Any]]:
        """Get list of currently registered UE sessions."""
        sessions = self.parse_ue_sessions()
        return [session.to_dict() for session in sessions.values()]

    def get_ue_count(self) -> int:
        """Get count of registered UEs (from parsed session state, not transient NGAP contexts)."""
        sessions = self.parse_ue_sessions()
        return len(sessions)

    def get_session_count(self) -> int:
        """Get count of active sessions (registered UEs with PDU sessions)."""
        sessions = self.parse_ue_sessions()
        return len(sessions)


# =============================================================================
# Module-level Singleton
# =============================================================================

_amf_parser: Optional[AMFLogParser] = None


def get_amf_parser() -> AMFLogParser:
    """Get or create the singleton AMF parser instance."""
    global _amf_parser
    if _amf_parser is None:
        _amf_parser = AMFLogParser()
    return _amf_parser
