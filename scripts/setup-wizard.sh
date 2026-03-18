#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Waveriders Collective Inc.
# scripts/setup-wizard.sh - Open5G2GO Interactive Setup Wizard
# Generates .env file from env.example with user-provided values

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Ensure we can read from terminal even when piped (e.g., curl | bash)
# This allows the one-liner install to work with interactive prompts
if [ ! -t 0 ]; then
    exec < /dev/tty
fi

# Colors
RED='[0;31m'
GREEN='[0;32m'
YELLOW='[1;33m'
BLUE='[0;34m'
BOLD='[1m'
NC='[0m'

echo ""
echo -e "${BOLD}========================================"
echo "  Open5G2GO Setup Wizard"
echo -e "========================================${NC}"
echo ""

# Setup mode: "full" (default) or "network"
SETUP_MODE="full"

# =============================================================================
# Existing Installation Detection
# =============================================================================

if [ -f ".env" ]; then
    echo -e "${YELLOW}Existing Open5G2GO configuration detected!${NC}"
    echo ""
    echo "What would you like to do?"
    echo ""
    echo -e "  ${BOLD}[1]${NC} Full Setup - Complete reconfiguration (backs up existing settings)"
    echo -e "  ${BOLD}[2]${NC} Network Reconfiguration - Update host IP/network only (preserves SIM, PLMN, eNodeBs)"
    echo -e "  ${BOLD}[3]${NC} Cancel"
    echo ""

    read -p "Choice [1]: " setup_choice
    setup_choice="${setup_choice:-1}"

    case "$setup_choice" in
        1)
            SETUP_MODE="full"
            echo ""
            echo -e "Selected: ${GREEN}Full Setup${NC}"
            echo ""
            ;;
        2)
            SETUP_MODE="network"
            echo ""
            echo -e "Selected: ${GREEN}Network Reconfiguration${NC}"
            echo ""
            # Load existing values from .env to preserve them
            echo "Loading existing configuration..."
            source .env
            PRESERVED_MCC="${MCC}"
            PRESERVED_MNC="${MNC}"
            PRESERVED_K="${OPEN5GS_DEFAULT_K}"
            PRESERVED_OPC="${OPEN5GS_DEFAULT_OPC}"
            PRESERVED_DOCKER_GID="${DOCKER_GID}"
            # Load existing eNodeB config path
            PRESERVED_ENODEB_CONFIG="$PROJECT_DIR/config/enodebs.yaml"
            echo -e "  PLMN: ${GREEN}${PRESERVED_MCC}-${PRESERVED_MNC}${NC} (preserved)"
            echo -e "  SIM Keys: ${GREEN}Preserved${NC}"
            echo -e "  Docker GID: ${GREEN}${PRESERVED_DOCKER_GID}${NC} (preserved)"
            if [ -f "$PRESERVED_ENODEB_CONFIG" ]; then
                echo -e "  eNodeB Config: ${GREEN}Preserved${NC}"
            fi
            echo ""
            ;;
        3)
            echo "Setup cancelled."
            exit 0
            ;;
        *)
            SETUP_MODE="full"
            echo ""
            echo -e "Selected: ${GREEN}Full Setup${NC}"
            echo ""
            ;;
    esac
fi

# =============================================================================
# Helper Functions
# =============================================================================

# Prompt with default value
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    local value

    read -p "$prompt [$default]: " value
    value="${value:-$default}"
    eval "$var_name='$value'"
}

# Validate hex string (32 chars for K/OPc keys)
validate_hex_key() {
    local key="$1"
    local name="$2"

    if [[ ! "$key" =~ ^[0-9A-Fa-f]{32}$ ]]; then
        echo -e "${RED}Error: $name must be exactly 32 hexadecimal characters${NC}"
        return 1
    fi
    return 0
}

