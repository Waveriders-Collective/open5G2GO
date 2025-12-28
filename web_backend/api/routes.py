"""
API routes for the Open5G2GO Web Backend.

Exposes REST endpoints for Open5GS subscriber management.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from .models import (
    AddSubscriberRequest,
    UpdateSubscriberRequest,
    HealthCheckResponse,
)
from .dependencies import get_service
from ..services.open5gs_service import Open5GSService
from ..config import settings

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()


# ============================================================================
# Health Check Endpoint
# ============================================================================

@router.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["Health"],
    summary="Health check endpoint"
)
async def health_check() -> HealthCheckResponse:
    """
    Check if the API is running and healthy.

    Returns:
        HealthCheckResponse: API health status
    """
    return HealthCheckResponse(
        status="healthy",
        version=settings.app_version,
        service=settings.app_name
    )


# ============================================================================
# Read Operations
# ============================================================================

@router.get(
    "/subscribers",
    tags=["Devices"],
    summary="List all provisioned devices",
    response_description="List of devices with IMSI, name, IP, APN"
)
async def list_subscribers(
    service: Open5GSService = Depends(get_service)
) -> Dict[str, Any]:
    """
    List all provisioned devices on the Open5GS system.

    Returns device details including IMSI, device name, APN,
    and assigned static IP address.

    **Example Response:**
    ```json
    {
      "timestamp": "2024-01-15 10:30:00 UTC",
      "total": 10,
      "subscribers": [
        {
          "imsi": "315010000000001",
          "name": "CAM-01",
          "apn": "internet",
          "ip": "10.48.99.2"
        }
      ]
    }
    ```
    """
    logger.info("Listing subscribers")
    result = await service.list_subscribers()

    if "error" in result:
        logger.error(f"Error listing subscribers: {result['error']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result
        )

    return result


@router.get(
    "/status",
    tags=["System"],
    summary="Get system health and status",
    response_description="System health dashboard with subscriber counts"
)
async def get_system_status(
    service: Open5GSService = Depends(get_service)
) -> Dict[str, Any]:
    """
    Get Open5GS system health and status dashboard.

    Returns subscriber counts and overall health assessment.

    **Example Response:**
    ```json
    {
      "timestamp": "2024-01-15 10:30:00 UTC",
      "subscribers": {
        "provisioned": 10,
        "registered": 1,
        "connected": 1
      },
      "enodebs": {
        "total": 1,
        "list": []
      },
      "health": {
        "core_operational": true,
        "database_connected": true,
        "has_active_connections": true
      }
    }
    ```
    """
    logger.info("Getting system status")
    result = await service.get_system_status()

    if "error" in result:
        logger.error(f"Error getting system status: {result['error']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result
        )

    # Add system name to response
    result["system_name"] = settings.system_name

    return result


@router.get(
    "/connections",
    tags=["Connections"],
    summary="Get active device connections",
    response_description="List of currently connected devices"
)
async def get_active_connections(
    service: Open5GSService = Depends(get_service)
) -> Dict[str, Any]:
    """
    Get list of currently active device connections.

    Note: Real-time connection tracking requires log parsing
    which is planned for Phase 2. Returns placeholder data for MVP.

    **Example Response:**
    ```json
    {
      "timestamp": "2024-01-15 10:30:00 UTC",
      "total_active": 0,
      "connections": [],
      "note": "Real-time connection tracking requires log parsing (Phase 2)"
    }
    ```
    """
    logger.info("Getting active connections")
    result = await service.get_active_connections()

    if "error" in result:
        logger.error(f"Error getting active connections: {result['error']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result
        )

    return result


@router.get(
    "/config",
    tags=["Network"],
    summary="Get network configuration",
    response_description="Network identity and APN configurations"
)
async def get_network_config(
    service: Open5GSService = Depends(get_service)
) -> Dict[str, Any]:
    """
    Get network configuration including PLMNID, APNs, and IP pool settings.

    Returns the core network configuration including network identity
    (PLMNID, network name, TAC) and APN configurations.

    **Example Response:**
    ```json
    {
      "timestamp": "2024-01-15 10:30:00 UTC",
      "network_identity": {
        "plmnid": "315010",
        "mcc": "315",
        "mnc": "010",
        "network_name": "Open5G2GO",
        "tac": "1"
      },
      "apns": {
        "total": 1,
        "list": [
          {
            "name": "internet",
            "downlink_mbps": 100,
            "uplink_mbps": 50
          }
        ]
      },
      "ip_pool": {
        "start": "10.48.99.2",
        "end": "10.48.99.254"
      }
    }
    ```
    """
    logger.info("Getting network config")
    result = await service.get_network_config()

    if "error" in result:
        logger.error(f"Error getting network config: {result['error']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result
        )

    return result


# ============================================================================
# Write Operations
# ============================================================================

@router.post(
    "/subscribers",
    tags=["Devices"],
    summary="Add a new device",
    response_description="Provisioning result with IMSI, IP, and status",
    status_code=status.HTTP_201_CREATED
)
async def add_subscriber(
    request: AddSubscriberRequest,
    service: Open5GSService = Depends(get_service)
) -> Dict[str, Any]:
    """
    Provision a new device on the Open5GS system.

    Creates a new subscriber with automatically generated IMSI (from device_number),
    calculated static IP address, and standard authentication keys.

    **Request Body:**
    ```json
    {
      "device_number": 1,
      "name": "CAM-01",
      "apn": "internet",
      "ip": "10.48.99.10"
    }
    ```

    **Success Response:**
    ```json
    {
      "success": true,
      "timestamp": "2024-01-15 10:30:00 UTC",
      "subscriber": {
        "imsi": "315010000000001",
        "name": "CAM-01",
        "ip": "10.48.99.10",
        "apn": "internet"
      }
    }
    ```
    """
    logger.info(
        f"Adding subscriber: device_number={request.device_number}, "
        f"name={request.name}, apn={request.apn}"
    )

    result = await service.add_subscriber(
        device_number=request.device_number,
        name=request.name,
        apn=request.apn,
        ip=request.ip,
        imsi=request.imsi
    )

    # Check if provisioning failed
    if not result.get("success", False):
        logger.error(f"Failed to add subscriber: {result.get('error')}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result
        )

    return result


@router.get(
    "/subscribers/{imsi}",
    tags=["Devices"],
    summary="Get device details",
    response_description="Full device configuration data"
)
async def get_subscriber(
    imsi: str,
    service: Open5GSService = Depends(get_service)
) -> Dict[str, Any]:
    """
    Get detailed information for a single device by IMSI.

    Returns the complete subscriber configuration including authentication data,
    APN configuration, and static IP address.

    **Path Parameters:**
    - imsi: 15-digit IMSI of device to retrieve

    **Example Response:**
    ```json
    {
      "success": true,
      "imsi": "315010000000001",
      "data": {
        "imsi": "315010000000001",
        "security": {...},
        "slice": [...]
      }
    }
    ```
    """
    # Validate IMSI format
    if not imsi.isdigit() or len(imsi) != 15:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "IMSI must be exactly 15 digits"}
        )

    logger.info(f"Getting subscriber {imsi}")
    result = await service.get_subscriber(imsi)

    if not result.get("success", False):
        error_msg = result.get("error", "Subscriber not found")
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result
        )

    return result


@router.put(
    "/subscribers/{imsi}",
    tags=["Devices"],
    summary="Update device details",
    response_description="Update result with changes made"
)
async def update_subscriber(
    imsi: str,
    request: UpdateSubscriberRequest,
    service: Open5GSService = Depends(get_service)
) -> Dict[str, Any]:
    """
    Update device details (IP address, APN, or name).

    At least one field (ip, apn, or name) must be provided.
    IMSI and authentication keys cannot be changed.

    **Path Parameters:**
    - imsi: 15-digit IMSI of device to update

    **Request Body:**
    ```json
    {
      "ip": "10.48.99.50",
      "apn": "internet",
      "name": "CAM-50"
    }
    ```

    **Example Response:**
    ```json
    {
      "success": true,
      "imsi": "315010000000001",
      "changes": ["ip → 10.48.99.50"],
      "message": "Subscriber updated: ip → 10.48.99.50"
    }
    ```
    """
    # Validate IMSI format
    if not imsi.isdigit() or len(imsi) != 15:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "IMSI must be exactly 15 digits"}
        )

    # Validate at least one field provided
    if not request.ip and not request.apn and not request.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "At least one field (ip, apn, or name) must be provided"}
        )

    logger.info(f"Updating subscriber {imsi}")
    result = await service.update_subscriber(
        imsi=imsi,
        ip=request.ip,
        apn=request.apn,
        name=request.name
    )

    if not result.get("success", False):
        error_msg = result.get("error", "Update failed")
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result
        )

    return result


@router.delete(
    "/subscribers/{imsi}",
    tags=["Devices"],
    summary="Delete a device",
    response_description="Deletion result"
)
async def delete_subscriber(
    imsi: str,
    service: Open5GSService = Depends(get_service)
) -> Dict[str, Any]:
    """
    Delete a device from the Open5GS system.

    WARNING: This permanently removes the subscriber configuration.
    The device will no longer be able to connect to the network.

    **Path Parameters:**
    - imsi: 15-digit IMSI of device to delete

    **Example Response:**
    ```json
    {
      "success": true,
      "message": "Subscriber 315010000000001 deleted successfully"
    }
    ```
    """
    # Validate IMSI format
    if not imsi.isdigit() or len(imsi) != 15:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "IMSI must be exactly 15 digits"}
        )

    logger.info(f"Deleting subscriber {imsi}")
    result = await service.delete_subscriber(imsi)

    if not result.get("success", False):
        error_msg = result.get("error", "Delete failed")
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result
        )

    return result


# ============================================================================
# eNodeB Status Endpoints
# ============================================================================

@router.get(
    "/enodeb/status",
    tags=["eNodeB"],
    summary="Get eNodeB connection and SAS status",
    response_description="Combined S1AP and SAS status for all configured eNodeBs"
)
async def get_enodeb_status(
    service: Open5GSService = Depends(get_service)
) -> Dict[str, Any]:
    """
    Get combined eNodeB status including S1AP connections and SAS grants.

    Returns status for all configured eNodeBs from enodebs.yaml, including:
    - S1AP connection status (from MME log parsing)
    - SAS registration and grant status (if Google SAS API is configured)

    **Example Response:**
    ```json
    {
      "timestamp": "2024-01-15 10:30:00 UTC",
      "s1ap": {
        "available": true,
        "connected_count": 1,
        "enodebs": [{
          "serial_number": "120200046421CKY0606",
          "config_name": "Nova-430i-Test",
          "location": "Test Lab",
          "connected": true,
          "ip_address": "10.48.0.159"
        }]
      },
      "sas": {
        "available": false,
        "registered_count": 0,
        "authorized_count": 0,
        "enodebs": []
      }
    }
    ```
    """
    logger.info("Getting eNodeB status")
    result = await service.get_enodeb_status()

    if "error" in result and result.get("s1ap", {}).get("available") is False:
        logger.error(f"Error getting eNodeB status: {result.get('error')}")
        # Return the result anyway for partial data display

    return result


@router.post(
    "/enodeb/refresh",
    tags=["eNodeB"],
    summary="Refresh SAS status",
    response_description="Refresh result"
)
async def refresh_sas_status(
    service: Open5GSService = Depends(get_service)
) -> Dict[str, Any]:
    """
    Trigger a manual refresh of SAS status for all eNodeBs.

    This polls the Google SAS Portal API for the latest grant status.
    Note: SAS API must be configured with valid credentials.

    **Example Response:**
    ```json
    {
      "success": true,
      "message": "SAS status refreshed",
      "timestamp": "2024-01-15 10:30:00 UTC"
    }
    ```
    """
    logger.info("Refreshing SAS status")

    # Get fresh status (this triggers a new poll)
    result = await service.get_enodeb_status()

    sas_available = result.get("sas", {}).get("available", False)

    return {
        "success": True,
        "message": "SAS status refreshed" if sas_available else "SAS not configured",
        "timestamp": result.get("timestamp", "")
    }
