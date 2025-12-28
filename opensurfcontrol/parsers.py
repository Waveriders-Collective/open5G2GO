"""
Parsers for Attocore CLI command outputs.

Functions to parse tab-separated data, key-value pairs, JSON, and other
CLI output formats from Attocore systems.
"""

import json
import re
from typing import Dict, List, Optional, Any


def parse_tab_separated(output: str, skip_header: bool = True) -> List[List[str]]:
    """
    Parse tab-separated CLI output into list of rows.

    Args:
        output: Raw CLI output with tab-separated columns
        skip_header: Whether to skip first line (column headers)

    Returns:
        List of rows, where each row is a list of column values

    Example:
        Input: "IMSI\\tName\\tService\\nxxx\\tWR-VIDEO-01\\tvideo"
        Output: [["xxx", "WR-VIDEO-01", "video"]]
    """
    lines = [line for line in output.strip().split('\n') if line.strip()]

    if not lines:
        return []

    # Skip header if requested
    data_lines = lines[1:] if skip_header and len(lines) > 1 else lines

    # Split each line by tabs and clean whitespace
    rows = []
    for line in data_lines:
        columns = [col.strip() for col in line.split('\t')]
        rows.append(columns)

    return rows


def parse_subscriber_list(output: str) -> List[Dict[str, str]]:
    """
    Parse output of 'atto-5gc-cli listues' command.

    Expected format (tab-separated):
    IMSI    Name    Service    StaticIP
    imsi-xxx    WR-VIDEO-01    video    10.48.100.11

    Args:
        output: Raw output from listues command

    Returns:
        List of subscriber dictionaries with keys: imsi, name, service, ip
    """
    rows = parse_tab_separated(output, skip_header=True)

    subscribers = []
    for row in rows:
        if len(row) >= 4:
            subscribers.append({
                "imsi": row[0].replace("imsi-", ""),  # Remove prefix
                "name": row[1],
                "service": row[2],
                "ip": row[3]
            })

    return subscribers


def parse_key_value_pairs(output: str, separator: str = "=") -> Dict[str, str]:
    """
    Parse key=value pairs from CLI output.

    Args:
        output: Raw output with format "key1=value1,key2=value2"
        separator: Character separating keys and values

    Returns:
        Dictionary of key-value pairs

    Example:
        Input: "Registered=5,Connected=2"
        Output: {"Registered": "5", "Connected": "2"}
    """
    result = {}

    # Split by comma and parse each pair
    pairs = output.strip().split(',')
    for pair in pairs:
        if separator in pair:
            key, value = pair.split(separator, 1)
            result[key.strip()] = value.strip()

    return result


def parse_ue_state_counts(output: str) -> Dict[str, int]:
    """
    Parse output of 'atto-5gc-cli countuestate' command.

    Expected format: "Registered=X,Connected=Y"

    Args:
        output: Raw output from countuestate command

    Returns:
        Dictionary with keys 'registered' and 'connected' (int values)
    """
    pairs = parse_key_value_pairs(output)

    return {
        "registered": int(pairs.get("Registered", "0")),
        "connected": int(pairs.get("Connected", "0"))
    }


def parse_gnb_state(output: str) -> List[Dict[str, str]]:
    """
    Parse output of 'atto-5gc-cli gnbstate' command.

    Expected format (space-separated):
    GNB: F2240-0121 10.48.98.50 Waveriders-gNodeB-01

    Args:
        output: Raw output from gnbstate command

    Returns:
        List of gNodeB dictionaries with keys: id, ip, name
    """
    gnbs = []

    for line in output.strip().split('\n'):
        line = line.strip()
        if line.startswith('GNB:'):
            # Remove "GNB:" prefix and split by whitespace
            parts = line.replace('GNB:', '').strip().split()

            if len(parts) >= 3:
                gnbs.append({
                    "id": parts[0],
                    "ip": parts[1],
                    "name": parts[2] if len(parts) > 2 else "Unknown"
                })

    return gnbs


