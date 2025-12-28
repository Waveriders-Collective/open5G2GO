#!/usr/bin/env python3
"""
OpenSurfControl MCP Server

MCP server for managing Open5GS 4G/LTE mobile core systems.
Provides tools for subscriber management, system monitoring, and network configuration.

Part of Open5G2GO - Homelab toolkit for private 4G cellular networks.
"""

import json
import logging
from enum import Enum
from ipaddress import IPv4Address, AddressValueError
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

# MCP SDK
from mcp.server.fastmcp import FastMCP

# Local modules
from .constants import (
    PLMNID,
    MCC,
    MNC,
    TAC,
    NETWORK_NAME_SHORT,
    NETWORK_NAME_LONG,
    IMSI_PREFIX,
    DEFAULT_APN,
    DEFAULT_K,
    DEFAULT_OPC,
    DEFAULT_AMBR_UL,
    DEFAULT_AMBR_DL,
    UE_POOL_START,
    UE_POOL_END,
    UE_GATEWAY,
    UE_DNS,
)
from .mongodb_client import (
    Open5GSClient,
    get_client,
    MongoDBConnectionError,
    SubscriberError,
    ValidationError as ClientValidationError,
)
from .formatters import (
    format_subscriber_list_markdown,
    format_subscriber_list_json,
    format_system_status_markdown,
    format_system_status_json,
    format_network_config_markdown,
    format_network_config_json,
    format_add_subscriber_result,
)
from .sas_client import get_sas_client, GoogleSASClient
from .mme_client import get_mme_parser, MMELogParser
from .grant_history import get_history_store, GrantHistoryStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("open5g2go_mcp")


# ============================================================================
# Pydantic Models for Input Validation
# ============================================================================

class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"


class BaseInput(BaseModel):
    """Base input model with response format."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )


class AddSubscriberInput(BaseModel):
    """Input model for adding a new subscriber."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    device_number: str = Field(
        ...,
        description="Device number (1-4 digits) used to generate IMSI (e.g., '0001' for CAM-01)",
        min_length=1,
        max_length=4,
        pattern=r"^\d{1,4}$"
    )
    device_name: Optional[str] = Field(
        default=None,
        description="Device name (e.g., 'CAM-01', 'TABLET-02'). Auto-generated if not provided.",
        min_length=1,
        max_length=50
    )
    apn: str = Field(
        default=DEFAULT_APN,
        description="Access Point Name (e.g., 'internet')",
        min_length=1,
        max_length=50
    )
    ip: Optional[str] = Field(
        default=None,
        description="Static IP address (optional). Leave blank for DHCP.",
        pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
    )

    @field_validator('device_number')
    @classmethod
    def validate_device_number(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Device number must contain only digits")
        num = int(v)
        if num < 1 or num > 9999:
            raise ValueError("Device number must be between 1 and 9999")
        return v.zfill(4)  # Zero-pad to 4 digits

    @field_validator('ip')
    @classmethod
    def validate_ip_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate IPv4 address format and range."""
        if v is None:
            return v
        try:
            ip = IPv4Address(v)
            # Validate IP is in the allowed pool range
            pool_start = IPv4Address(UE_POOL_START)
            pool_end = IPv4Address(UE_POOL_END)
            if not (pool_start <= ip <= pool_end):
                raise ValueError(
                    f"IP {v} must be in pool range {UE_POOL_START} - {UE_POOL_END}"
                )
            return str(ip)
        except AddressValueError:
            raise ValueError(f"Invalid IPv4 address: {v}")


class GetSubscriberInput(BaseModel):
    """Input model for getting a single subscriber."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    imsi: str = Field(
        ...,
        description="IMSI of subscriber to retrieve (15 digits)",
        min_length=15,
        max_length=15,
        pattern=r"^\d{15}$"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="Output format: 'markdown' or 'json'"
    )


