#!/bin/bash
# scripts/setup-wizard.sh - Open5G2GO Interactive Setup Wizard
# Generates .env file from env.example with user-provided values

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${BOLD}========================================"
echo "  Open5G2GO Setup Wizard"
echo -e "========================================${NC}"
echo ""

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
# Step 1: Network Configuration
# =============================================================================

echo -e "${BLUE}Step 1: Network Configuration${NC}"
echo "─────────────────────────────────"
echo ""

# Auto-detect host IP
DETECTED_IP=$(detect_host_ip)
echo -e "Detected host IP: ${YELLOW}$DETECTED_IP${NC}"
echo "This is the IP address your eNodeB will connect to."
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
# Step 2: SIM Configuration
# =============================================================================

echo ""
echo -e "${BLUE}Step 2: SIM Configuration${NC}"
echo "─────────────────────────────────"
echo ""
echo "Choose your SIM card configuration:"
echo ""
echo -e "  ${BOLD}[W]${NC} Waveriders-provided SIMs (default K/OPc keys)"
echo -e "  ${BOLD}[B]${NC} Bring Your Own SIMs (enter your K/OPc keys)"
echo ""

read -p "Choice [W/B]: " sim_choice
sim_choice="${sim_choice:-W}"

if [[ "${sim_choice^^}" == "B" ]]; then
    echo ""
    echo "Enter your SIM authentication keys (32 hex characters each):"
    echo ""

    while true; do
        read -p "Default K: " OPEN5GS_DEFAULT_K
        if validate_hex_key "$OPEN5GS_DEFAULT_K" "K"; then
            break
        fi
    done

    while true; do
        read -p "Default OPc: " OPEN5GS_DEFAULT_OPC
        if validate_hex_key "$OPEN5GS_DEFAULT_OPC" "OPc"; then
            break
        fi
    done
else
    # Waveriders defaults
    OPEN5GS_DEFAULT_K="465B5CE8B199B49FAA5F0A2EE238A6BC"
    OPEN5GS_DEFAULT_OPC="E8ED289DEBA952E4283B54E88E6183CA"
    echo -e "Using Waveriders default SIM keys: ${GREEN}OK${NC}"
fi

# =============================================================================
# Step 3: GitHub Authentication
# =============================================================================

echo ""
echo -e "${BLUE}Step 3: GitHub Authentication${NC}"
echo "─────────────────────────────────"
echo ""
echo "Docker images are hosted on GitHub Container Registry (ghcr.io)."
echo "You need a GitHub Personal Access Token (PAT) with 'read:packages' scope."
echo ""
echo -e "Create one at: ${YELLOW}https://github.com/settings/tokens/new${NC}"
echo "Required scope: read:packages"
echo ""

# Check if already logged in
if docker pull ghcr.io/waveriders-collective/open5g2go-backend:latest --quiet 2>/dev/null; then
    echo -e "Already authenticated with ghcr.io: ${GREEN}OK${NC}"
    GITHUB_AUTHENTICATED=true
else
    GITHUB_AUTHENTICATED=false

    read -p "GitHub username: " GITHUB_USER

    if [ -z "$GITHUB_USER" ]; then
        echo -e "${RED}Error: GitHub username is required${NC}"
        exit 1
    fi

    read -s -p "GitHub PAT (hidden): " GITHUB_PAT
    echo ""

    if [ -z "$GITHUB_PAT" ]; then
        echo -e "${RED}Error: GitHub PAT is required${NC}"
        exit 1
    fi

    echo ""
    echo "Authenticating with ghcr.io..."

    if echo "$GITHUB_PAT" | docker login ghcr.io -u "$GITHUB_USER" --password-stdin 2>/dev/null; then
        echo -e "Successfully authenticated with ghcr.io: ${GREEN}OK${NC}"
        GITHUB_AUTHENTICATED=true
    else
        echo -e "${RED}Authentication failed!${NC}"
        echo "Please check your username and PAT, then try again."
        exit 1
    fi
fi

# =============================================================================
# Step 4: Docker Configuration
# =============================================================================

echo ""
echo -e "${BLUE}Step 4: Docker Configuration${NC}"
echo "─────────────────────────────────"
echo ""

# Detect Docker group ID
DOCKER_GID=$(getent group docker 2>/dev/null | cut -d: -f3 || echo "994")
echo -e "Detected Docker group ID: ${YELLOW}$DOCKER_GID${NC}"

# =============================================================================
# Step 5: Generate .env file
# =============================================================================

echo ""
echo -e "${BLUE}Step 5: Generating Configuration${NC}"
echo "─────────────────────────────────"
echo ""

# Check if .env already exists
if [ -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file already exists${NC}"
    read -p "Overwrite? [y/N]: " overwrite
    if [[ ! "${overwrite}" =~ ^[Yy] ]]; then
        echo "Keeping existing .env file."
        echo "Setup complete (configuration unchanged)."
        exit 0
    fi
    cp .env .env.backup
    echo "Backup saved to .env.backup"
fi

# Generate .env file
cat > .env << EOF
# Open5G2GO Environment Configuration
# Generated by setup-wizard.sh on $(date -Iseconds)

# =============================================================================
# Network Configuration
# =============================================================================

# Docker host IP address (the machine running docker-compose)
# This should be the IP your eNodeB will connect to
DOCKER_HOST_IP=${DOCKER_HOST_IP}

# Host IP alias for backend service
HOST_IP=${DOCKER_HOST_IP}

# UE IP Pool (assigned to connected devices)
UE_POOL_SUBNET=${UE_POOL_SUBNET}
UE_POOL_GATEWAY=${UE_POOL_GATEWAY}

# =============================================================================
# PLMN Configuration (Network Identity)
# =============================================================================

# Mobile Country Code (315 = US private network)
MCC=315

# Mobile Network Code (010 = Waveriders test network)
MNC=010

# =============================================================================
# SIM Authentication Keys
# =============================================================================

# Default authentication keys for subscriber provisioning
OPEN5GS_DEFAULT_K=${OPEN5GS_DEFAULT_K}
OPEN5GS_DEFAULT_OPC=${OPEN5GS_DEFAULT_OPC}

# =============================================================================
# S1AP Configuration (eNodeB Connection)
# =============================================================================

# S1AP port for eNodeB connection
S1AP_PORT=36412

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

# MongoDB URI (used by backend and HSS)
MONGODB_URI=mongodb://mongodb:27017/open5gs
EOF

echo -e "Configuration file generated: ${GREEN}.env${NC}"

# =============================================================================
# Summary
# =============================================================================

echo ""
echo -e "${BOLD}========================================"
echo "  Setup Complete!"
echo -e "========================================${NC}"
echo ""
echo "Configuration Summary:"
echo "  Host IP:      $DOCKER_HOST_IP"
echo "  UE Pool:      $UE_POOL_SUBNET"
echo "  SIM Keys:     ${sim_choice^^} ($([ "${sim_choice^^}" == "W" ] && echo "Waveriders" || echo "Custom"))"
echo "  GitHub Auth:  $([ "$GITHUB_AUTHENTICATED" == "true" ] && echo "OK" || echo "Skipped")"
echo ""
echo "Next step: Run ./scripts/pull-and-run.sh to start the stack"
echo ""