def parse_ue_state_list(output: str) -> List[Dict[str, str]]:
    """
    Parse output of 'atto-5gc-cli listuestate' command.

    Expected format (tab-separated):
    IMSI    TMSI    CM_STATE    RM_STATE

    Args:
        output: Raw output from listuestate command

    Returns:
        List of UE state dictionaries
    """
    rows = parse_tab_separated(output, skip_header=True)

    ue_states = []
    for row in rows:
        if len(row) >= 4:
            ue_states.append({
                "imsi": row[0].strip(),
                "tmsi": row[1].strip(),
                "cm_state": row[2].strip(),
                "rm_state": row[3].strip()
            })

    return ue_states


def parse_pdu_session_info(output: str) -> Optional[Dict[str, str]]:
    """
    Parse output of 'atto-5gc-cli getpdusessioninformation' command.

    Expected format (space-separated):
    imsi-xxx context-id session-id ip-address dnn

    Args:
        output: Raw output from getpdusessioninformation command

    Returns:
        Dictionary with PDU session info or None if no data
    """
    lines = [line for line in output.strip().split('\n') if line.strip()]

    for line in lines:
        if line.startswith('imsi-'):
            parts = line.split()
            if len(parts) >= 5:
                return {
                    "imsi": parts[0].replace("imsi-", ""),
                    "context_id": parts[1],
                    "session_id": parts[2],
                    "ip": parts[3],
                    "dnn": parts[4]
                }

    return None


def parse_json_output(output: str) -> Any:
    """
    Parse JSON output from CLI commands.

    Args:
        output: Raw JSON string from CLI

    Returns:
        Parsed JSON object (dict, list, etc.)

    Raises:
        ValueError: If output is not valid JSON
    """
    try:
        return json.loads(output)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON output: {str(e)}") from e


def extract_dnn_names_from_shared_data(shared_data_json: Dict[str, Any]) -> List[str]:
    """
    Extract DNN names from shared data JSON.

    Args:
        shared_data_json: Parsed JSON from getshareddata command

    Returns:
        List of DNN names found in sharedDnnConfigurations
    """
    dnn_names = []

    # Navigate to sharedDnnConfigurations
    dnn_configs = shared_data_json.get("sharedDnnConfigurations", {})

    # Extract all DNN names (top-level keys)
    for dnn_name in dnn_configs.keys():
        dnn_names.append(dnn_name)

    return dnn_names


def extract_dnn_config(shared_data_json: Dict[str, Any], dnn_name: str) -> Optional[Dict[str, Any]]:
    """
    Extract configuration for a specific DNN from shared data JSON.

    Args:
        shared_data_json: Parsed JSON from getshareddata command
        dnn_name: Name of DNN to extract config for

    Returns:
        DNN configuration dictionary or None if not found
    """
    dnn_configs = shared_data_json.get("sharedDnnConfigurations", {})
    dnn_config = dnn_configs.get(dnn_name)

    if not dnn_config:
        return None

    # Extract key configuration values
    session_ambr = dnn_config.get("sessionAmbr", {})

    return {
        "name": dnn_name,
        "downlink_kbps": session_ambr.get("downlink", "Unknown"),
        "uplink_kbps": session_ambr.get("uplink", "Unknown"),
        "pdu_session_types": dnn_config.get("pduSessionTypes", {}),
        "ssc_modes": dnn_config.get("sscModes", {})
    }


def extract_sm_context_id(ue_state_detail: str) -> Optional[str]:
    """
    Extract SM context ID from getuestatebyimsi output.

    Args:
        ue_state_detail: Raw output from getuestatebyimsi command

    Returns:
        SM context ID or None if not found
    """
    # Look for data lines containing 'imsi-' pattern (skip header lines with '?')
    # Data format: Registered\tNot Active\t1\t2,imsi-XXX_2_3GPP,ATTO5GC.SMF#1.SESSION_MANAGER
    # The 4th field contains comma-separated values including SM context ID
    lines = [line for line in ue_state_detail.strip().split('\n') if line.strip()]

    for line in lines:
        # Skip header lines (contain '?') and find data lines with 'imsi-' pattern
        if 'imsi-' in line and '?' not in line:
            parts = line.split('\t')
            if len(parts) >= 4:
                # Fourth field contains comma-separated values
                # Format: "pdu-session-id,sm-context-id,smf-instance-id"
                comma_parts = parts[3].split(',')
                if len(comma_parts) >= 2:
                    return comma_parts[1].strip()

    return None
