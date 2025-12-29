"""
Open5GS MME Log Parser

Parses MME logs to extract S1AP connection status for eNodeBs
and UE (device) session tracking.

This provides real-time visibility into:
- Which eNodeBs are connected to the Open5GS EPC core
- Which UEs are registered and attached
- Active PDN sessions (data connectivity)

Log location (Docker): /var/log/open5gs/mme.log
"""

import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class S1APConnection:
    """Represents an S1AP connection from an eNodeB."""
    enb_id: str
    ip_address: str
    port: int
    connected_at: Optional[datetime] = None
    is_connected: bool = True
    sctp_streams: Optional[int] = None


@dataclass
class UESession:
    """Represents a UE (device) session."""
    imsi: str
    apn: str = "internet"
    enb_ue_s1ap_id: Optional[int] = None
    mme_ue_s1ap_id: Optional[int] = None
    attached_at: Optional[datetime] = None
    state: str = "attaching"  # attaching, attached, detached

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "imsi": self.imsi,
            "apn": self.apn,
            "enb_ue_s1ap_id": self.enb_ue_s1ap_id,
            "mme_ue_s1ap_id": self.mme_ue_s1ap_id,
            "attached_at": self.attached_at.isoformat() if self.attached_at else None,
            "state": self.state,
        }


# =============================================================================
# Log Patterns - eNodeB S1AP
# =============================================================================

# Pattern: eNB-S1 accepted[10.0.1.14]:3223
S1AP_ACCEPTED_PATTERN = re.compile(
    r"eNB-S1 accepted\[(\d+\.\d+\.\d+\.\d+)\]:(\d+)"
)

# Pattern: [Added] Number of eNBs is now 1
ENB_COUNT_PATTERN = re.compile(
    r"\[Added\] Number of eNBs is now (\d+)"
)

# Pattern: eNB-S1[10.0.1.14] connection refused!!!
S1AP_REFUSED_PATTERN = re.compile(
    r"eNB-S1\[(\d+\.\d+\.\d+\.\d+)\] connection refused"
)

# Pattern: timestamp MM/DD HH:MM:SS.mmm
TIMESTAMP_PATTERN = re.compile(
    r"(\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d{3})"
)

# Pattern: eNB-S1[10.48.0.159] max_num_of_ostreams : 10
SCTP_STREAMS_PATTERN = re.compile(
    r"eNB-S1\[(\d+\.\d+\.\d+\.\d+)\] max_num_of_ostreams\s*:\s*(\d+)"
)


# =============================================================================
# Log Patterns - UE Session Tracking
# =============================================================================

# Pattern: [Added] Number of eNB-UEs is now 1
# Tracks UEs attached to radio
ENB_UE_COUNT_PATTERN = re.compile(
    r"\[(Added|Removed)\] Number of eNB-UEs is now (\d+)"
)

# Pattern: [Added] Number of MME-Sessions is now 1
# Tracks active PDN sessions
MME_SESSION_COUNT_PATTERN = re.compile(
    r"\[(Added|Removed)\] Number of MME-Sessions is now (\d+)"
)

# Pattern: [315010000000010] Attach request or Attach complete
ATTACH_EVENT_PATTERN = re.compile(
    r"\[(\d{15})\]\s+(Attach request|Attach complete)"
)

# Pattern: [315010000000010] Detach request
DETACH_EVENT_PATTERN = re.compile(
    r"\[(\d{15})\]\s+Detach request"
)

# Pattern: IMSI[315010000000010]
IMSI_PATTERN = re.compile(
    r"IMSI\[(\d{15})\]"
)

# Pattern: ENB_UE_S1AP_ID[167] MME_UE_S1AP_ID[36]
UE_CONTEXT_PATTERN = re.compile(
    r"ENB_UE_S1AP_ID\[(\d+)\]\s+MME_UE_S1AP_ID\[(\d+)\]"
)

# Pattern: Removed Session: UE IMSI:[315010000000010] APN:[internet]
SESSION_REMOVED_PATTERN = re.compile(
    r"Removed Session: UE IMSI:\[(\d{15})\] APN:\[(\w+)\]"
)