# Validate IP address
validate_ip() {
    local ip="$1"
    if [[ "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        return 0
    fi
    return 1
}

# Auto-detect host IP (prefer non-loopback, non-docker interface)
detect_host_ip() {
    # Try to get the default route interface IP
    local ip
    ip=$(ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K[\d.]+' 2>/dev/null) && echo "$ip" && return
    ip=$(hostname -I 2>/dev/null | awk '{print $1}') && [ -n "$ip" ] && echo "$ip" && return
    echo "10.48.0.110"
}

# =============================================================================
# Step 1: Network Mode Selection
# =============================================================================

echo -e "${BLUE}Step 1: Network Mode${NC}"
echo "─────────────────────────────────"
echo ""
echo "Select your network type:"
echo ""
echo -e "  ${BOLD}[1]${NC} 4G LTE (default) - For eNodeB base stations"
echo -e "  ${BOLD}[2]${NC} 5G SA (Standalone) - For gNodeB base stations"
echo ""

read -p "Choice [1]: " network_mode_choice
network_mode_choice="${network_mode_choice:-1}"

case "$network_mode_choice" in
    1) NETWORK_MODE="4g" ;;
    2) NETWORK_MODE="5g" ;;
    *) NETWORK_MODE="4g" ;;
esac

echo -e "Selected: ${GREEN}${NETWORK_MODE}${NC}"

# Set compose file based on mode
if [ "$NETWORK_MODE" = "5g" ]; then
    COMPOSE_FILE="docker-compose.5g.prod.yml"
    RAN_TYPE="gNodeB"
else
    COMPOSE_FILE="docker-compose.prod.yml"
    RAN_TYPE="eNodeB"
fi

# =============================================================================
# Step 2: Network Configuration
# =============================================================================

echo ""
echo -e "${BLUE}Step 2: Network Configuration${NC}"
echo "─────────────────────────────────"
echo ""

# Auto-detect host IP
DETECTED_IP=$(detect_host_ip)
echo -e "Detected host IP: ${YELLOW}$DETECTED_IP${NC}"
echo "This is the IP address your ${RAN_TYPE} will connect to."
echo ""

prompt_with_default "Docker host IP" "$DETECTED_IP" "DOCKER_HOST_IP"

if ! validate_ip "$DOCKER_HOST_IP"; then
    echo -e "${RED}Warning: '$DOCKER_HOST_IP' doesn't look like a valid IP address${NC}"
    read -p "Continue anyway? [y/N]: " confirm
    if [[ ! "${confirm}" =~ ^[Yy] ]]; then
        echo "Setup cancelled."
        exit 1
    fi
fi

echo ""
prompt_with_default "UE IP pool subnet" "10.48.99.0/24" "UE_POOL_SUBNET"
prompt_with_default "UE pool gateway" "10.48.99.1" "UE_POOL_GATEWAY"

# =============================================================================
# Step 3: PLMN Configuration
# =============================================================================

if [ "$SETUP_MODE" = "full" ]; then
    echo ""
    echo -e "${BLUE}Step 3: Network Identity (PLMN)${NC}"
    echo "─────────────────────────────────"
    echo ""
    echo "Your PLMN (Public Land Mobile Network) ID must match your SIM cards."
    echo ""
    echo -e "  ${BOLD}[1]${NC} 315-010 - US CBRS Private LTE (default)"
    echo -e "  ${BOLD}[2]${NC} 001-01  - Test Network (sysmocom/programmable SIMs)"
    echo -e "  ${BOLD}[3]${NC} 999-99  - Test Network"
    echo -e "  ${BOLD}[4]${NC} 999-01  - Test Network"
    echo ""

    read -p "Choice [1]: " plmn_choice
    plmn_choice="${plmn_choice:-1}"

    case "$plmn_choice" in
        1) MCC="315"; MNC="010" ;;
        2) MCC="001"; MNC="01" ;;
        3) MCC="999"; MNC="99" ;;
        4) MCC="999"; MNC="01" ;;
        *) MCC="315"; MNC="010" ;;
    esac

    echo -e "Selected PLMN: ${GREEN}${MCC}-${MNC}${NC}"
