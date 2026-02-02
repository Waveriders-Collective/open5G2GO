# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Waveriders Collective Inc.

"""
Constants and configuration for OpenSurfControl.

Defines Open5GS network standards, default values, and configuration.
Used for Open5G2GO - a homelab toolkit for private 4G cellular networks.
"""

import os

# Open5GS MongoDB
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = "open5gs"

# Network Identity (PLMN) - read from environment
MCC = os.getenv("MCC", "315")
MNC = os.getenv("MNC", "010")

# Handle 2-digit MNC -> 3-digit for IMSI (3GPP compliance)
# 001-01 -> 001010, 999-99 -> 999990, 315-010 -> 315010
MNC_IMSI = MNC if len(MNC) == 3 else f"{MNC}0"
PLMNID = f"{MCC}{MNC_IMSI}"

# IMSI Prefix (deprecated - will be removed in Phase 5)
# Format: PLMNID + 5 zeros, user appends last 4 digits
# Example: 315010 + 00000 + 0001 = 315010000000001
IMSI_PREFIX = f"{PLMNID}00000"

# Default APN
DEFAULT_APN = "internet"

# UE IP Pool
UE_POOL_START = "10.48.99.2"
UE_POOL_END = "10.48.99.254"
UE_GATEWAY = "10.48.99.1"
UE_DNS = ["8.8.8.8", "8.8.4.4"]

# QoS (MVP: single best-effort profile)
DEFAULT_QCI = 9
DEFAULT_ARP_PRIORITY = 8
DEFAULT_AMBR_UL = 50000000   # 50 Mbps
DEFAULT_AMBR_DL = 100000000  # 100 Mbps

# Authentication Keys (REQUIRED - no defaults)
# These are your SIM authentication keys from your SIM vendor.
DEFAULT_K = os.getenv("OPEN5GS_DEFAULT_K")
DEFAULT_OPC = os.getenv("OPEN5GS_DEFAULT_OPC")


def validate_auth_keys():
    """Validate that authentication keys are configured."""
    if not DEFAULT_K or not DEFAULT_OPC:
        raise ValueError(
            "OPEN5GS_DEFAULT_K and OPEN5GS_DEFAULT_OPC environment variables are required. "
            "These are your SIM authentication keys from your SIM vendor."
        )

# Open5GS Paths
OPEN5GS_CONFIG_PATH = os.getenv("OPEN5GS_CONFIG_PATH", "/etc/open5gs")

# Network Naming
NETWORK_NAME_SHORT = "Open5G2GO"
NETWORK_NAME_LONG = "Open5G2GO Private LTE"
TAC = 1  # Tracking Area Code

# MCP Response Limits
CHARACTER_LIMIT = 25000  # Maximum response size in characters

# Device Name Patterns
DEVICE_NAME_CAM = "CAM"      # Camera devices
DEVICE_NAME_TABLET = "TABLET"  # Tablet devices
DEVICE_NAME_PHONE = "PHONE"   # Phone devices
