"""Pydantic models for Waveriders unified configuration schema"""

from typing import Literal
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