else
    # Network reconfiguration mode - use preserved values
    MCC="$PRESERVED_MCC"
    MNC="$PRESERVED_MNC"
    echo -e "${BLUE}Step 3: Network Identity (PLMN)${NC} - ${GREEN}Preserved${NC} (${MCC}-${MNC})"
fi

# =============================================================================
# Step 4: SIM Configuration
# =============================================================================

if [ "$SETUP_MODE" = "full" ]; then
    echo ""
    echo -e "${BLUE}Step 4: SIM Configuration${NC}"
    echo "─────────────────────────────────"
    echo ""
    echo "You need pre-programmed SIM cards with Ki and OPc authentication keys."
    echo ""
    echo "Ki (Authentication Key) and OPc (Operator Key) are cryptographic keys"
    echo "programmed into your SIM cards. Your SIM vendor provides these values."
    echo ""
    echo -e "  Need SIMs? Order at: ${YELLOW}https://waveriders.live/sims${NC}"
    echo ""
    echo "Enter your SIM authentication keys (32 hex characters each):"
    echo ""

    while true; do
        read -p "  Ki:  " OPEN5GS_DEFAULT_K
        if validate_hex_key "$OPEN5GS_DEFAULT_K" "Ki"; then
            break
        fi
    done

    while true; do
        read -p "  OPc: " OPEN5GS_DEFAULT_OPC
        if validate_hex_key "$OPEN5GS_DEFAULT_OPC" "OPc"; then
            break
        fi
    done

    echo ""
    echo -e "SIM keys configured: ${GREEN}OK${NC}"
else
    # Network reconfiguration mode - use preserved values
    OPEN5GS_DEFAULT_K="$PRESERVED_K"
    OPEN5GS_DEFAULT_OPC="$PRESERVED_OPC"
    echo -e "${BLUE}Step 4: SIM Configuration${NC} - ${GREEN}Preserved${NC}"
fi

# =============================================================================
# Step 5: RAN Configuration (eNodeB or gNodeB)
# =============================================================================

# Initialize RAN arrays
declare -a ENODEB_ENTRIES=()
declare -a GNODEB_ENTRIES=()

