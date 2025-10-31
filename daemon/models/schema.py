"""Pydantic models for Waveriders unified configuration schema"""

import ipaddress
from typing import Dict, List, Literal, Optional
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


class NetworkSlice(BaseModel):
    """5G network slice configuration"""

    service_type: int = Field(
        ...,
        description="Slice/Service Type (SST) - 1=eMBB, 2=URLLC, 3=MIoT",
        ge=1,
        le=3
    )
    slice_id: str = Field(
        ...,
        description="Slice Differentiator (SD) - 6 hex digits",
        pattern=r"^[0-9A-Fa-f]{6}$"
    )


class RadioParameters(BaseModel):
    """Radio access network configuration"""

    network_name: str = Field(
        default="internet",
        description="Network name (APN for 4G, DNN for 5G)",
        examples=["internet", "production"]
    )
    frequency_band: str = Field(
        ...,
        description="Operating frequency band",
        examples=["CBRS_Band48", "3.5GHz_CBRS", "custom"]
    )
    network_slice: Optional[NetworkSlice] = Field(
        default=None,
        description="5G network slice configuration (5G only)"
    )


class QoSPolicy(BaseModel):
    """Quality of Service policy definition"""

    name: str = Field(
        ...,
        description="Policy name",
        examples=["high_priority", "standard", "low_latency"]
    )
    description: str = Field(
        ...,
        description="Human-readable description"
    )
    priority_level: int = Field(
        ...,
        description="Priority level (1=highest, 10=lowest)",
        ge=1,
        le=10
    )
    guaranteed_bandwidth: bool = Field(
        default=False,
        description="Whether bandwidth is guaranteed"
    )
    uplink_mbps: int = Field(
        ...,
        description="Uplink bandwidth limit in Mbps",
        ge=1
    )
    downlink_mbps: int = Field(
        ...,
        description="Downlink bandwidth limit in Mbps",
        ge=1
    )


class DeviceConfig(BaseModel):
    """Individual device configuration"""

    imsi: str = Field(
        ...,
        description="International Mobile Subscriber Identity",
        pattern=r"^\d{15}$"
    )
    name: str = Field(
        ...,
        description="Human-readable device name",
        examples=["CAM-01", "TABLET-1"]
    )
    k: str = Field(
        ...,
        description="Authentication key (32 hex chars)",
        pattern=r"^[0-9A-Fa-f]{32}$"
    )
    opc: str = Field(
        ...,
        description="Operator variant key (32 hex chars)",
        pattern=r"^[0-9A-Fa-f]{32}$"
    )
    ip: Optional[str] = Field(
        default=None,
        description="Assigned IP address (populated at runtime)"
    )


class DeviceGroup(BaseModel):
    """Group of devices with common QoS policy"""

    name: str = Field(
        ...,
        description="Group name",
        examples=["Uplink_Cameras", "Crew_Devices"]
    )
    description: str = Field(
        default="",
        description="Group description"
    )
    qos_policy: str = Field(
        ...,
        description="QoS policy name to apply"
    )
    devices: List[DeviceConfig] = Field(
        default_factory=list,
        description="Devices in this group"
    )


class WaveridersConfig(BaseModel):
    """Complete Waveriders network configuration"""

    network_type: Literal["4G_LTE", "5G_Standalone"] = Field(
        ...,
        description="Network generation"
    )
    network_identity: NetworkIdentity
    ip_addressing: IPAddressing
    radio_parameters: RadioParameters
    service_quality: Literal["standard", "high_priority", "low_latency", "custom"] = Field(
        default="standard"
    )
    template_source: str = Field(
        ...,
        description="Configuration template source",
        examples=["waveriders_4g_standard", "waveriders_5g_standard", "custom"]
    )
    qos_policies: Dict[str, QoSPolicy] = Field(
        default_factory=dict,
        description="Available QoS policies"
    )
    device_groups: List[DeviceGroup] = Field(
        default_factory=list,
        description="Device groups"
    )

    @field_validator("radio_parameters")
    @classmethod
    def validate_5g_slice(cls, v: RadioParameters, info) -> RadioParameters:
        """Validate 5G networks have network slice configured"""
        if info.data.get("network_type") == "5G_Standalone":
            if v.network_slice is None:
                raise ValueError("5G networks require network_slice configuration")
        return v
