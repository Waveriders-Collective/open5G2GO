"""Pydantic models for Waveriders unified configuration schema"""

import ipaddress
from typing import List, Literal
from pydantic import BaseModel, Field, field_validator


class NetworkIdentity(BaseModel):
    """Network identity configuration (PLMN, TAC, name)"""

    country_code: str = Field(
        ...,
        description="Mobile Country Code (MCC) - 3 digits",
        examples=["315"]
    )
    network_code: str = Field(
        ...,
        description="Mobile Network Code (MNC) - 2-3 digits",
        examples=["010"]
    )
    area_code: int = Field(
        ...,
        description="Tracking Area Code (TAC)",
        ge=1,
        le=65535
    )
    network_name: str = Field(
        ...,
        description="Human-readable network name",
        min_length=1,
        max_length=64
    )

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        """Validate MCC is 3 digits"""
        if not v.isdigit() or len(v) != 3:
            raise ValueError("Country code must be 3 digits")
        return v

    @field_validator("network_code")
    @classmethod
    def validate_network_code(cls, v: str) -> str:
        """Validate MNC is 2-3 digits"""
        if not v.isdigit() or len(v) not in [2, 3]:
            raise ValueError("Network code must be 2-3 digits")
        return v


class IPAddressing(BaseModel):
    """IP addressing configuration"""

    architecture: Literal["direct_routing"] = Field(
        default="direct_routing",
        description="Waveriders standard: devices directly routable on LAN"
    )
    core_address: str = Field(
        ...,
        description="IP address of core control plane (MME/AMF)",
        examples=["10.48.0.5"]
    )
    device_pool: str = Field(
        ...,
        description="CIDR subnet for device IP assignments",
        examples=["10.48.99.0/24"]
    )
    device_gateway: str = Field(
        ...,
        description="Gateway IP for devices (ogstun interface)",
        examples=["10.48.99.1"]
    )
    dns_servers: List[str] = Field(
        default=["8.8.8.8", "8.8.4.4"],
        description="DNS servers for device internet access"
    )

    @field_validator("core_address", "device_gateway")
    @classmethod
    def validate_ip_address(cls, v: str) -> str:
        """Validate IP address format"""
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"Invalid IP address: {v}")
        return v

    @field_validator("device_pool")
    @classmethod
    def validate_cidr(cls, v: str) -> str:
        """Validate CIDR notation"""
        if "/" not in v:
            raise ValueError(f"Invalid CIDR notation: {v} (missing /prefix)")
        try:
            ipaddress.ip_network(v, strict=False)
        except ValueError:
            raise ValueError(f"Invalid CIDR notation: {v}")
        return v

    @field_validator("dns_servers")
    @classmethod
    def validate_dns_servers(cls, v: List[str]) -> List[str]:
        """Validate DNS server IPs"""
        for dns in v:
            try:
                ipaddress.ip_address(dns)
            except ValueError:
                raise ValueError(f"Invalid DNS server IP: {dns}")
        return v