if [ "$SETUP_MODE" = "full" ]; then
    echo ""

    if [ "$NETWORK_MODE" = "5g" ]; then
        echo -e "${BLUE}Step 5: gNodeB Configuration${NC}"
        echo "─────────────────────────────────"
        echo ""
        echo "Configure your gNodeB for NGAP connection tracking and status display."
        echo "You can skip this step and configure later via config/gnodebs.yaml."
        echo ""

        read -p "Configure a gNodeB now? [Y/n]: " configure_gnb
        configure_gnb="${configure_gnb:-Y}"

        if [[ "${configure_gnb}" =~ ^[Yy] ]]; then
            while true; do
                echo ""
                echo "Enter gNodeB details:"

                # IP Address (required)
                while true; do
                    read -p "  IP Address: " gnb_ip
                    if validate_ip "$gnb_ip"; then
                        break
                    else
                        echo -e "${RED}  Invalid IP address format. Please try again.${NC}"
                    fi
                done

                # Name (required, with default)
                read -p "  Name (e.g., 'Lab-gNB') [gNodeB-1]: " gnb_name
                gnb_name="${gnb_name:-gNodeB-1}"

                # Location (optional)
                read -p "  Location (optional): " gnb_location
                gnb_location="${gnb_location:-}"

                # Store the entry
                GNODEB_ENTRIES+=("$gnb_ip|$gnb_name|$gnb_location")

                echo -e "  ${GREEN}gNodeB added: $gnb_name ($gnb_ip)${NC}"

                # Ask to add another
                echo ""
                read -p "Add another gNodeB? [y/N]: " add_another
                if [[ ! "${add_another}" =~ ^[Yy] ]]; then
                    break
                fi
            done

            echo ""
            echo -e "gNodeBs configured: ${GREEN}${#GNODEB_ENTRIES[@]}${NC}"
        else
            echo -e "gNodeB configuration: ${YELLOW}Skipped${NC}"
            echo "You can configure gNodeBs later by editing config/gnodebs.yaml"
        fi
    else
        echo -e "${BLUE}Step 5: eNodeB Configuration${NC}"
        echo "─────────────────────────────────"
        echo ""
        echo "Configure your Baicells eNodeB for SNMP monitoring and status display."
        echo "You can skip this step and configure later via config/enodebs.yaml."
        echo ""

        read -p "Configure an eNodeB now? [Y/n]: " configure_enb
        configure_enb="${configure_enb:-Y}"

        if [[ "${configure_enb}" =~ ^[Yy] ]]; then
            while true; do
                echo ""
                echo "Enter eNodeB details:"

                # IP Address (required)
                while true; do
                    read -p "  IP Address: " enb_ip
                    if validate_ip "$enb_ip"; then
                        break
                    else
                        echo -e "${RED}  Invalid IP address format. Please try again.${NC}"
                    fi
                done

                # Name (required, with default)
                read -p "  Name (e.g., 'Office-eNB') [eNodeB-1]: " enb_name
                enb_name="${enb_name:-eNodeB-1}"

                # Serial Number (optional)
                read -p "  Serial Number (from device label, optional): " enb_serial
                enb_serial="${enb_serial:-unknown}"

                # Location (optional)
                read -p "  Location (optional): " enb_location
                enb_location="${enb_location:-}"

                # Store the entry
                ENODEB_ENTRIES+=("$enb_ip|$enb_name|$enb_serial|$enb_location")

                echo -e "  ${GREEN}eNodeB added: $enb_name ($enb_ip)${NC}"

                # Ask to add another
                echo ""
                read -p "Add another eNodeB? [y/N]: " add_another
                if [[ ! "${add_another}" =~ ^[Yy] ]]; then
                    break
                fi
            done

            echo ""
            echo -e "eNodeBs configured: ${GREEN}${#ENODEB_ENTRIES[@]}${NC}"
        else
            echo -e "eNodeB configuration: ${YELLOW}Skipped${NC}"
            echo "You can configure eNodeBs later by editing config/enodebs.yaml"
        fi
    fi
else
    # Network reconfiguration mode - preserve existing RAN config
    SKIP_ENODEB_GENERATION=true
    SKIP_GNODEB_GENERATION=true
    echo -e "${BLUE}Step 5: RAN Configuration${NC} - ${GREEN}Preserved${NC}"
fi

# =============================================================================
# Step 6: Docker Configuration
# =============================================================================

if [ "$SETUP_MODE" = "full" ]; then
    echo ""
    echo -e "${BLUE}Step 6: Docker Configuration${NC}"
    echo "─────────────────────────────────"
    echo ""

    # Detect Docker group ID
    DOCKER_GID=$(getent group docker 2>/dev/null | cut -d: -f3 || echo "994")
    echo -e "Detected Docker group ID: ${YELLOW}$DOCKER_GID${NC}"
else
    # Network reconfiguration mode - use preserved value
    DOCKER_GID="$PRESERVED_DOCKER_GID"
    echo -e "${BLUE}Step 6: Docker Configuration${NC} - ${GREEN}Preserved${NC} (GID: ${DOCKER_GID})"
fi

# =============================================================================
# Step 7: Generate .env file
# =============================================================================

echo ""
echo -e "${BLUE}Step 7: Generating Configuration${NC}"
echo "─────────────────────────────────"
echo ""

# Backup existing .env if present (we already confirmed mode at the start)
if [ -f ".env" ]; then
    cp .env .env.backup
    echo "Backup saved to .env.backup"
fi

# Generate .env file
cat > .env << EOF
# Open5G2GO Environment Configuration
# Generated by setup-wizard.sh on $(date -Iseconds)

# =============================================================================
# Network Mode
# =============================================================================

# Network mode: 4g (LTE EPC) or 5g (SA Core)
NETWORK_MODE=${NETWORK_MODE}