# =============================================================================
# MME Log Parser
# =============================================================================

class MMELogParser:
    """
    Parser for Open5GS MME logs to extract S1AP and UE session status.

    Parses log files to determine:
    - Which eNodeBs are currently connected (S1AP)
    - Which UEs are attached (registered + connected)
    - Active PDN sessions
    """

    DEFAULT_LOG_PATH = "/var/log/open5gs/mme.log"

    def __init__(self, log_path: Optional[str] = None):
        """Initialize the MME log parser."""
        self.log_path = Path(log_path or self.DEFAULT_LOG_PATH)
        self._connections: Dict[str, S1APConnection] = {}
        self._ue_sessions: Dict[str, UESession] = {}
        self._enb_ue_count: int = 0
        self._mme_session_count: int = 0
        self._last_parse_time: Optional[datetime] = None

    def is_available(self) -> bool:
        """Check if MME log file is accessible."""
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
            logger.warning(f"MME log not found at {self.log_path}")
            return []

        try:
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
                return lines[-lines_to_read:] if len(lines) > lines_to_read else lines
        except Exception as e:
            logger.error(f"Error reading MME logs: {e}")
            return []

    def parse_logs(self, lines_to_read: int = 2000) -> Dict[str, S1APConnection]:
        """
        Parse recent MME logs for S1AP connections.

        Returns:
            Dictionary of IP -> S1APConnection for connected eNodeBs.
        """
        lines = self._read_log_lines(lines_to_read)
        if not lines:
            return {}

        try:
            connections: Dict[str, S1APConnection] = {}
            refused_ips: set = set()

            for line in lines:
                # Check for accepted connections
                accepted_match = S1AP_ACCEPTED_PATTERN.search(line)
                if accepted_match:
                    ip = accepted_match.group(1)
                    port = int(accepted_match.group(2))
                    timestamp = self._extract_timestamp(line)

                    connections[ip] = S1APConnection(
                        enb_id=f"eNB-{ip.replace('.', '-')}",
                        ip_address=ip,
                        port=port,
                        connected_at=timestamp,
                        is_connected=True
                    )
                    refused_ips.discard(ip)

                # Check for SCTP streams info
                streams_match = SCTP_STREAMS_PATTERN.search(line)
                if streams_match:
                    ip = streams_match.group(1)
                    streams = int(streams_match.group(2))
                    if ip in connections:
                        connections[ip].sctp_streams = streams

                # Check for refused connections
                refused_match = S1AP_REFUSED_PATTERN.search(line)
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
            logger.error(f"Error parsing MME logs: {e}")
            return {}

    def parse_ue_sessions(self, lines_to_read: int = 2000) -> Dict[str, UESession]:
        """
        Parse MME logs for UE session tracking.

        Tracks attach/detach events to determine which UEs are currently connected.

        Returns:
            Dictionary of IMSI -> UESession for attached UEs.
        """
        lines = self._read_log_lines(lines_to_read)
        if not lines:
            return {}

        try:
            sessions: Dict[str, UESession] = {}
            pending_context: Dict[str, tuple] = {}  # IMSI -> (enb_id, mme_id)
            last_enb_ue_count = 0
            last_session_count = 0

            for line in lines:
                timestamp = self._extract_timestamp(line)

                # Track UE context (ENB_UE_S1AP_ID, MME_UE_S1AP_ID)
                context_match = UE_CONTEXT_PATTERN.search(line)
                imsi_match = IMSI_PATTERN.search(line)

                if context_match and imsi_match:
                    imsi = imsi_match.group(1)
                    enb_id = int(context_match.group(1))
                    mme_id = int(context_match.group(2))
                    pending_context[imsi] = (enb_id, mme_id)

                # Check for attach events
                attach_match = ATTACH_EVENT_PATTERN.search(line)
                if attach_match:
                    imsi = attach_match.group(1)
                    event_type = attach_match.group(2)

                    if imsi not in sessions:
                        sessions[imsi] = UESession(imsi=imsi)

                    if event_type == "Attach request":
                        sessions[imsi].state = "attaching"
                    elif event_type == "Attach complete":
                        sessions[imsi].state = "attached"
                        sessions[imsi].attached_at = timestamp

                    # Apply context if available
                    if imsi in pending_context:
                        enb_id, mme_id = pending_context[imsi]
                        sessions[imsi].enb_ue_s1ap_id = enb_id
                        sessions[imsi].mme_ue_s1ap_id = mme_id

                # Check for detach events
                detach_match = DETACH_EVENT_PATTERN.search(line)
                if detach_match:
                    imsi = detach_match.group(1)
                    if imsi in sessions:
                        sessions[imsi].state = "detached"

                # Check for session removal (captures APN)
                session_removed_match = SESSION_REMOVED_PATTERN.search(line)
                if session_removed_match:
                    imsi = session_removed_match.group(1)
                    apn = session_removed_match.group(2)
                    if imsi in sessions:
                        sessions[imsi].apn = apn
                        sessions[imsi].state = "detached"

                # Track counts from log messages
                enb_ue_match = ENB_UE_COUNT_PATTERN.search(line)
                if enb_ue_match:
                    last_enb_ue_count = int(enb_ue_match.group(2))

                session_match = MME_SESSION_COUNT_PATTERN.search(line)
                if session_match:
                    last_session_count = int(session_match.group(2))

            # Store the final counts
            self._enb_ue_count = last_enb_ue_count
            self._mme_session_count = last_session_count

            # Filter to only attached sessions
            self._ue_sessions = {
                imsi: session for imsi, session in sessions.items()
                if session.state == "attached"
            }

            return self._ue_sessions

        except Exception as e:
            logger.error(f"Error parsing UE sessions: {e}")
            return {}

    def get_connected_enodebs(self) -> List[Dict[str, Any]]:
        """Get list of currently connected eNodeBs."""
        connections = self.parse_logs()

        return [
            {
                "id": conn.enb_id,
                "ip": conn.ip_address,
                "port": conn.port,
                "name": f"eNodeB @ {conn.ip_address}",
                "connected": conn.is_connected,
                "connected_at": conn.connected_at.isoformat() if conn.connected_at else None,
                "sctp_streams": conn.sctp_streams,
            }
            for conn in connections.values()
            if conn.is_connected
        ]

    def get_enb_count(self) -> int:
        """Get count of connected eNodeBs."""
        connections = self.parse_logs()
        return len([c for c in connections.values() if c.is_connected])

    def get_ue_sessions(self) -> List[Dict[str, Any]]:
        """Get list of currently attached UE sessions."""
        sessions = self.parse_ue_sessions()
        return [session.to_dict() for session in sessions.values()]

    def get_ue_count(self) -> int:
        """Get count of attached UEs."""
        self.parse_ue_sessions()
        return self._enb_ue_count

    def get_session_count(self) -> int:
        """Get count of active PDN sessions."""
        self.parse_ue_sessions()
        return self._mme_session_count

    def get_ue_status_summary(self) -> Dict[str, Any]:
        """
        Get UE session status summary.

        Returns:
            Summary with counts and session list.
        """
        sessions = self.get_ue_sessions()

        return {
            "available": self.is_available(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "enb_ue_count": self._enb_ue_count,
            "session_count": self._mme_session_count,
            "attached_ues": len(sessions),
            "sessions": sessions,
        }

    def get_connection_status_summary(self) -> Dict[str, Any]:
        """Get S1AP connection status summary."""
        enodebs = self.get_connected_enodebs()

        return {
            "available": self.is_available(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_connected": len(enodebs),
            "enodebs": enodebs,
            "log_path": str(self.log_path),
        }


# =============================================================================
# Module-level Singleton
# =============================================================================

_mme_parser: Optional[MMELogParser] = None


def get_mme_parser() -> MMELogParser:
    """Get or create the singleton MME parser instance."""
    global _mme_parser
    if _mme_parser is None:
        _mme_parser = MMELogParser()
    return _mme_parser