class DeleteSubscriberInput(BaseModel):
    """Input model for deleting a subscriber."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    imsi: str = Field(
        ...,
        description="IMSI of subscriber to delete (15 digits)",
        min_length=15,
        max_length=15,
        pattern=r"^\d{15}$"
    )


class UpdateSubscriberInput(BaseModel):
    """Input model for updating subscriber details."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    imsi: str = Field(
        ...,
        description="IMSI of subscriber to update (15 digits)",
        min_length=15,
        max_length=15,
        pattern=r"^\d{15}$"
    )
    device_name: Optional[str] = Field(
        default=None,
        description="New device name (e.g., 'CAM-01')",
        min_length=1,
        max_length=50
    )


# ============================================================================
# Helper Functions
# ============================================================================

def _build_imsi(device_number: str) -> str:
    """
    Build full IMSI from device number.

    Args:
        device_number: Zero-padded 4-digit device number (e.g., "0001")

    Returns:
        Full 15-digit IMSI (e.g., "315010000000001")
    """
    return f"{IMSI_PREFIX}{device_number}"


def _generate_device_name(device_number: str) -> str:
    """
    Generate default device name from device number.

    Args:
        device_number: Zero-padded 4-digit device number

    Returns:
        Device name (e.g., "DEVICE-0001")
    """
    return f"DEVICE-{device_number}"


def _format_subscriber_for_list(subscriber: dict) -> dict:
    """
    Format Open5GS subscriber document for list display.

    Args:
        subscriber: Raw MongoDB subscriber document

    Returns:
        Simplified subscriber dict with name, imsi, service, ip
    """
    imsi = subscriber.get("imsi", "Unknown")
    name = subscriber.get("device_name", f"IMSI-{imsi[-4:]}")

    # Extract APN/DNN from slice configuration
    apn = DEFAULT_APN
    ip = "DHCP"

    if "slice" in subscriber and subscriber["slice"]:
        slice_data = subscriber["slice"][0]
        if "session" in slice_data and slice_data["session"]:
            session = slice_data["session"][0]
            apn = session.get("name", DEFAULT_APN)
            if "ue" in session and session["ue"].get("addr"):
                ip = session["ue"]["addr"]

    return {
        "imsi": imsi,
        "name": name,
        "service": apn,
        "ip": ip
    }


# ============================================================================
# Tool 1: List Subscribers
# ============================================================================