# Docker Compose file for this mode
COMPOSE_FILE=${COMPOSE_FILE}

# =============================================================================
# Network Configuration
# =============================================================================

# Docker host IP address (the machine running docker-compose)
# This should be the IP your ${RAN_TYPE} will connect to
DOCKER_HOST_IP=${DOCKER_HOST_IP}

# Host IP alias for backend service
HOST_IP=${DOCKER_HOST_IP}

# UE IP Pool (assigned to connected devices)
UE_POOL_SUBNET=${UE_POOL_SUBNET}
UE_POOL_GATEWAY=${UE_POOL_GATEWAY}

# =============================================================================
# PLMN Configuration (Network Identity)
# =============================================================================

# Mobile Country Code
MCC=${MCC}

# Mobile Network Code
MNC=${MNC}

# =============================================================================
# SIM Authentication Keys
# =============================================================================

# Default authentication keys for subscriber provisioning
OPEN5GS_DEFAULT_K=${OPEN5GS_DEFAULT_K}
OPEN5GS_DEFAULT_OPC=${OPEN5GS_DEFAULT_OPC}

# =============================================================================
# RAN Configuration
# =============================================================================

# S1AP port for eNodeB connection (4G)
S1AP_PORT=36412

# NGAP port for gNodeB connection (5G)
NGAP_PORT=38412

# GTP-U port for user data
GTPU_PORT=2152

# =============================================================================
# Web UI Configuration
# =============================================================================

# Web UI port (exposed on docker host)
WEB_UI_PORT=8080

# Debug mode (set to true for development)
DEBUG=false

# =============================================================================
# Docker Configuration
# =============================================================================

# Docker group ID (for service monitoring)
DOCKER_GID=${DOCKER_GID}

# =============================================================================
# MongoDB Configuration
# =============================================================================

# MongoDB URI (used by backend and HSS/UDR)
MONGODB_URI=mongodb://mongodb:27017/open5gs
EOF

echo -e "Configuration file generated: ${GREEN}.env${NC}"

# Update PLMN in the appropriate control plane config
if [ "$NETWORK_MODE" = "5g" ]; then
    # Update AMF, NRF PLMN for 5G mode
    # Update both AMF configs (bridge and host mode)
    for AMF_CONFIG in "$PROJECT_DIR/open5gs/config/amf.yaml" "$PROJECT_DIR/open5gs/config/amf-host.yaml"; do
        if [ -f "$AMF_CONFIG" ]; then
            sed "s/mcc: \"[^\"]*\"/mcc: \"${MCC}\"/g" "$AMF_CONFIG" > "$AMF_CONFIG.tmp" && mv "$AMF_CONFIG.tmp" "$AMF_CONFIG"
            sed "s/mnc: \"[^\"]*\"/mnc: \"${MNC}\"/g" "$AMF_CONFIG" > "$AMF_CONFIG.tmp" && mv "$AMF_CONFIG.tmp" "$AMF_CONFIG"
        fi
    done
    echo -e "AMF PLMN configured: ${GREEN}${MCC}-${MNC}${NC}"

    NRF_CONFIG="$PROJECT_DIR/open5gs/config/nrf.yaml"
    if [ -f "$NRF_CONFIG" ]; then
        sed "s/mcc: \"[^\"]*\"/mcc: \"${MCC}\"/g" "$NRF_CONFIG" > "$NRF_CONFIG.tmp" && mv "$NRF_CONFIG.tmp" "$NRF_CONFIG"
        sed "s/mnc: \"[^\"]*\"/mnc: \"${MNC}\"/g" "$NRF_CONFIG" > "$NRF_CONFIG.tmp" && mv "$NRF_CONFIG.tmp" "$NRF_CONFIG"
        echo -e "NRF PLMN configured: ${GREEN}${MCC}-${MNC}${NC}"
    fi
