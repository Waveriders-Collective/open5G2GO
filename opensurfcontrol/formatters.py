# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Waveriders Collective Inc.

"""
Response formatters for OpenSurfControl MCP server.

Functions to format tool responses in JSON and Markdown formats,
following MCP best practices for human-readable vs machine-readable output.

Part of Open5G2GO - Homelab toolkit for private 4G cellular networks.
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from .constants import CHARACTER_LIMIT


def format_timestamp() -> str:
    """
    Generate human-readable timestamp.

    Returns:
        ISO 8601 formatted timestamp (e.g., "2024-01-15 10:30:00 UTC")
    """
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def truncate_if_needed(content: str, item_count: Optional[int] = None) -> str:
    """
    Truncate response if it exceeds CHARACTER_LIMIT.

    Args:
        content: Response content to check/truncate
        item_count: Optional count of items in response for helpful message

    Returns:
        Original or truncated content with truncation notice
    """
    if len(content) <= CHARACTER_LIMIT:
        return content

    # Truncate to CHARACTER_LIMIT
    truncated = content[:CHARACTER_LIMIT]

    # Add truncation notice
    notice = f"\n\n[TRUNCATED - Response exceeded {CHARACTER_LIMIT} characters"
    if item_count:
        notice += f". Showing partial results. Use filtering or pagination to see more]"
    else:
        notice += ". Use filtering to reduce result size]"

    return truncated + notice


def format_subscriber_list_markdown(
    subscribers: List[Dict[str, str]],
    host: str
) -> str:
    """
    Format subscriber list as Markdown.

    Args:
        subscribers: List of subscriber dictionaries
        host: System identifier (e.g., "Open5GS")

    Returns:
        Markdown formatted string
    """
    lines = [
        "# Open5GS Subscriber List",
        f"**Host:** {host}",
        f"**Timestamp:** {format_timestamp()}",
        f"**Total Subscribers:** {len(subscribers)}",
        ""
    ]

    if not subscribers:
        lines.append("*No subscribers provisioned*")
        return "\n".join(lines)

    # Group by service type
    by_service: Dict[str, List[Dict[str, str]]] = {}
    for sub in subscribers:
        service = sub.get("service", "unknown")
        if service not in by_service:
            by_service[service] = []
        by_service[service].append(sub)

    # Display by service groups
    for service, subs in sorted(by_service.items()):
        lines.append(f"## Service: {service.upper()}")
        lines.append(f"*{len(subs)} subscriber(s)*")
        lines.append("")

        for sub in subs:
            lines.append(f"### {sub['name']}")
            lines.append(f"- **IMSI:** {sub['imsi']}")
            lines.append(f"- **Static IP:** {sub['ip']}")
            lines.append("")

    return truncate_if_needed("\n".join(lines), len(subscribers))


def format_subscriber_list_json(
    subscribers: List[Dict[str, str]],
    host: str
) -> str:
    """
    Format subscriber list as JSON.

    Args:
        subscribers: List of subscriber dictionaries
        host: System identifier (e.g., "Open5GS")

    Returns:
        JSON formatted string
    """
    response = {
        "host": host,
        "timestamp": format_timestamp(),
        "total": len(subscribers),
        "subscribers": subscribers
    }

    json_str = json.dumps(response, indent=2)
    return truncate_if_needed(json_str, len(subscribers))


def format_system_status_markdown(
    provisioned: int,
    registered: int,
    connected: int,
    gnbs: List[Dict[str, str]],
    host: str
) -> str:
    """
    Format system status as Markdown.

    Args:
        provisioned: Total provisioned subscribers
        registered: Currently registered UEs
        connected: Currently connected UEs
        gnbs: List of connected eNodeBs/gNodeBs
        host: System identifier (e.g., "Open5GS")

    Returns:
        Markdown formatted string
    """
    lines = [
        "# Open5GS System Status",
        f"**Host:** {host}",
        f"**Timestamp:** {format_timestamp()}",
        "",
        "## Subscriber Summary",
        f"- **Provisioned:** {provisioned} subscriber(s)",
        f"- **Registered:** {registered} UE(s)",
        f"- **Connected:** {connected} UE(s)",
        ""
    ]

    # eNodeB/gNodeB status
    lines.append("## Connected Base Stations")
    if gnbs:
        lines.append(f"*{len(gnbs)} base station(s) connected*")
        lines.append("")

        for gnb in gnbs:
            lines.append(f"### {gnb['name']}")
            lines.append(f"- **ID:** {gnb['id']}")
            lines.append(f"- **IP Address:** {gnb['ip']}")
            lines.append("")
    else:
        lines.append("*No base stations detected (requires log parsing)*")
        lines.append("")

    # Health assessment
    lines.append("## System Health")
    lines.append("- **Core Status:** Operational (MongoDB connected)")

    if connected > 0:
        lines.append(f"- **Active UEs:** {connected} device(s) connected")
    elif registered > 0:
        lines.append(f"- **Active UEs:** {registered} registered but not connected")
    else:
        lines.append("- **Active UEs:** Connection tracking requires log parsing")

    return "\n".join(lines)


def _determine_operational_status(gnb_count: int, connected_count: int) -> str:
    """
    Determine the operational status based on base station and connection state.

    Returns:
        str: One of 'fully_operational', 'core_and_network_ready', 'core_ready'
    """
    if gnb_count == 0:
        return "core_ready"              # LTE Core Ready (awaiting base station detection)
    elif connected_count > 0:
        return "fully_operational"       # Fully Operational (subscribers connected)
    else:
        return "core_and_network_ready"  # Core and Network Ready (base stations connected)


def format_system_status_json(
    provisioned: int,
    registered: int,
    connected: int,
    gnbs: List[Dict[str, str]],
    host: str
) -> str:
    """
    Format system status as JSON.

    Args:
        provisioned: Total provisioned subscribers
        registered: Currently registered UEs
        connected: Currently connected UEs
        gnbs: List of connected eNodeBs/gNodeBs
        host: System identifier (e.g., "Open5GS")

    Returns:
        JSON formatted string
    """
    response = {
        "host": host,
        "timestamp": format_timestamp(),
        "subscribers": {
            "provisioned": provisioned,
            "registered": registered,
            "connected": connected
        },
        "gnodebs": {
            "total": len(gnbs),
            "list": gnbs
        },
        "health": {
            "core_operational": True,  # If we can retrieve this data, core is operational
            "has_active_connections": connected > 0,
            "gnodebs_connected": len(gnbs) > 0,
            "operational_status": _determine_operational_status(len(gnbs), connected)
        }
    }

    return json.dumps(response, indent=2)


def format_active_connections_markdown(
    connections: List[Dict[str, Any]],
    host: str
) -> str:
    """
    Format active connections as Markdown.

    Args:
        connections: List of active connection dictionaries
        host: System identifier (e.g., "Open5GS")

    Returns:
        Markdown formatted string
    """
    lines = [
        "# Open5GS Active Connections",
        f"**Host:** {host}",
        f"**Timestamp:** {format_timestamp()}",
        f"**Total Active:** {len(connections)} device(s)",
        ""
    ]

    if not connections:
        lines.append("*No active connections*")
        return "\n".join(lines)

    for conn in connections:
        lines.append(f"## ● {conn['name']}")
        lines.append(f"- **IMSI:** {conn['imsi']}")
        lines.append(f"- **Connection State:** {conn['cm_state']}")
        lines.append(f"- **Registration:** {conn['rm_state']}")

        if conn.get('ip'):
            lines.append(f"- **IP Address:** {conn['ip']}")
        if conn.get('dnn'):
            lines.append(f"- **DNN:** {conn['dnn']}")
        if conn.get('session_id'):
            lines.append(f"- **PDU Session ID:** {conn['session_id']}")

        lines.append("")

    return truncate_if_needed("\n".join(lines), len(connections))


def format_active_connections_json(
    connections: List[Dict[str, Any]],
    host: str
) -> str:
    """
    Format active connections as JSON.

    Args:
        connections: List of active connection dictionaries
        host: System identifier (e.g., "Open5GS")

    Returns:
        JSON formatted string
    """
    response = {
        "host": host,
        "timestamp": format_timestamp(),
        "total_active": len(connections),
        "connections": connections
    }

    json_str = json.dumps(response, indent=2)
    return truncate_if_needed(json_str, len(connections))


def format_network_config_markdown(
    plmnid: str,
    tac: str,
    network_name: str,
    dnns: List[Dict[str, str]],
    host: str
) -> str:
    """
    Format network configuration as Markdown.

    Args:
        plmnid: PLMN ID (e.g., "315010")
        tac: Tracking Area Code
        network_name: Network name
        dnns: List of DNN/APN configurations
        host: System identifier (e.g., "Open5GS")

    Returns:
        Markdown formatted string
    """
    mcc = plmnid[:3]
    mnc = plmnid[3:]

    lines = [
        "# Open5GS Network Configuration",
        f"**Host:** {host}",
        f"**Timestamp:** {format_timestamp()}",
        "",
        "## Network Identity",
        f"- **PLMNID:** {plmnid} (MCC: {mcc}, MNC: {mnc})",
        f"- **Network Name:** {network_name}",
        f"- **Tracking Area Code:** {tac}",
        "",
        "## Data Network Names (DNNs)"
    ]

    if dnns:
        lines.append(f"*{len(dnns)} DNN(s) configured*")
        lines.append("")

        for dnn in dnns:
            lines.append(f"### {dnn['name']}")
            lines.append(f"- **Downlink:** {dnn['downlink_kbps']}")
            lines.append(f"- **Uplink:** {dnn['uplink_kbps']}")
            lines.append("")
    else:
        lines.append("*No DNNs configured*")

    return "\n".join(lines)


def format_network_config_json(
    plmnid: str,
    tac: str,
    network_name: str,
    dnns: List[Dict[str, str]],
    host: str
) -> str:
    """
    Format network configuration as JSON.

    Args:
        plmnid: PLMN ID (e.g., "315010")
        tac: Tracking Area Code
        network_name: Network name
        dnns: List of DNN/APN configurations
        host: System identifier (e.g., "Open5GS")

    Returns:
        JSON formatted string
    """
    mcc = plmnid[:3]
    mnc = plmnid[3:]

    response = {
        "host": host,
        "timestamp": format_timestamp(),
        "network_identity": {
            "plmnid": plmnid,
            "mcc": mcc,
            "mnc": mnc,
            "network_name": network_name,
            "tac": tac
        },
        "dnns": {
            "total": len(dnns),
            "list": dnns
        }
    }

    return json.dumps(response, indent=2)


def format_add_subscriber_result(
    success: bool,
    imsi: str,
    name: str,
    ip: str,
    dnn: str,
    error_message: Optional[str] = None
) -> str:
    """
    Format add subscriber result as JSON.

    Args:
        success: Whether provisioning succeeded
        imsi: Subscriber IMSI
        name: Subscriber name
        ip: Assigned IP address
        dnn: DNN name
        error_message: Error message if failed

    Returns:
        JSON formatted string
    """
    response = {
        "success": success,
        "timestamp": format_timestamp(),
        "subscriber": {
            "imsi": imsi,
            "name": name,
            "ip": ip,
            "dnn": dnn
        }
    }

    if not success and error_message:
        response["error"] = error_message

    return json.dumps(response, indent=2)
