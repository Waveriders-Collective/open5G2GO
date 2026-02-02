# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Waveriders Collective Inc.

"""
Pydantic models for API requests and responses.

These models define the structure of data exchanged between
the frontend and backend API.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


# ============================================================================
# Request Models
# ============================================================================

class AddSubscriberRequest(BaseModel):
    """Request body for adding a new subscriber (device)."""
    device_number: int = Field(
        ...,
        ge=1,
        le=9999,
        description="Device number (1-9999, becomes last 4 digits of IMSI)"
    )
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="Device name (e.g., 'CAM-01', 'TABLET-01')"
    )
    apn: str = Field(
        default="internet",
        description="Access Point Name"
    )
    ip: Optional[str] = Field(
        None,
        pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",
        description="Static IP address (auto-assigned if not specified)"
    )
    imsi: Optional[str] = Field(
        None,
        min_length=15,
        max_length=15,
        pattern=r"^\d{15}$",
        description="Full IMSI (overrides device_number calculation)"
    )


class UpdateSubscriberRequest(BaseModel):
    """Request body for updating a subscriber."""
    ip: Optional[str] = Field(
        None,
        pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",
        description="New static IP address (e.g., '10.48.99.10')"
    )
    apn: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="New Access Point Name"
    )
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="New device name"
    )


# ============================================================================
# Response Models
# ============================================================================

class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="API health status")
    version: str = Field(..., description="API version")
    service: str = Field(..., description="Service name")


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")


class SubscriberSummary(BaseModel):
    """Summary of a subscriber for list view."""
    imsi: str = Field(..., description="Subscriber IMSI")
    name: str = Field(..., description="Device name")
    ip: Optional[str] = Field(None, description="Assigned IP address")
    apn: str = Field(..., description="Access Point Name")


class SubscriberListResponse(BaseModel):
    """List of subscribers response."""
    timestamp: str = Field(..., description="Response timestamp")
    total: int = Field(..., description="Total number of subscribers")
    subscribers: List[SubscriberSummary] = Field(..., description="List of subscribers")


class SubscriberResponse(BaseModel):
    """Single subscriber details response."""
    success: bool = Field(..., description="Operation success status")
    imsi: Optional[str] = Field(None, description="Subscriber IMSI")
    data: Optional[dict] = Field(None, description="Full subscriber data")
    error: Optional[str] = Field(None, description="Error message if any")


class AddSubscriberResponse(BaseModel):
    """Add subscriber operation response."""
    success: bool = Field(..., description="Operation success status")
    timestamp: str = Field(..., description="Response timestamp")
    subscriber: Optional[SubscriberSummary] = Field(None, description="Created subscriber")
    error: Optional[str] = Field(None, description="Error message if any")


class UpdateSubscriberResponse(BaseModel):
    """Update subscriber operation response."""
    success: bool = Field(..., description="Operation success status")
    imsi: Optional[str] = Field(None, description="Subscriber IMSI")
    changes: Optional[List[str]] = Field(None, description="List of changes made")
    message: Optional[str] = Field(None, description="Success message")
    error: Optional[str] = Field(None, description="Error message if any")


class DeleteSubscriberResponse(BaseModel):
    """Delete subscriber operation response."""
    success: bool = Field(..., description="Operation success status")
    message: Optional[str] = Field(None, description="Success message")
    error: Optional[str] = Field(None, description="Error message if any")


class SystemStatusResponse(BaseModel):
    """System status response."""
    timestamp: str = Field(..., description="Response timestamp")
    subscribers: dict = Field(..., description="Subscriber counts")
    enodebs: dict = Field(..., description="eNodeB information")
    health: dict = Field(..., description="System health indicators")
    system_name: Optional[str] = Field(None, description="System name")


class NetworkConfigResponse(BaseModel):
    """Network configuration response."""
    timestamp: str = Field(..., description="Response timestamp")
    network_identity: dict = Field(..., description="Network identity (PLMN)")
    apns: dict = Field(..., description="APN configuration")
    ip_pool: dict = Field(..., description="UE IP pool configuration")


# ============================================================================
# Service Status Models
# ============================================================================

class ServiceStatus(BaseModel):
    """Status of a single Open5GS service."""
    name: str = Field(..., description="Service name (e.g., 'mme', 'amf')")
    display_name: str = Field(..., description="Human-readable service name")
    category: str = Field(..., description="Service category (4G EPC Core, 5G SA Core)")
    status: str = Field(..., description="Service status: running, stopped, error, or unknown")
    uptime: Optional[str] = Field(None, description="Service uptime")
    last_checked: str = Field(..., description="ISO timestamp of last status check")
    details: Optional[str] = Field(None, description="Additional details")


class ServicesResponse(BaseModel):
    """Response containing status of all Open5GS services."""
    host: str = Field(..., description="Host name")
    timestamp: str = Field(..., description="Response timestamp")
    check_method: str = Field(..., description="Method used to check services: docker or process")
    services: List[ServiceStatus] = Field(..., description="List of service statuses")
    summary: dict = Field(..., description="Summary counts of service statuses")