else
    # Update MME PLMN for 4G mode (both gummei.plmn_id and tai.plmn_id sections)
    MME_CONFIG="$PROJECT_DIR/open5gs/config/mme.yaml"
    if [ -f "$MME_CONFIG" ]; then
        sed "s/mcc: \"[^\"]*\"/mcc: \"${MCC}\"/g" "$MME_CONFIG" > "$MME_CONFIG.tmp" && mv "$MME_CONFIG.tmp" "$MME_CONFIG"
        sed "s/mnc: \"[^\"]*\"/mnc: \"${MNC}\"/g" "$MME_CONFIG" > "$MME_CONFIG.tmp" && mv "$MME_CONFIG.tmp" "$MME_CONFIG"
        echo -e "MME PLMN configured: ${GREEN}${MCC}-${MNC}${NC}"
    else
        echo -e "${YELLOW}Warning: MME config not found at $MME_CONFIG${NC}"
    fi
fi

# =============================================================================
# Step 8: Generate RAN Configuration
# =============================================================================

echo ""
echo -e "${BLUE}Step 8: RAN Configuration File${NC}"
echo "─────────────────────────────────"
echo ""

ENODEB_CONFIG="$PROJECT_DIR/config/enodebs.yaml"
GNODEB_CONFIG="$PROJECT_DIR/config/gnodebs.yaml"

# Generate gNodeB config for 5G mode
if [ "$NETWORK_MODE" = "5g" ] && [ "$SKIP_GNODEB_GENERATION" != "true" ]; then
    cat > "$GNODEB_CONFIG" << 'GNODEB_HEADER'
# =============================================================================
# gNodeB Configuration for Open5G2GO (5G SA Mode)
# =============================================================================
#
# This file defines the gNodeBs in your 5G SA deployment.
# Used for NGAP connection tracking and status display.
#
# Configuration is read at startup. Restart the backend service after changes.
#