@mcp.tool(
    name="open5gs_list_subscribers",
    annotations={
        "title": "List Open5GS Subscribers",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def open5gs_list_subscribers(params: BaseInput) -> str:
    """
    List all provisioned subscribers (devices) on the Open5GS mobile core system.

    This tool retrieves the complete list of subscribers that have been provisioned
    on the Open5GS system, including their IMSI, device name, APN, and assigned
    static IP address.

    Args:
        params (BaseInput): Input parameters containing:
            - response_format (ResponseFormat): Output format - 'markdown' or 'json'

    Returns:
        str: Formatted list of subscribers.

    Examples:
        - Use when: "Show me all devices on the system"
        - Use when: "List all provisioned subscribers"
        - Use when: "How many devices are configured?"
    """
    try:
        client = get_client()
        raw_subscribers = client.list_subscribers()

        # Transform to display format
        subscribers = [_format_subscriber_for_list(s) for s in raw_subscribers]

        # Format response based on requested format
        if params.response_format == ResponseFormat.MARKDOWN:
            return format_subscriber_list_markdown(subscribers, "Open5GS")
        else:
            return format_subscriber_list_json(subscribers, "Open5GS")

    except MongoDBConnectionError as e:
        return f"Error: Cannot connect to Open5GS MongoDB. {str(e)}"
    except SubscriberError as e:
        return f"Error: Failed to retrieve subscriber list. {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in list_subscribers: {e}")
        return f"Error: Unexpected error occurred: {str(e)}"


# ============================================================================
# Tool 2: Get System Status
# ============================================================================

@mcp.tool(
    name="open5gs_get_system_status",
    annotations={
        "title": "Get Open5GS System Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def open5gs_get_system_status(params: BaseInput) -> str:
    """
    Check Open5GS system health and status dashboard.

    This tool provides a health check of the Open5GS mobile core system,
    including subscriber counts and database connection status.

    Note: Real-time eNodeB connection status and active UE counts require
    log parsing which is not yet implemented. These will show as 0.

    Args:
        params (BaseInput): Input parameters containing:
            - response_format (ResponseFormat): Output format - 'markdown' or 'json'

    Returns:
        str: System status report.

    Examples:
        - Use when: "Is the Open5GS system healthy?"
        - Use when: "How many devices are provisioned?"
    """
    try:
        client = get_client()
        status = client.get_system_status()

        provisioned = status.get("total_subscribers", 0)
        # Note: Registered/connected counts require log parsing (Phase 2+)
        registered = 0
        connected = 0

        # eNodeB status from logs (Phase 2+)
        enodebs = []

        if params.response_format == ResponseFormat.MARKDOWN:
            return format_system_status_markdown(
                provisioned,
                registered,
                connected,
                enodebs,
                "Open5GS"
            )
        else:
            return format_system_status_json(
                provisioned,
                registered,
                connected,
                enodebs,
                "Open5GS"
            )

    except MongoDBConnectionError as e:
        return f"Error: Cannot connect to Open5GS MongoDB. {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in get_system_status: {e}")
        return f"Error: Unexpected error occurred: {str(e)}"


# ============================================================================
# Tool 3: Get Active Connections
# ============================================================================

@mcp.tool(
    name="open5gs_get_active_connections",
    annotations={
        "title": "Get Active Open5GS Connections",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def open5gs_get_active_connections(params: BaseInput) -> str:
    """
    Show which devices are currently online with their IP addresses.

    Note: This feature requires Open5GS log parsing which is not yet implemented.
    Currently returns a placeholder response. Real-time connection tracking will
    be added in a future phase.

    Args:
        params (BaseInput): Input parameters containing:
            - response_format (ResponseFormat): Output format - 'markdown' or 'json'

    Returns:
        str: List of active connections (placeholder for MVP).

    Examples:
        - Use when: "Which devices are currently connected?"
        - Use when: "Show me all online devices"
    """
    # Phase 2+: Implement log parsing to get active connections
    # For now, return placeholder
    connections = []

    if params.response_format == ResponseFormat.MARKDOWN:
        return """# Open5GS Active Connections
**Status:** Feature pending implementation

Active connection tracking requires Open5GS log parsing, which will be
implemented in a future phase.

Use `open5gs_list_subscribers` to see all provisioned subscribers.
"""
    else:
        return json.dumps({
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            "total_active": 0,
            "connections": [],
            "note": "Real-time connection tracking requires log parsing (Phase 2+)"
        }, indent=2)


# ============================================================================
# Tool 4: Get Network Configuration
# ============================================================================

@mcp.tool(
    name="open5gs_get_network_config",
    annotations={
        "title": "Get Open5GS Network Configuration",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def open5gs_get_network_config(params: BaseInput) -> str:
    """
    Read network configuration including PLMNID, APN, and bandwidth settings.

    This tool retrieves the core network configuration from constants,
    including the network identity (PLMNID), default APN, and QoS settings.

    Args:
        params (BaseInput): Input parameters containing:
            - response_format (ResponseFormat): Output format - 'markdown' or 'json'

    Returns:
        str: Network configuration report.

    Examples:
        - Use when: "What is the PLMNID for the network?"
        - Use when: "Show me the APN configuration"
        - Use when: "What is the UE IP pool?"
    """
    # Build DNN configuration from constants
    dnns = [{
        "name": DEFAULT_APN,
        "downlink_kbps": f"{DEFAULT_AMBR_DL // 1000} Kbps",
        "uplink_kbps": f"{DEFAULT_AMBR_UL // 1000} Kbps"
    }]

    if params.response_format == ResponseFormat.MARKDOWN:
        return format_network_config_markdown(
            PLMNID,
            str(TAC),
            NETWORK_NAME_SHORT,
            dnns,
            "Open5GS"
        )
    else:
        return format_network_config_json(
            PLMNID,
            str(TAC),
            NETWORK_NAME_SHORT,
            dnns,
            "Open5GS"
        )


# ============================================================================
# Tool 5: Add Subscriber
# ============================================================================

@mcp.tool(
    name="open5gs_add_subscriber",
    annotations={
        "title": "Add Open5GS Subscriber",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def open5gs_add_subscriber(params: AddSubscriberInput) -> str:
    """
    Provision a new device (subscriber) on the Open5GS mobile core network.

    This tool provisions a new subscriber by:
    1. Generating the full IMSI from the device number (user enters last 4 digits)
    2. Using default K/OPc authentication keys (matching Waveriders SIM template)
    3. Setting up the APN and optional static IP

    Args:
        params (AddSubscriberInput): Input parameters containing:
            - device_number (str): Device number 1-9999 (e.g., "0001")
            - device_name (str, optional): Friendly name (e.g., "CAM-01")
            - apn (str): Access Point Name (default: "internet")
            - ip (str, optional): Static IP address (leave blank for DHCP)

    Returns:
        str: JSON formatted result.

    Examples:
        - Use when: "Add device 0001 as CAM-01"
        - Use when: "Provision a new camera with IP 10.48.99.10"

    Important Notes:
        - IMSI format: 315010000000XXX (XXX = user-provided device_number)
        - Uses Waveriders SIM template authentication keys
        - Default bandwidth: 100 Mbps downlink, 50 Mbps uplink
    """
    try:
        # Build IMSI from device number
        imsi = _build_imsi(params.device_number)

        # Generate device name if not provided
        device_name = params.device_name or _generate_device_name(params.device_number)

        # Add subscriber via MongoDB client
        client = get_client()
        subscriber = client.add_subscriber(
            imsi=imsi,
            k=DEFAULT_K,
            opc=DEFAULT_OPC,
            apn=params.apn,
            ip=params.ip,
            ambr_ul=DEFAULT_AMBR_UL,
            ambr_dl=DEFAULT_AMBR_DL,
            device_name=device_name
        )

        # Return success result
        return format_add_subscriber_result(
            success=True,
            imsi=imsi,
            name=device_name,
            ip=params.ip or "DHCP",
            dnn=params.apn
        )

    except ClientValidationError as e:
        return format_add_subscriber_result(
            success=False,
            imsi=_build_imsi(params.device_number) if params.device_number else "unknown",
            name=params.device_name or "unknown",
            ip=params.ip or "DHCP",
            dnn=params.apn,
            error_message=f"Validation error: {str(e)}"
        )
    except MongoDBConnectionError as e:
        return format_add_subscriber_result(
            success=False,
            imsi=_build_imsi(params.device_number) if params.device_number else "unknown",
            name=params.device_name or "unknown",
            ip=params.ip or "DHCP",
            dnn=params.apn,
            error_message=f"Cannot connect to MongoDB: {str(e)}"
        )
    except SubscriberError as e:
        return format_add_subscriber_result(
            success=False,
            imsi=_build_imsi(params.device_number) if params.device_number else "unknown",
            name=params.device_name or "unknown",
            ip=params.ip or "DHCP",
            dnn=params.apn,
            error_message=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in add_subscriber: {e}")
        return format_add_subscriber_result(
            success=False,
            imsi="unknown",
            name="unknown",
            ip="unknown",
            dnn=params.apn,
            error_message=f"Unexpected error: {str(e)}"
        )


# ============================================================================
# Tool 6: Get Subscriber
# ============================================================================

@mcp.tool(
    name="open5gs_get_subscriber",
    annotations={
        "title": "Get Subscriber Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def open5gs_get_subscriber(params: GetSubscriberInput) -> str:
    """
    Get detailed information for a single subscriber by IMSI.

    Returns the complete subscriber configuration including device name,
    APN configuration, static IP address, and QoS settings.

    Args:
        params (GetSubscriberInput): Input parameters containing:
            - imsi (str): 15-digit IMSI of subscriber to retrieve
            - response_format (ResponseFormat): Output format - 'markdown' or 'json'

    Returns:
        str: Subscriber details in requested format
    """
    try:
        client = get_client()
        subscriber = client.get_subscriber(params.imsi)

        if not subscriber:
            return json.dumps({
                "success": False,
                "error": f"Subscriber {params.imsi} not found"
            })

        # Extract display fields
        name = subscriber.get("device_name", f"IMSI-{params.imsi[-4:]}")
        apn = DEFAULT_APN
        ip = "DHCP"

        if "slice" in subscriber and subscriber["slice"]:
            slice_data = subscriber["slice"][0]
            if "session" in slice_data and slice_data["session"]:
                session = slice_data["session"][0]
                apn = session.get("name", DEFAULT_APN)
                if "ue" in session and session["ue"].get("addr"):
                    ip = session["ue"]["addr"]

        if params.response_format == ResponseFormat.JSON:
            return json.dumps({
                "success": True,
                "imsi": params.imsi,
                "name": name,
                "apn": apn,
                "ip": ip,
                "data": subscriber
            }, indent=2)
        else:
            return f"""## Subscriber Details

| Field | Value |
|-------|-------|
| IMSI | {params.imsi} |
| Name | {name} |
| APN | {apn} |
| Static IP | {ip} |

**Status:** Found
"""

    except ClientValidationError as e:
        return json.dumps({
            "success": False,
            "error": f"Validation error: {str(e)}"
        })
    except MongoDBConnectionError as e:
        return json.dumps({
            "success": False,
            "error": f"Cannot connect to MongoDB: {str(e)}"
        })
    except SubscriberError as e:
        return json.dumps({
            "success": False,
            "error": f"Database error: {str(e)}"
        })
    except Exception as e:
        logger.error(f"Unexpected error in get_subscriber: {e}")
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        })


# ============================================================================
# Tool 7: Delete Subscriber
# ============================================================================

@mcp.tool(
    name="open5gs_delete_subscriber",
    annotations={
        "title": "Delete Subscriber",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def open5gs_delete_subscriber(params: DeleteSubscriberInput) -> str:
    """
    Delete a subscriber from the Open5GS system.

    WARNING: This permanently removes the subscriber configuration.
    The device will no longer be able to connect to the network.

    Args:
        params (DeleteSubscriberInput): Input parameters containing:
            - imsi (str): 15-digit IMSI of subscriber to delete

    Returns:
        str: JSON result with success status
    """
    try:
        client = get_client()

        # First verify subscriber exists
        existing = client.get_subscriber(params.imsi)
        if not existing:
            return json.dumps({
                "success": False,
                "error": f"Subscriber {params.imsi} not found"
            })

        # Delete the subscriber
        deleted = client.delete_subscriber(params.imsi)

        if deleted:
            return json.dumps({
                "success": True,
                "message": f"Subscriber {params.imsi} deleted successfully"
            })
        else:
            return json.dumps({
                "success": False,
                "error": f"Failed to delete subscriber {params.imsi}"
            })

    except ClientValidationError as e:
        return json.dumps({
            "success": False,
            "error": f"Validation error: {str(e)}"
        })
    except MongoDBConnectionError as e:
        return json.dumps({
            "success": False,
            "error": f"Cannot connect to MongoDB: {str(e)}"
        })
    except SubscriberError as e:
        return json.dumps({
            "success": False,
            "error": f"Database error: {str(e)}"
        })
    except Exception as e:
        logger.error(f"Unexpected error in delete_subscriber: {e}")
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        })


# ============================================================================
# Tool 8: Update Subscriber
# ============================================================================

@mcp.tool(
    name="open5gs_update_subscriber",
    annotations={
        "title": "Update Subscriber",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def open5gs_update_subscriber(params: UpdateSubscriberInput) -> str:
    """
    Update subscriber details (device name).

    Note: For security, only the device_name field can be updated.
    IMSI and authentication keys (K/OPc) cannot be changed.
    To change IP or APN, delete and re-add the subscriber.

    Args:
        params (UpdateSubscriberInput): Input parameters containing:
            - imsi (str): 15-digit IMSI of subscriber to update
            - device_name (str, optional): New device name

    Returns:
        str: JSON result with success status and updated values
    """
    # Validate at least one field to update
    if not params.device_name:
        return json.dumps({
            "success": False,
            "error": "At least device_name must be provided for update"
        })

    try:
        client = get_client()

        # First verify subscriber exists
        existing = client.get_subscriber(params.imsi)
        if not existing:
            return json.dumps({
                "success": False,
                "error": f"Subscriber {params.imsi} not found"
            })

        # Build updates dict
        updates = {}
        changes_made = []

        if params.device_name:
            updates["device_name"] = params.device_name
            changes_made.append(f"device_name -> {params.device_name}")

        # Apply updates
        updated = client.update_subscriber(params.imsi, **updates)

        if updated:
            return json.dumps({
                "success": True,
                "imsi": params.imsi,
                "changes": changes_made,
                "message": f"Subscriber updated: {', '.join(changes_made)}"
            })
        else:
            return json.dumps({
                "success": False,
                "error": "No changes were applied (fields may already have these values)"
            })

    except ClientValidationError as e:
        return json.dumps({
            "success": False,
            "error": f"Validation error: {str(e)}"
        })
    except MongoDBConnectionError as e:
        return json.dumps({
            "success": False,
            "error": f"Cannot connect to MongoDB: {str(e)}"
        })
    except SubscriberError as e:
        return json.dumps({
            "success": False,
            "error": f"Database error: {str(e)}"
        })
    except Exception as e:
        logger.error(f"Unexpected error in update_subscriber: {e}")
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        })


# ============================================================================
# Tool 9: Get eNodeB Status (S1AP + SAS)
# ============================================================================

class EnodebStatusInput(BaseModel):
    """Input for eNodeB status query."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    serial_number: Optional[str] = Field(
        default=None,
        description="Specific eNodeB serial number. If omitted, returns all eNodeBs."
    )
    include_history: bool = Field(
        default=False,
        description="Include 24h grant history for each eNodeB"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="Output format: 'markdown' or 'json'"
    )


@mcp.tool(
    name="open5gs_get_enodeb_status",
    annotations={
        "title": "Get eNodeB Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def open5gs_get_enodeb_status(params: EnodebStatusInput) -> str:
    """
    Get combined eNodeB status from Open5GS (S1AP) and Google SAS (grants).

    This tool provides a unified view of eNodeB status showing:
    - S1AP connection status (is the eNodeB connected to the MME?)
    - SAS registration status (REGISTERED, DEREGISTERED)
    - Active grant status (AUTHORIZED, SUSPENDED, EXPIRED)
    - Grant frequency range and power level

    Args:
        params (EnodebStatusInput): Input parameters containing:
            - serial_number (str, optional): Specific eNodeB serial
            - include_history (bool): Include 24h grant state changes
            - response_format (ResponseFormat): Output format

    Returns:
        str: eNodeB status in requested format.

    Examples:
        - Use when: "Is the eNodeB connected?"
        - Use when: "What is the SAS grant status?"
        - Use when: "Show me all eNodeB status"
    """
    try:
        # Get S1AP connection status from MME logs
        mme = get_mme_parser()
        s1ap_status = mme.get_connection_status_summary()

        # Get SAS status from Google API
        sas = get_sas_client()
        sas_status = sas.get_status_summary()

        # Combine statuses
        combined = {
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            "s1ap": {
                "available": s1ap_status.get("available", False),
                "connected_count": s1ap_status.get("total_connected", 0),
                "enodebs": s1ap_status.get("enodebs", [])
            },
            "sas": {
                "available": sas_status.get("available", False),
                "registered_count": sas_status.get("registered", 0),
                "authorized_count": sas_status.get("authorized", 0),
                "enodebs": sas_status.get("enodebs", [])
            }
        }

        # If specific serial requested, filter to that eNodeB
        if params.serial_number:
            sas_enb = next(
                (e for e in combined["sas"]["enodebs"]
                 if e.get("serial_number") == params.serial_number),
                None
            )

            if sas_enb and params.include_history:
                history_store = get_history_store()
                sas_enb["grant_history"] = history_store.get_grant_state_changes(
                    params.serial_number, hours=24
                )

            combined["sas"]["enodebs"] = [sas_enb] if sas_enb else []

        # Format response
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(combined, indent=2, default=str)
        else:
            return _format_enodeb_status_markdown(combined)

    except Exception as e:
        logger.error(f"Error getting eNodeB status: {e}")
        return json.dumps({
            "success": False,
            "error": f"Failed to get eNodeB status: {str(e)}"
        })


def _format_enodeb_status_markdown(status: dict) -> str:
    """Format eNodeB status as markdown."""
    lines = ["# eNodeB Status\n"]

    # S1AP Section
    s1ap = status.get("s1ap", {})
    lines.append("## S1AP Connection (Open5GS MME)")
    if not s1ap.get("available"):
        lines.append("*S1AP status unavailable - MME logs not accessible*\n")
    else:
        lines.append(f"**Connected eNodeBs:** {s1ap.get('connected_count', 0)}\n")
        for enb in s1ap.get("enodebs", []):
            lines.append(f"- {enb.get('name', 'Unknown')} ({enb.get('ip', 'N/A')})")

    # SAS Section
    sas = status.get("sas", {})
    lines.append("\n## SAS Registration (Google CBRS)")
    if not sas.get("available"):
        lines.append("*SAS status unavailable - API not configured*\n")
    else:
        lines.append(f"**Registered:** {sas.get('registered_count', 0)}")
        lines.append(f"**Authorized (Active Grant):** {sas.get('authorized_count', 0)}\n")

        for enb in sas.get("enodebs", []):
            name = enb.get("config_name", enb.get("serial_number", "Unknown"))
            state = enb.get("sas_state", "UNKNOWN")
            grant = enb.get("active_grant")

            lines.append(f"### {name}")
            lines.append(f"- **Serial:** {enb.get('serial_number', 'N/A')}")
            lines.append(f"- **FCC ID:** {enb.get('fcc_id', 'N/A')}")
            lines.append(f"- **SAS State:** {state}")

            if grant:
                freq = grant.get("frequency_mhz", {})
                lines.append(f"- **Grant:** {grant.get('state', 'N/A')}")
                lines.append(f"- **Frequency:** {freq.get('low', '?')}-{freq.get('high', '?')} MHz")
                lines.append(f"- **Channel Type:** {grant.get('channel_type', 'N/A')}")
            else:
                lines.append("- **Grant:** No active grant")

            lines.append("")

    return "\n".join(lines)


# ============================================================================
# Tool 10: Get SAS Grant History
# ============================================================================

class GrantHistoryInput(BaseModel):
    """Input for grant history query."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    serial_number: str = Field(
        ...,
        description="eNodeB serial number to get history for"
    )
    hours: int = Field(
        default=24,
        description="Number of hours of history to retrieve (max 168)",
        ge=1,
        le=168
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="Output format: 'markdown' or 'json'"
    )


@mcp.tool(
    name="open5gs_get_grant_history",
    annotations={
        "title": "Get SAS Grant History",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def open5gs_get_grant_history(params: GrantHistoryInput) -> str:
    """
    Get SAS grant state change history for an eNodeB.

    Shows grant state transitions over time, including:
    - When grants were authorized
    - When grants were suspended (DPA events)
    - When grants expired or were terminated

    Args:
        params (GrantHistoryInput): Input parameters containing:
            - serial_number (str): eNodeB serial number
            - hours (int): Hours of history (default 24, max 168)
            - response_format (ResponseFormat): Output format

    Returns:
        str: Grant history in requested format.

    Examples:
        - Use when: "Show me grant history for eNodeB-01"
        - Use when: "Were there any DPA suspensions today?"
    """
    try:
        history_store = get_history_store()

        # Get state changes
        changes = history_store.get_grant_state_changes(
            params.serial_number,
            hours=params.hours
        )

        result = {
            "serial_number": params.serial_number,
            "hours": params.hours,
            "total_changes": len(changes),
            "changes": changes
        }

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(result, indent=2, default=str)
        else:
            return _format_grant_history_markdown(result)

    except Exception as e:
        logger.error(f"Error getting grant history: {e}")
        return json.dumps({
            "success": False,
            "error": f"Failed to get grant history: {str(e)}"
        })


def _format_grant_history_markdown(history: dict) -> str:
    """Format grant history as markdown."""
    lines = [
        f"# Grant History: {history.get('serial_number', 'Unknown')}",
        f"**Time Range:** Last {history.get('hours', 24)} hours",
        f"**Total State Changes:** {history.get('total_changes', 0)}\n",
    ]

    changes = history.get("changes", [])
    if not changes:
        lines.append("*No state changes recorded in this period*")
    else:
        lines.append("| Timestamp | Type | From | To |")
        lines.append("|-----------|------|------|-----|")
        for change in changes:
            ts = change.get("timestamp", "")
            if hasattr(ts, "strftime"):
                ts = ts.strftime("%Y-%m-%d %H:%M")
            change_type = change.get("type", "unknown")
            from_state = change.get("from_state", "-")
            to_state = change.get("to_state", "-")
            lines.append(f"| {ts} | {change_type} | {from_state} | {to_state} |")

    return "\n".join(lines)


# ============================================================================
# Tool 11: Refresh SAS Status (Poll and Store)
# ============================================================================

@mcp.tool(
    name="open5gs_refresh_sas_status",
    annotations={
        "title": "Refresh SAS Status",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def open5gs_refresh_sas_status(params: BaseInput) -> str:
    """
    Poll Google SAS API and store current grant status.

    This tool manually triggers a SAS status poll and stores the
    snapshot for history tracking. Normally this runs automatically
    on a timer, but can be triggered manually.

    Args:
        params (BaseInput): Input parameters containing:
            - response_format (ResponseFormat): Output format

    Returns:
        str: Poll results.
    """
    try:
        sas = get_sas_client()

        if not sas.is_available():
            return json.dumps({
                "success": False,
                "error": "SAS API not configured. Check GOOGLE_APPLICATION_CREDENTIALS."
            })

        # Get all eNodeB statuses
        statuses = sas.get_all_enodeb_status()

        # Store snapshots
        history_store = get_history_store()
        stored = history_store.store_all_snapshots(statuses)

        # Cleanup old history
        config = sas.config
        hours = config.get("grant_history_hours", 24)
        deleted = history_store.cleanup_old_history(hours)

        result = {
            "success": True,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            "enodebs_polled": len(statuses),
            "snapshots_stored": stored,
            "old_records_cleaned": deleted,
            "statuses": statuses
        }

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(result, indent=2, default=str)
        else:
            return f"""# SAS Status Refresh

**Timestamp:** {result['timestamp']}
**eNodeBs Polled:** {result['enodebs_polled']}
**Snapshots Stored:** {result['snapshots_stored']}
**Old Records Cleaned:** {result['old_records_cleaned']}

Refresh complete. Use `open5gs_get_enodeb_status` to view current status.
"""

    except Exception as e:
        logger.error(f"Error refreshing SAS status: {e}")
        return json.dumps({
            "success": False,
            "error": f"Failed to refresh SAS status: {str(e)}"
        })


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
