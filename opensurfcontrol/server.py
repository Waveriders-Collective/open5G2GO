#!/usr/bin/env python3
"""
Attocore MCP Server

MCP server for managing Attocore 5G/4G mobile core systems.
Provides tools for subscriber management, system monitoring, and network configuration.
"""

import json
import logging
from enum import Enum
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict

# MCP SDK
from mcp.server.fastmcp import FastMCP

# Local modules
from .constants import (
    DEFAULT_HOST,
    CLI_LIST_UES,
    CLI_COUNT_SUBS,
    CLI_COUNT_STATE,
    CLI_GNB_STATE,
    CLI_LIST_UE_STATE,
    CLI_GET_UE_STATE,
    CLI_GET_PDU_SESSION,
    CLI_GET_ATTR,
    CLI_GET_ATTR_SIMPLE,
    CLI_LIST_SHARED_DATA,
    CLI_GET_SHARED_DATA,
    CLI_CREATE_UE,
    CLI_GET_UE,
    CLI_DELETE_UE,
    IMSI_PREFIX,
    IP_MODE_OLD_SUBNET,
    IP_MODE_OLD_OFFSET,
    IP_MODE_NEW_SUBNET,
    DEFAULT_DNN,
    PLMNID,
    AUTH_K_KEY,
    AUTH_OPC_KEY,
    SHARED_AM_ID_TEMPLATE,
    SHARED_SMF_ID_TEMPLATE,
    DEFAULT_DOWNLINK_KBPS,
    DEFAULT_UPLINK_KBPS,
)
from .ssh_client import AttocoreSSHClient, SSHConnectionError, SSHCommandError
from .parsers import (
    parse_subscriber_list,
    parse_ue_state_counts,
    parse_gnb_state,
    parse_ue_state_list,
    parse_pdu_session_info,
    parse_json_output,
    extract_dnn_names_from_shared_data,
    extract_dnn_config,
    extract_sm_context_id,
)
from .formatters import (
    format_subscriber_list_markdown,
    format_subscriber_list_json,
    format_system_status_markdown,
    format_system_status_json,
    format_active_connections_markdown,
    format_active_connections_json,
    format_network_config_markdown,
    format_network_config_json,
    format_add_subscriber_result,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("attocore_mcp")


# ============================================================================
# Pydantic Models for Input Validation
# ============================================================================

class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"


class AttocoreHostInput(BaseModel):
    """Base input model with host and response format."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    host: str = Field(
        default=DEFAULT_HOST,
        description=f"Attocore system IP address (e.g., '10.48.98.5', '192.168.1.100')"
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

    device_number: int = Field(
        ...,
        ge=1,
        le=999,
        description="Device number (1-999) used to generate IMSI and name (e.g., 18 for WR-VIDEO-18)"
    )
    name_prefix: str = Field(
        default="WR-VIDEO",
        description="Device name prefix (e.g., 'WR-VIDEO', 'WR-iVIDEO' for iPhone, 'WR-VIDEO-e' for eSIM)",
        min_length=1,
        max_length=20
    )
    dnn: str = Field(
        default=DEFAULT_DNN,
        description="Data Network Name (e.g., 'video', 'internet')",
        min_length=1,
        max_length=50
    )
    ip_mode: Literal["old", "new"] = Field(
        default="old",
        description="IP addressing mode: 'old' (10.48.100.x, offset +10) or 'new' (10.48.98.x, direct)"
    )
    host: str = Field(
        default=DEFAULT_HOST,
        description="Attocore system IP address"
    )
    imsi: str = Field(
        ...,
        description="IMSI (15 digits)",
        min_length=15,
        max_length=15,
        pattern=r"^\d{15}$"
    )

    @field_validator('device_number')
    @classmethod
    def validate_device_number(cls, v: int) -> int:
        if v < 1 or v > 999:
            raise ValueError("Device number must be between 1 and 999")
        return v

    @field_validator('imsi')
    @classmethod
    def validate_imsi(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 15:
            raise ValueError("IMSI must be exactly 15 digits")
        return v


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
    host: str = Field(
        default=DEFAULT_HOST,
        description="Attocore system IP address"
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
    host: str = Field(
        default=DEFAULT_HOST,
        description="Attocore system IP address"
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
    ip: Optional[str] = Field(
        default=None,
        description="New static IP address (e.g., '10.48.100.50')",
        pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
    )
    dnn: Optional[str] = Field(
        default=None,
        description="New Data Network Name (e.g., 'video', 'internet')",
        min_length=1,
        max_length=50
    )
    name: Optional[str] = Field(
        default=None,
        description="New subscriber name (e.g., 'WR-VIDEO-01')",
        min_length=1,
        max_length=50
    )
    host: str = Field(
        default=DEFAULT_HOST,
        description="Attocore system IP address"
    )


# ============================================================================
# Tool 1: List Subscribers
# ============================================================================

@mcp.tool(
    name="attocore_list_subscribers",
    annotations={
        "title": "List Attocore Subscribers",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def attocore_list_subscribers(params: AttocoreHostInput) -> str:
    """
    List all provisioned subscribers (devices) on the Attocore mobile core system.

    This tool retrieves the complete list of subscribers that have been provisioned
    on the Attocore system, including their IMSI, device name, service type, and
    assigned static IP address. This is useful for checking what devices are
    configured and verifying subscriber provisioning.

    Args:
        params (AttocoreHostInput): Input parameters containing:
            - host (str): Attocore system IP address (default: 10.48.98.5)
            - response_format (ResponseFormat): Output format - 'markdown' or 'json'

    Returns:
        str: Formatted list of subscribers. Format depends on response_format:

        Markdown format:
        - Human-readable list grouped by service type
        - Shows device names, IMSIs, and IP addresses
        - Includes total count

        JSON format:
        ```json
        {
          "host": "10.48.98.5",
          "timestamp": "2024-01-15 10:30:00 UTC",
          "total": 15,
          "subscribers": [
            {
              "imsi": "999773308170001",
              "name": "WR-VIDEO-01",
              "service": "video",
              "ip": "10.48.100.11"
            }
          ]
        }
        ```

    Examples:
        - Use when: "Show me all devices on the NHL system"
        - Use when: "List all provisioned subscribers"
        - Use when: "How many devices are configured?"
        - Don't use when: You need to see which devices are currently connected (use attocore_get_active_connections instead)

    Error Handling:
        - Returns clear error message if SSH connection fails
        - Returns "No subscribers provisioned" if list is empty
        - Handles network timeouts gracefully
    """
    try:
        async with AttocoreSSHClient(host=params.host) as client:
            # Execute listues command
            output = await client.execute_command(CLI_LIST_UES)

            # Parse the output
            subscribers = parse_subscriber_list(output)

            # Format response based on requested format
            if params.response_format == ResponseFormat.MARKDOWN:
                return format_subscriber_list_markdown(subscribers, params.host)
            else:
                return format_subscriber_list_json(subscribers, params.host)

    except SSHConnectionError as e:
        return f"Error: Cannot connect to Attocore system at {params.host}. {str(e)}"
    except SSHCommandError as e:
        return f"Error: Failed to retrieve subscriber list. {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in list_subscribers: {e}")
        return f"Error: Unexpected error occurred: {str(e)}"


# ============================================================================
# Tool 2: Get System Status
# ============================================================================

@mcp.tool(
    name="attocore_get_system_status",
    annotations={
        "title": "Get Attocore System Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def attocore_get_system_status(params: AttocoreHostInput) -> str:
    """
    Check Attocore system health and status dashboard.

    This tool provides a comprehensive health check of the Attocore mobile core system,
    including subscriber counts, device registration/connection states, and cell tower
    (gNodeB) connectivity. Use this to monitor system health and troubleshoot connectivity
    issues.

    Args:
        params (AttocoreHostInput): Input parameters containing:
            - host (str): Attocore system IP address (default: 10.48.98.5)
            - response_format (ResponseFormat): Output format - 'markdown' or 'json'

    Returns:
        str: System status report. Format depends on response_format:

        Markdown format:
        - Human-readable dashboard with emoji indicators
        - Subscriber summary (provisioned, registered, connected)
        - Connected gNodeBs (cell towers) with IDs and IPs
        - Overall health assessment

        JSON format:
        ```json
        {
          "host": "10.48.98.5",
          "timestamp": "2024-01-15 10:30:00 UTC",
          "subscribers": {
            "provisioned": 15,
            "registered": 1,
            "connected": 1
          },
          "gnodebs": {
            "total": 1,
            "list": [{"id": "F2240-0121", "ip": "10.48.98.50", "name": "Waveriders-gNodeB-01"}]
          },
          "health": {
            "core_operational": true,
            "has_active_connections": true
          }
        }
        ```

    Examples:
        - Use when: "Is the NHL Attocore system healthy?"
        - Use when: "Are any gNodeBs connected?"
        - Use when: "How many devices are currently connected?"
        - Don't use when: You need detailed information about specific connected devices (use attocore_get_active_connections instead)

    Error Handling:
        - Returns clear error message if SSH connection fails
        - Handles cases where no gNodeBs are connected
        - Shows warning indicators for unhealthy states
    """
    try:
        async with AttocoreSSHClient(host=params.host) as client:
            # Execute multiple commands to gather status
            provisioned_output = await client.execute_command(CLI_COUNT_SUBS)
            state_output = await client.execute_command(CLI_COUNT_STATE)
            gnb_output = await client.execute_command(CLI_GNB_STATE)

            # Parse outputs
            provisioned = int(provisioned_output.strip())
            state_counts = parse_ue_state_counts(state_output)
            gnbs = parse_gnb_state(gnb_output)

            # Format response
            if params.response_format == ResponseFormat.MARKDOWN:
                return format_system_status_markdown(
                    provisioned,
                    state_counts["registered"],
                    state_counts["connected"],
                    gnbs,
                    params.host
                )
            else:
                return format_system_status_json(
                    provisioned,
                    state_counts["registered"],
                    state_counts["connected"],
                    gnbs,
                    params.host
                )

    except SSHConnectionError as e:
        return f"Error: Cannot connect to Attocore system at {params.host}. {str(e)}"
    except SSHCommandError as e:
        return f"Error: Failed to retrieve system status. {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in get_system_status: {e}")
        return f"Error: Unexpected error occurred: {str(e)}"


# ============================================================================
# Tool 3: Get Active Connections
# ============================================================================

@mcp.tool(
    name="attocore_get_active_connections",
    annotations={
        "title": "Get Active Attocore Connections",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def attocore_get_active_connections(params: AttocoreHostInput) -> str:
    """
    Show which devices are currently online with their IP addresses and connection details.

    This tool performs a multi-step analysis to identify all devices that are actively
    connected to the Attocore mobile core network. For each connected device, it retrieves
    the device name, IMSI, assigned IP address, DNN (data network), and connection state.
    This is useful for troubleshooting connectivity issues and monitoring real-time network usage.

    Args:
        params (AttocoreHostInput): Input parameters containing:
            - host (str): Attocore system IP address (default: 10.48.98.5)
            - response_format (ResponseFormat): Output format - 'markdown' or 'json'

    Returns:
        str: List of active connections. Format depends on response_format:

        Markdown format:
        - Human-readable list of connected devices
        - Shows device name, IMSI, IP address, DNN, connection state
        - Grouped by device with clear indicators

        JSON format:
        ```json
        {
          "host": "10.48.98.5",
          "timestamp": "2024-01-15 10:30:00 UTC",
          "total_active": 1,
          "connections": [
            {
              "imsi": "999773308170005",
              "name": "WR-VIDEO-05",
              "cm_state": "CONNECTED",
              "rm_state": "REGISTERED",
              "ip": "10.48.100.15",
              "dnn": "video",
              "session_id": "1"
            }
          ]
        }
        ```

    Examples:
        - Use when: "Which devices are currently connected?"
        - Use when: "Show me all online devices with their IPs"
        - Use when: "Is WR-VIDEO-05 connected right now?"
        - Don't use when: You just need subscriber counts (use attocore_get_system_status instead)
        - Don't use when: You need the full list of provisioned devices (use attocore_list_subscribers instead)

    Error Handling:
        - Returns "No active connections" if no devices are connected
        - Handles partial data gracefully (e.g., registered but no IP assigned yet)
        - Returns clear error messages for SSH/CLI failures
    """
    try:
        async with AttocoreSSHClient(host=params.host) as client:
            # Step 1: Get list of UEs with active state
            ue_state_output = await client.execute_command(CLI_LIST_UE_STATE)
            ue_states = parse_ue_state_list(ue_state_output)

            if not ue_states:
                # No active connections
                if params.response_format == ResponseFormat.MARKDOWN:
                    return format_active_connections_markdown([], params.host)
                else:
                    return format_active_connections_json([], params.host)

            # Step 2: Get subscriber list to map IMSI to names
            subscribers_output = await client.execute_command(CLI_LIST_UES)
            subscribers = parse_subscriber_list(subscribers_output)
            imsi_to_name = {sub["imsi"]: sub["name"] for sub in subscribers}

            # Step 3: For each active UE, get detailed info including IP
            connections = []
            for ue_state in ue_states:
                imsi = ue_state["imsi"].replace("imsi-", "")
                name = imsi_to_name.get(imsi, "Unknown")

                connection_info = {
                    "imsi": imsi,
                    "name": name,
                    "cm_state": ue_state["cm_state"],
                    "rm_state": ue_state["rm_state"]
                }

                # Get detailed UE state to find PDU session
                try:
                    ue_detail_cmd = CLI_GET_UE_STATE.format(imsi=imsi)
                    ue_detail = await client.execute_command(ue_detail_cmd)
                    sm_context_id = extract_sm_context_id(ue_detail)

                    if sm_context_id:
                        # Get PDU session information (IP, DNN)
                        pdu_cmd = CLI_GET_PDU_SESSION.format(id=sm_context_id)
                        pdu_output = await client.execute_command(pdu_cmd)
                        pdu_info = parse_pdu_session_info(pdu_output)

                        if pdu_info:
                            connection_info["ip"] = pdu_info["ip"]
                            connection_info["dnn"] = pdu_info["dnn"]
                            connection_info["session_id"] = pdu_info["session_id"]

                except Exception as e:
                    logger.warning(f"Could not retrieve PDU session for {imsi}: {e}")
                    # Continue without IP/DNN info

                connections.append(connection_info)

            # Format response
            if params.response_format == ResponseFormat.MARKDOWN:
                return format_active_connections_markdown(connections, params.host)
            else:
                return format_active_connections_json(connections, params.host)

    except SSHConnectionError as e:
        return f"Error: Cannot connect to Attocore system at {params.host}. {str(e)}"
    except SSHCommandError as e:
        return f"Error: Failed to retrieve active connections. {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in get_active_connections: {e}")
        return f"Error: Unexpected error occurred: {str(e)}"


# ============================================================================
# Tool 4: Get Network Configuration
# ============================================================================

@mcp.tool(
    name="attocore_get_network_config",
    annotations={
        "title": "Get Attocore Network Configuration",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def attocore_get_network_config(params: AttocoreHostInput) -> str:
    """
    Read network configuration including PLMNID, DNNs, and bandwidth settings.

    This tool retrieves the core network configuration from the Attocore system,
    including the network identity (PLMNID, network name, tracking area code),
    configured Data Network Names (DNNs), and bandwidth allocation settings.
    This is useful for understanding network configuration and troubleshooting
    network-level issues.

    Args:
        params (AttocoreHostInput): Input parameters containing:
            - host (str): Attocore system IP address (default: 10.48.98.5)
            - response_format (ResponseFormat): Output format - 'markdown' or 'json'

    Returns:
        str: Network configuration report. Format depends on response_format:

        Markdown format:
        - Human-readable configuration grouped by category
        - Network identity section (PLMNID, MCC, MNC, TAC, network name)
        - DNN configurations with bandwidth settings

        JSON format:
        ```json
        {
          "host": "10.48.98.5",
          "timestamp": "2024-01-15 10:30:00 UTC",
          "network_identity": {
            "plmnid": "999773",
            "mcc": "999",
            "mnc": "773",
            "network_name": "Waveriders Mobile",
            "tac": "1"
          },
          "dnns": {
            "total": 1,
            "list": [
              {
                "name": "video",
                "downlink_kbps": "1000000 Kbps",
                "uplink_kbps": "1000000 Kbps"
              }
            ]
          }
        }
        ```

    Examples:
        - Use when: "What is the PLMNID for the Waveriders network?"
        - Use when: "Show me the DNN configuration"
        - Use when: "What bandwidth is allocated for the video DNN?"
        - Don't use when: You need subscriber-specific configuration (use attocore_list_subscribers instead)

    Error Handling:
        - Returns clear error message if SSH connection fails
        - Handles missing or incomplete configuration data
        - Provides meaningful defaults for optional fields
    """
    try:
        async with AttocoreSSHClient(host=params.host) as client:
            # Get network identity
            plmn_cmd = CLI_GET_ATTR.format(attr="plmn", pkg="AMF_CONFIG_PKG")
            plmnid = (await client.execute_command(plmn_cmd)).strip().strip('"')

            tac_cmd = CLI_GET_ATTR_SIMPLE.format(attr="tacs")
            tac = (await client.execute_command(tac_cmd)).strip().strip('"')

            name_cmd = CLI_GET_ATTR_SIMPLE.format(attr="amf_network_name_short")
            network_name = (await client.execute_command(name_cmd)).strip().strip('"')

            # Get DNN configurations from shared data
            sm_data_cmd = CLI_LIST_SHARED_DATA.format(type="SM")
            sm_data_ids = (await client.execute_command(sm_data_cmd)).strip().split('\n')

            dnns = []
            for sm_id in sm_data_ids:
                sm_id = sm_id.strip()
                if not sm_id:
                    continue

                try:
                    # Get detailed shared data configuration
                    get_data_cmd = CLI_GET_SHARED_DATA.format(id=sm_id)
                    shared_data_json_str = await client.execute_command(get_data_cmd)
                    shared_data_json = parse_json_output(shared_data_json_str)

                    # Extract DNN names from this shared data
                    dnn_names = extract_dnn_names_from_shared_data(shared_data_json)

                    # Extract configuration for each DNN
                    for dnn_name in dnn_names:
                        dnn_config = extract_dnn_config(shared_data_json, dnn_name)
                        if dnn_config:
                            dnns.append(dnn_config)

                except Exception as e:
                    logger.warning(f"Could not parse shared data {sm_id}: {e}")
                    continue

            # Format response
            if params.response_format == ResponseFormat.MARKDOWN:
                return format_network_config_markdown(
                    plmnid,
                    tac,
                    network_name,
                    dnns,
                    params.host
                )
            else:
                return format_network_config_json(
                    plmnid,
                    tac,
                    network_name,
                    dnns,
                    params.host
                )

    except SSHConnectionError as e:
        return f"Error: Cannot connect to Attocore system at {params.host}. {str(e)}"
    except SSHCommandError as e:
        return f"Error: Failed to retrieve network configuration. {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in get_network_config: {e}")
        return f"Error: Unexpected error occurred: {str(e)}"


# ============================================================================
# Tool 5: Add Subscriber
# ============================================================================

@mcp.tool(
    name="attocore_add_subscriber",
    annotations={
        "title": "Add Attocore Subscriber",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def attocore_add_subscriber(params: AddSubscriberInput) -> str:
    """
    Provision a new device (subscriber) on the Attocore mobile core network.

    This tool provisions a new subscriber on the Attocore system by automatically
    generating the IMSI, calculating the static IP address, building the required
    JSON configuration, and executing the provisioning command. It follows Waveriders
    network standards for IMSI format, authentication keys, and IP addressing.

    Args:
        params (AddSubscriberInput): Input parameters containing:
            - device_number (int): Device number 1-999 (e.g., 18 for WR-VIDEO-18)
            - name_prefix (str): Device name prefix (default: "WR-VIDEO")
                Options: "WR-VIDEO" (standard), "WR-iVIDEO" (iPhone), "WR-VIDEO-e" (eSIM)
            - dnn (str): Data Network Name (default: "video")
            - ip_mode (str): IP addressing mode (default: "old")
                "old" = 10.48.100.x where x = device_number + 10 (current NHL)
                "new" = 10.48.98.x where x = device_number (production standard)
            - host (str): Attocore system IP address (default: 10.48.98.5)

    Returns:
        str: JSON formatted result containing:
        ```json
        {
          "success": true,
          "timestamp": "2024-01-15 10:30:00 UTC",
          "subscriber": {
            "imsi": "999773308170018",
            "name": "WR-VIDEO-18",
            "ip": "10.48.100.28",
            "dnn": "video"
          }
        }
        ```

        On error:
        ```json
        {
          "success": false,
          "timestamp": "2024-01-15 10:30:00 UTC",
          "subscriber": {...},
          "error": "Error message describing what went wrong"
        }
        ```

    Examples:
        - Use when: "Provision WR-VIDEO-18 on the NHL system"
        - Use when: "Add a new iPhone device as WR-iVIDEO-20"
        - Use when: "Create subscriber for device number 25 using new IP mode"
        - Don't use when: The device already exists (check with attocore_list_subscribers first)
        - Don't use when: You want to modify an existing subscriber (not supported yet)

    Error Handling:
        - Returns error if device number is already in use
        - Returns error if SSH connection fails
        - Returns error if IMSI already exists in system
        - All parameters are validated before execution

    Important Notes:
        - IMSI format: 999773308170XXX (XXX = zero-padded device_number)
        - Uses standard Waveriders test authentication keys (K and OPc)
        - Default bandwidth: 1 Gbps downlink/uplink
        - Safe to test with device numbers 18 and above on NHL system
    """
    try:
        # Use provided IMSI and build subscriber name
        imsi = params.imsi
        subscriber_name = f"{params.name_prefix}-{params.device_number:02d}"

        # Calculate static IP based on mode
        if params.ip_mode == "new":
            static_ip = f"{IP_MODE_NEW_SUBNET}.{params.device_number}"
        else:  # old mode
            static_ip = f"{IP_MODE_OLD_SUBNET}.{params.device_number + IP_MODE_OLD_OFFSET}"

        # Build shared data IDs
        shared_am_id = SHARED_AM_ID_TEMPLATE.format(plmnid=PLMNID, dnn=params.dnn)
        shared_smf_id = SHARED_SMF_ID_TEMPLATE.format(plmnid=PLMNID, dnn=params.dnn)

        # Build JSON payload for createue
        subscriber_data = {
            "authenticationData": {
                "authenticationSubscription": {
                    "algorithmId": "atto-1",
                    "authenticationManagementField": "8000",
                    "authenticationMethod": "5G_AKA",
                    "encOpcKey": AUTH_OPC_KEY,
                    "encPermanentKey": AUTH_K_KEY,
                    "protectionParameterId": "atto-null",
                    "sequenceNumber": {
                        "lastIndexes": {},
                        "sqn": "000000000000",
                        "sqnScheme": "NON_TIME_BASED"
                    }
                }
            },
            "identityData": {
                "supiList": [f"imsi-{imsi}"]
            },
            "operatorSpecificData": {
                "NetworkNameLong": {
                    "dataType": "STRING",
                    "value": {"OperatorSpecificDataContainerValueStrPart": "Waveriders 5G"}
                },
                "NetworkNameShort": {
                    "dataType": "STRING",
                    "value": {"OperatorSpecificDataContainerValueStrPart": "Wave 5G"}
                },
                "ServiceEnabled": {
                    "dataType": "BOOLEAN",
                    "value": {"OperatorSpecificDataContainerValueBooleanPart": True}
                },
                "SubscriberName": {
                    "dataType": "STRING",
                    "value": {"OperatorSpecificDataContainerValueStrPart": subscriber_name}
                }
            },
            "provisionedDataByPlmn": {
                PLMNID: {
                    "amData": {
                        "sharedAmDataIds": [shared_am_id]
                    },
                    "smData": [
                        {
                            "dnnConfigurations": {
                                params.dnn: {
                                    "pduSessionTypes": {
                                        "allowedSessionTypes": ["IPV6", "IPV4V6"],
                                        "defaultSessionType": "IPV4"
                                    },
                                    "sessionAmbr": {
                                        "downlink": DEFAULT_DOWNLINK_KBPS,
                                        "uplink": DEFAULT_UPLINK_KBPS
                                    },
                                    "sscModes": {
                                        "allowedSscModes": ["SSC_MODE_1"],
                                        "defaultSscMode": "SSC_MODE_1"
                                    },
                                    "staticIpAddress": [
                                        {"ipv4Addr": static_ip}
                                    ]
                                }
                            },
                            "singleNssai": {
                                "sd": "000001",
                                "sst": 1
                            }
                        }
                    ],
                    "smfSelectionData": {
                        "sharedSnssaiInfosId": shared_smf_id
                    }
                }
            }
        }

        # Convert to compact JSON string (use separators to minimize whitespace)
        json_data = json.dumps(subscriber_data, separators=(',', ':'))

        # Execute createue command
        async with AttocoreSSHClient(host=params.host) as client:
            create_cmd = CLI_CREATE_UE.format(imsi=imsi, data=json_data)
            result = await client.execute_command(create_cmd)

            # FIX: Attocore CLI returns exit code 0 even on errors,
            # so we must validate the output content
            result_stripped = result.strip()
            if "Exception" in result or "Error" in result or "error" in result:
                raise SSHCommandError(f"Provisioning failed: {result}")

            if result_stripped != "OK":
                raise SSHCommandError(f"Unexpected response (expected 'OK'): {result}")

            # FIX: Verify subscriber was actually created (defense against false positives)
            verify_cmd = f"{CLI_LIST_UES} | grep '{imsi}'"
            try:
                verify_result = await client.execute_command(verify_cmd)
                if not verify_result or imsi not in verify_result:
                    raise SSHCommandError(
                        f"Subscriber {imsi} not found in system after provisioning. "
                        f"Command reported success but subscriber is missing."
                    )
            except SSHCommandError as e:
                # If grep fails (exit code 1), subscriber wasn't found
                if "not found" not in str(e).lower():
                    # Re-raise if it's a different error
                    raise
                raise SSHCommandError(
                    f"Subscriber {imsi} not found in system after provisioning. "
                    f"Command reported success but subscriber is missing."
                )

        # Return success result
        return format_add_subscriber_result(
            success=True,
            imsi=imsi,
            name=subscriber_name,
            ip=static_ip,
            dnn=params.dnn
        )

    except SSHConnectionError as e:
        error_msg = f"Cannot connect to Attocore system at {params.host}. {str(e)}"
        return format_add_subscriber_result(
            success=False,
            imsi=imsi if 'imsi' in locals() else "unknown",
            name=subscriber_name if 'subscriber_name' in locals() else "unknown",
            ip=static_ip if 'static_ip' in locals() else "unknown",
            dnn=params.dnn,
            error_message=error_msg
        )
    except SSHCommandError as e:
        error_msg = f"Failed to provision subscriber. {str(e)}"
        # Check if it's a duplicate IMSI error
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            error_msg = f"Subscriber with IMSI {imsi} already exists. Choose a different device number."
        return format_add_subscriber_result(
            success=False,
            imsi=imsi,
            name=subscriber_name,
            ip=static_ip,
            dnn=params.dnn,
            error_message=error_msg
        )
    except Exception as e:
        logger.error(f"Unexpected error in add_subscriber: {e}")
        error_msg = f"Unexpected error occurred: {str(e)}"
        return format_add_subscriber_result(
            success=False,
            imsi=imsi if 'imsi' in locals() else "unknown",
            name=subscriber_name if 'subscriber_name' in locals() else "unknown",
            ip=static_ip if 'static_ip' in locals() else "unknown",
            dnn=params.dnn,
            error_message=error_msg
        )


# ============================================================================
# Tool 6: Get Subscriber
# ============================================================================

@mcp.tool(
    name="attocore_get_subscriber",
    annotations={
        "title": "Get Subscriber Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def attocore_get_subscriber(params: GetSubscriberInput) -> str:
    """
    Get detailed information for a single subscriber by IMSI.

    Returns the complete subscriber configuration including authentication data,
    DNN configuration, static IP address, and operator-specific data.

    Args:
        params (GetSubscriberInput): Input parameters containing:
            - imsi (str): 15-digit IMSI of subscriber to retrieve
            - host (str): Attocore system IP address
            - response_format (ResponseFormat): Output format - 'markdown' or 'json'

    Returns:
        str: Subscriber details in requested format
    """
    try:
        async with AttocoreSSHClient(host=params.host) as client:
            get_cmd = CLI_GET_UE.format(imsi=params.imsi)
            result = await client.execute_command(get_cmd)

            if not result or result.strip() == "":
                return json.dumps({
                    "success": False,
                    "error": f"Subscriber {params.imsi} not found"
                })

            if "Exception" in result or "Error" in result:
                return json.dumps({
                    "success": False,
                    "error": result.strip()
                })

            # Parse the JSON response
            subscriber_data = json.loads(result.strip())

            if params.response_format == ResponseFormat.JSON:
                return json.dumps({
                    "success": True,
                    "imsi": params.imsi,
                    "data": subscriber_data
                }, indent=2)
            else:
                # Format as markdown
                name = "Unknown"
                ip = "Unknown"
                dnn = "Unknown"

                # Extract name from operatorSpecificData
                if "operatorSpecificData" in subscriber_data:
                    osd = subscriber_data["operatorSpecificData"]
                    if "SubscriberName" in osd:
                        name = osd["SubscriberName"]["value"].get(
                            "OperatorSpecificDataContainerValueStrPart", "Unknown"
                        )

                # Extract IP and DNN from provisionedDataByPlmn
                if "provisionedDataByPlmn" in subscriber_data:
                    for plmn_data in subscriber_data["provisionedDataByPlmn"].values():
                        if "smData" in plmn_data and plmn_data["smData"]:
                            sm_data = plmn_data["smData"][0]
                            if "dnnConfigurations" in sm_data:
                                for dnn_name, dnn_config in sm_data["dnnConfigurations"].items():
                                    dnn = dnn_name
                                    if "staticIpAddress" in dnn_config and dnn_config["staticIpAddress"]:
                                        ip = dnn_config["staticIpAddress"][0].get("ipv4Addr", "Unknown")
                                    break

                return f"""## Subscriber Details

| Field | Value |
|-------|-------|
| IMSI | {params.imsi} |
| Name | {name} |
| DNN | {dnn} |
| Static IP | {ip} |

**Status:** Found
"""

    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to parse subscriber data: {str(e)}"
        })
    except SSHConnectionError as e:
        return json.dumps({
            "success": False,
            "error": f"Cannot connect to Attocore system at {params.host}: {str(e)}"
        })
    except SSHCommandError as e:
        return json.dumps({
            "success": False,
            "error": f"Command failed: {str(e)}"
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
    name="attocore_delete_subscriber",
    annotations={
        "title": "Delete Subscriber",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def attocore_delete_subscriber(params: DeleteSubscriberInput) -> str:
    """
    Delete a subscriber from the Attocore system.

    WARNING: This permanently removes the subscriber configuration.
    The device will no longer be able to connect to the network.

    Args:
        params (DeleteSubscriberInput): Input parameters containing:
            - imsi (str): 15-digit IMSI of subscriber to delete
            - host (str): Attocore system IP address

    Returns:
        str: JSON result with success status
    """
    try:
        async with AttocoreSSHClient(host=params.host) as client:
            # First verify subscriber exists
            get_cmd = CLI_GET_UE.format(imsi=params.imsi)
            check_result = await client.execute_command(get_cmd)

            if not check_result or check_result.strip() == "" or "Exception" in check_result:
                return json.dumps({
                    "success": False,
                    "error": f"Subscriber {params.imsi} not found"
                })

            # Delete the subscriber
            delete_cmd = CLI_DELETE_UE.format(imsi=params.imsi)
            result = await client.execute_command(delete_cmd)

            result_stripped = result.strip()
            if result_stripped == "OK":
                return json.dumps({
                    "success": True,
                    "message": f"Subscriber {params.imsi} deleted successfully"
                })
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Delete failed: {result_stripped}"
                })

    except SSHConnectionError as e:
        return json.dumps({
            "success": False,
            "error": f"Cannot connect to Attocore system at {params.host}: {str(e)}"
        })
    except SSHCommandError as e:
        return json.dumps({
            "success": False,
            "error": f"Command failed: {str(e)}"
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
    name="attocore_update_subscriber",
    annotations={
        "title": "Update Subscriber",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def attocore_update_subscriber(params: UpdateSubscriberInput) -> str:
    """
    Update subscriber details (IP address, DNN, or name).

    This tool fetches the current subscriber configuration, applies the requested
    changes, and uses createue (which performs an upsert) to update the subscriber.

    Note: IMSI and authentication keys (K/OPc) cannot be changed.

    Args:
        params (UpdateSubscriberInput): Input parameters containing:
            - imsi (str): 15-digit IMSI of subscriber to update
            - ip (str, optional): New static IP address
            - dnn (str, optional): New Data Network Name
            - name (str, optional): New subscriber name
            - host (str): Attocore system IP address

    Returns:
        str: JSON result with success status and updated values
    """
    # Validate at least one field to update
    if not params.ip and not params.dnn and not params.name:
        return json.dumps({
            "success": False,
            "error": "At least one field (ip, dnn, or name) must be provided for update"
        })

    try:
        async with AttocoreSSHClient(host=params.host) as client:
            # 1. Get current subscriber data
            get_cmd = CLI_GET_UE.format(imsi=params.imsi)
            result = await client.execute_command(get_cmd)

            if not result or result.strip() == "":
                return json.dumps({
                    "success": False,
                    "error": f"Subscriber {params.imsi} not found"
                })

            if "Exception" in result or "Error" in result:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to get subscriber: {result.strip()}"
                })

            # Check for "not found" message
            if "No UE subscription found" in result:
                return json.dumps({
                    "success": False,
                    "error": f"Subscriber {params.imsi} not found"
                })

            # Parse current data
            try:
                subscriber_data = json.loads(result.strip())
            except json.JSONDecodeError:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to parse subscriber data: {result.strip()[:100]}"
                })
            changes_made = []

            # 2. Apply updates
            # Update name in operatorSpecificData
            if params.name:
                if "operatorSpecificData" not in subscriber_data:
                    subscriber_data["operatorSpecificData"] = {}
                subscriber_data["operatorSpecificData"]["SubscriberName"] = {
                    "dataType": "STRING",
                    "value": {"OperatorSpecificDataContainerValueStrPart": params.name}
                }
                changes_made.append(f"name → {params.name}")

            # Update IP and/or DNN in provisionedDataByPlmn
            if params.ip or params.dnn:
                if "provisionedDataByPlmn" in subscriber_data:
                    for plmn_id, plmn_data in subscriber_data["provisionedDataByPlmn"].items():
                        if "smData" in plmn_data and plmn_data["smData"]:
                            sm_data = plmn_data["smData"][0]
                            if "dnnConfigurations" in sm_data:
                                current_dnns = list(sm_data["dnnConfigurations"].keys())
                                if current_dnns:
                                    old_dnn = current_dnns[0]
                                    dnn_config = sm_data["dnnConfigurations"][old_dnn]

                                    # Update IP
                                    if params.ip:
                                        if "staticIpAddress" not in dnn_config:
                                            dnn_config["staticIpAddress"] = [{}]
                                        dnn_config["staticIpAddress"][0]["ipv4Addr"] = params.ip
                                        changes_made.append(f"ip → {params.ip}")

                                    # Update DNN (rename the key)
                                    if params.dnn and params.dnn != old_dnn:
                                        sm_data["dnnConfigurations"][params.dnn] = dnn_config
                                        del sm_data["dnnConfigurations"][old_dnn]

                                        # Also update shared data IDs
                                        if "amData" in plmn_data:
                                            plmn_data["amData"]["sharedAmDataIds"] = [
                                                SHARED_AM_ID_TEMPLATE.format(plmnid=plmn_id, dnn=params.dnn)
                                            ]
                                        if "smfSelectionData" in plmn_data:
                                            plmn_data["smfSelectionData"]["sharedSnssaiInfosId"] = \
                                                SHARED_SMF_ID_TEMPLATE.format(plmnid=plmn_id, dnn=params.dnn)

                                        changes_made.append(f"dnn → {params.dnn}")

            # 3. Write updated data back using createue (upsert)
            # Write to temp file and use xargs to handle shell escaping
            json_data = json.dumps(subscriber_data, separators=(',', ':'))

            # Use a heredoc approach to avoid shell escaping issues
            update_cmd = f"echo '{json_data}' | xargs -0 -I {{}} atto-5gc-cli createue --imsi {params.imsi} --data {{}}"
            update_result = await client.execute_command(update_cmd)

            if update_result.strip() == "OK":
                return json.dumps({
                    "success": True,
                    "imsi": params.imsi,
                    "changes": changes_made,
                    "message": f"Subscriber updated: {', '.join(changes_made)}"
                })
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Update failed: {update_result.strip()}"
                })

    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to parse subscriber data: {str(e)}"
        })
    except SSHConnectionError as e:
        return json.dumps({
            "success": False,
            "error": f"Cannot connect to Attocore system at {params.host}: {str(e)}"
        })
    except SSHCommandError as e:
        return json.dumps({
            "success": False,
            "error": f"Command failed: {str(e)}"
        })
    except Exception as e:
        logger.error(f"Unexpected error in update_subscriber: {e}")
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        })


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
