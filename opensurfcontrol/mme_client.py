"""
Open5GS MME Log Parser

Parses MME logs to extract S1AP connection status for eNodeBs.
This provides real-time visibility into which eNodeBs are connected
to the Open5GS EPC core.

Log location (Docker): /var/log/open5gs/mme.log
"""

import re
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass

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
    sctp_streams: Optional[int] = None  # max_num_of_ostreams from logs


@dataclass
class UESession:
    """Represents a UE (device) session."""
    imsi: str
    ip_address: Optional[str] = None
    connected_at: Optional[datetime] = None
    is_active: bool = True


# =============================================================================
# Log Patterns
# =============================================================================

# Pattern: eNB-S1 accepted[10.0.1.14]:3223 in s1_path module
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

# Pattern: S1AP_S1SetupRequest - matching timestamp
TIMESTAMP_PATTERN = re.compile(
    r"(\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d{3})"
)

# Pattern for eNodeB ID in S1Setup
# Format varies but commonly includes eNB_ID
ENB_ID_PATTERN = re.compile(
    r"eNB_ID\[(\w+)\]|S1SetupRequest.*?eNB.*?(\d+)"
)

# Pattern: eNB-S1[10.48.0.159] max_num_of_ostreams : 10
SCTP_STREAMS_PATTERN = re.compile(
    r"eNB-S1\[(\d+\.\d+\.\d+\.\d+)\] max_num_of_ostreams\s*:\s*(\d+)"
)


# =============================================================================
# MME Log Parser
# =============================================================================

class MMELogParser:
    """
    Parser for Open5GS MME logs to extract S1AP connection status.

    Parses log files to determine:
    - Which eNodeBs are currently connected (S1AP)
    - When connections were established
    - Connection failures/refusals
    """

    DEFAULT_LOG_PATH = "/var/log/open5gs/mme.log"

    def __init__(self, log_path: Optional[str] = None):
        """
        Initialize the MME log parser.

        Args:
            log_path: Path to MME log file. Defaults to standard location.
        """
        self.log_path = Path(log_path or self.DEFAULT_LOG_PATH)
        self._connections: Dict[str, S1APConnection] = {}
        self._last_parse_time: Optional[datetime] = None

    def is_available(self) -> bool:
        """Check if MME log file is accessible."""
        return self.log_path.exists() and self.log_path.is_file()

    def parse_logs(self, lines_to_read: int = 1000) -> Dict[str, S1APConnection]:
        """
        Parse recent MME logs for S1AP connections.

        Args:
            lines_to_read: Number of lines from end of log to parse.

        Returns:
            Dictionary of IP -> S1APConnection for connected eNodeBs.
        """
        if not self.is_available():
            logger.warning(f"MME log not found at {self.log_path}")
            return {}

        try:
            # Read last N lines of log file
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
                recent_lines = lines[-lines_to_read:] if len(lines) > lines_to_read else lines

            connections: Dict[str, S1APConnection] = {}
            refused_ips: set = set()

            for line in recent_lines:
                # Check for accepted connections
                accepted_match = S1AP_ACCEPTED_PATTERN.search(line)
                if accepted_match:
                    ip = accepted_match.group(1)
                    port = int(accepted_match.group(2))

                    # Extract timestamp if present
                    timestamp = self._extract_timestamp(line)

                    connections[ip] = S1APConnection(
                        enb_id=f"eNB-{ip.replace('.', '-')}",
                        ip_address=ip,
                        port=port,
                        connected_at=timestamp,
                        is_connected=True
                    )
                    # Remove from refused if previously refused
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
                    # Mark as disconnected if we had a connection
                    if ip in connections:
                        connections[ip].is_connected = False

            # Filter to only connected eNodeBs
            self._connections = {
                ip: conn for ip, conn in connections.items()
                if conn.is_connected and ip not in refused_ips
            }

            self._last_parse_time = datetime.now(timezone.utc)
            return self._connections

        except Exception as e:
            logger.error(f"Error parsing MME logs: {e}")
            return {}

    def _extract_timestamp(self, line: str) -> Optional[datetime]:
        """Extract timestamp from log line."""
        match = TIMESTAMP_PATTERN.search(line)
        if match:
            try:
                # Format: 12/28 14:30:45.123
                ts_str = match.group(1)
                now = datetime.now(timezone.utc)
                parsed = datetime.strptime(ts_str, "%m/%d %H:%M:%S.%f")
                # Add current year
                return parsed.replace(year=now.year, tzinfo=timezone.utc)
            except ValueError:
                pass
        return None

    def get_connected_enodebs(self) -> List[Dict[str, Any]]:
        """
        Get list of currently connected eNodeBs.

        Returns:
            List of connection dictionaries for UI display.
        """
        # Re-parse logs to get current state
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

    def get_connection_status_summary(self) -> Dict[str, Any]:
        """
        Get S1AP connection status summary.

        Returns:
            Summary dictionary with connection counts and list.
        """
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
