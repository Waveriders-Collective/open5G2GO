"""
Constants and configuration for OpenSurfControl.

Defines Open5GS network standards, default values, and configuration.
Used for Open5G2GO - a homelab toolkit for private 4G cellular networks.
"""

import os

# Open5GS MongoDB
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = "open5gs"

# Network Identity (PLMN 315-010)
MCC = "315"
MNC = "010"
PLMNID = f"{MCC}{MNC}"

# IMSI Format: 315010 + 9 digits (user enters last 4 only)
# Example: User enters "0001" -> IMSI becomes "315010000000001"
IMSI_PREFIX = "31501000000"  # User appends 4 digits

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

# Default Authentication Keys
# These match the Waveriders SIM template for homelab testing
DEFAULT_K = "465B5CE8B199B49FAA5F0A2EE238A6BC"
DEFAULT_OPC = "E8ED289DEBA952E4283B54E88E6183CA"

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