gnodebs:
GNODEB_HEADER

    if [ ${#GNODEB_ENTRIES[@]} -gt 0 ]; then
        for entry in "${GNODEB_ENTRIES[@]}"; do
            IFS='|' read -r ip name location <<< "$entry"
            cat >> "$GNODEB_CONFIG" << GNODEB_ENTRY
  - name: "$name"
    ip_address: "$ip"
    location: "$location"

GNODEB_ENTRY
        done
        echo -e "gNodeB config generated: ${GREEN}${#GNODEB_ENTRIES[@]} gNodeB(s)${NC}"
    else
        cat >> "$GNODEB_CONFIG" << 'GNODEB_PLACEHOLDER'
  # No gNodeBs configured during setup.
  # Add your gNodeB(s) here or run the setup wizard again.
  #
  # Example:
  # - name: "gNodeB-1"
  #   ip_address: "10.48.0.159"
  #   location: "Test Lab"

GNODEB_PLACEHOLDER
        echo -e "gNodeB config generated: ${YELLOW}No gNodeBs configured${NC}"
    fi
fi

# Skip eNodeB generation in network reconfiguration mode or 5G mode
if [ "$SKIP_ENODEB_GENERATION" = "true" ] || [ "$NETWORK_MODE" = "5g" ]; then
    if [ "$NETWORK_MODE" != "5g" ]; then
        echo -e "eNodeB config: ${GREEN}Preserved (unchanged)${NC}"
    fi
else
    # Generate enodebs.yaml
    cat > "$ENODEB_CONFIG" << 'ENODEB_HEADER'
# =============================================================================
# eNodeB Configuration for Open5G2GO
# =============================================================================
#
# This file defines the Baicells eNodeBs in your deployment and their
# monitoring configuration for SNMP.
#
# Configuration is read at startup. Restart the backend service after changes.
#

# =============================================================================
# SNMP Settings
# =============================================================================
# SNMP v2c monitoring for Baicells eNodeBs
# Note: eNodeB must have SNMP enabled and allow queries from the docker host IP

snmp:
  enabled: true
  community: "public"
  timeout_seconds: 2
  poll_interval_seconds: 30

# =============================================================================
# eNodeB Definitions
# =============================================================================

enodebs:
ENODEB_HEADER

# Add configured eNodeBs or placeholder
if [ ${#ENODEB_ENTRIES[@]} -gt 0 ]; then
    for entry in "${ENODEB_ENTRIES[@]}"; do
        IFS='|' read -r ip name serial location <<< "$entry"
        cat >> "$ENODEB_CONFIG" << ENODEB_ENTRY
  - serial_number: "$serial"
    ip_address: "$ip"
    name: "$name"
    location: "$location"
    enabled: true

ENODEB_ENTRY
    done
    echo -e "eNodeB config generated: ${GREEN}${#ENODEB_ENTRIES[@]} eNodeB(s)${NC}"
else
    cat >> "$ENODEB_CONFIG" << 'ENODEB_PLACEHOLDER'
  # No eNodeBs configured during setup.
  # Add your eNodeB(s) here or via the Web UI (future feature).
  #
  # Example:
  # - serial_number: "120200046421CKY0606"
  #   ip_address: "192.168.1.100"
  #   name: "Office-eNB"
  #   location: "Server Room"
  #   enabled: true

ENODEB_PLACEHOLDER
    echo -e "eNodeB config generated: ${YELLOW}No eNodeBs configured${NC}"
fi
fi  # End of SKIP_ENODEB_GENERATION check

# =============================================================================
# Step 9: Generate FreeDiameter Certificates (4G only)
# =============================================================================

echo ""
echo -e "${BLUE}Step 9: FreeDiameter Certificates${NC}"
echo "─────────────────────────────────"
echo ""

if [ "$NETWORK_MODE" = "5g" ]; then
    echo -e "FreeDiameter certificates: ${YELLOW}Skipped (not needed for 5G SA)${NC}"

    # Generate HNET keys for SUCI decryption (5G-AKA authentication)
    echo ""
    echo -e "${BLUE}Step 9b: HNET Keys (SUCI Decryption)${NC}"
    echo "─────────────────────────────────"
    echo ""

    HNET_DIR="$PROJECT_DIR/open5gs/hnet"
    mkdir -p "$HNET_DIR"

    if [ ! -f "$HNET_DIR/curve25519-1.key" ]; then
        echo "Generating HNET curve25519 keys for SUCI decryption..."
        # Key ID 1 (primary)
        openssl genpkey -algorithm X25519 -out "$HNET_DIR/curve25519-1.key" 2>/dev/null
        # Key ID 2 (secondary)
        openssl genpkey -algorithm X25519 -out "$HNET_DIR/curve25519-2.key" 2>/dev/null
        chmod 600 "$HNET_DIR"/*.key 2>/dev/null || true
        echo -e "HNET keys: ${GREEN}Generated${NC}"
        echo ""
        echo -e "${YELLOW}NOTE: These keys must match your SIM card's SUPI concealment config.${NC}"
        echo "If your SIMs don't use SUCI concealment, these keys are ignored."
    else
        echo -e "HNET keys: ${GREEN}Already exist${NC}"
    fi
else

CERT_DIR="$PROJECT_DIR/open5gs/config/freeDiameter"

# Generate certificates if not present
if [ ! -f "$CERT_DIR/ca.cert.pem" ]; then
    echo "Generating FreeDiameter certificates..."

    # Generate DH parameters
    openssl dhparam -out "$CERT_DIR/dh.pem" 2048 2>/dev/null

    # Generate CA key and certificate
    openssl genrsa -out "$CERT_DIR/ca.key.pem" 2048 2>/dev/null
    openssl req -new -x509 -days 3650 -key "$CERT_DIR/ca.key.pem" -out "$CERT_DIR/ca.cert.pem" \
        -subj "/CN=Open5G2GO-CA/O=Waveriders/C=US" 2>/dev/null

    # Generate certificates for each component
    for component in hss mme smf pcrf; do
        openssl genrsa -out "$CERT_DIR/${component}.key.pem" 2048 2>/dev/null
        openssl req -new -key "$CERT_DIR/${component}.key.pem" -out "$CERT_DIR/${component}.csr.pem" \
            -subj "/CN=${component}.open5g2go.local/O=Waveriders/C=US" 2>/dev/null
        openssl x509 -req -days 3650 -in "$CERT_DIR/${component}.csr.pem" \
            -CA "$CERT_DIR/ca.cert.pem" -CAkey "$CERT_DIR/ca.key.pem" -CAcreateserial \
            -out "$CERT_DIR/${component}.cert.pem" 2>/dev/null
        rm -f "$CERT_DIR/${component}.csr.pem"
    done

    # Set proper permissions
    chmod 644 "$CERT_DIR"/*.pem 2>/dev/null || true
    chmod 600 "$CERT_DIR"/*.key.pem 2>/dev/null || true

    echo -e "FreeDiameter certificates: ${GREEN}Generated${NC}"
else
    echo -e "FreeDiameter certificates: ${GREEN}Already exist${NC}"
fi

fi  # End of 4G-only FreeDiameter section

# =============================================================================
# Step 10: Pre-configure SGWU / UPF advertise IP
# =============================================================================

echo ""
echo -e "${BLUE}Step 10: GTP-U Advertise Configuration${NC}"
echo "─────────────────────────────────"
echo ""

if [ "$NETWORK_MODE" = "5g" ]; then
    # 5G: UPF runs in host mode — no advertise IP needed.
    # GTP-U binds to 0.0.0.0 and the gNodeB connects to the real host IP directly.
    echo -e "UPF GTP-U advertise: ${GREEN}Not needed (host mode — gNodeB uses host IP directly)${NC}"
    echo -e "AMF NGAP: ${GREEN}Host mode on 0.0.0.0:38412${NC}"
else
    # 4G: Configure SGWU advertise address (eNodeB needs this)
    SGWU_CONFIG="$PROJECT_DIR/open5gs/config/sgwu.yaml"
    if [ -f "$SGWU_CONFIG" ]; then
        echo "Configuring SGWU advertise address..."
        sed "s/advertise:.*/advertise: ${DOCKER_HOST_IP}/" "$SGWU_CONFIG" > "$SGWU_CONFIG.tmp"
        mv "$SGWU_CONFIG.tmp" "$SGWU_CONFIG"
        echo -e "SGWU advertise IP: ${GREEN}${DOCKER_HOST_IP}${NC}"
    else
        echo -e "${YELLOW}Warning: SGWU config not found at $SGWU_CONFIG${NC}"
    fi
fi

# =============================================================================
# Summary
# =============================================================================

echo ""
echo -e "${BOLD}========================================"
if [ "$SETUP_MODE" = "network" ]; then
    echo "  Network Reconfiguration Complete!"
else
    echo "  Setup Complete!"
fi
echo -e "========================================${NC}"
echo ""
echo "Configuration Summary:"
echo "  Mode:         ${NETWORK_MODE^^}"
echo "  Host IP:      $DOCKER_HOST_IP"
echo "  UE Pool:      $UE_POOL_SUBNET"
echo "  PLMN:         ${MCC}-${MNC}"
echo "  Compose:      $COMPOSE_FILE"
if [ "$SETUP_MODE" = "network" ]; then
    echo "  SIM Keys:     Preserved"
    echo "  RAN Config:   Preserved"
    echo ""
    echo "Network settings updated. Other configuration preserved."
    echo ""
    echo "Next step: Restart the stack to apply changes:"
    echo "  docker compose -f $COMPOSE_FILE down"
    echo "  ./scripts/pull-and-run.sh"
else
    echo "  SIM Keys:     Configured"
    if [ "$NETWORK_MODE" = "5g" ]; then
        echo "  gNodeBs:      ${#GNODEB_ENTRIES[@]} configured"
    else
        echo "  eNodeBs:      ${#ENODEB_ENTRIES[@]} configured"
    fi
    echo ""
    echo "Next step: Run ./scripts/pull-and-run.sh to start the stack"
fi
echo ""
