#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Waveriders Collective Inc.
# scripts/preflight-check.sh

set -e

RED='[0;31m'
GREEN='[0;32m'
YELLOW='[1;33m'
NC='[0m'

echo "========================================"
echo "  Open5G2GO Preflight Checks"
echo "========================================"
echo ""

ERRORS=0

# Check Docker
check_docker() {
    echo -n "Checking Docker... "
    if command -v docker &> /dev/null && docker info &> /dev/null; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAILED${NC}"
        echo "  -> Install Docker: https://docs.docker.com/get-docker/"
        ((ERRORS++))
    fi
}

# Check Docker Compose
check_compose() {
    echo -n "Checking Docker Compose... "
    if docker compose version &> /dev/null; then
        VERSION=$(docker compose version --short)
        echo -e "${GREEN}OK${NC} (v$VERSION)"
    else
        echo -e "${RED}FAILED${NC}"
        echo "  -> Docker Compose v2 required"
        ((ERRORS++))
    fi
}

# Check SCTP
check_sctp() {
    echo -n "Checking SCTP kernel module... "
    if lsmod | grep -q sctp || modprobe -n sctp 2>/dev/null; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${YELLOW}WARNING${NC}"
        echo "  -> Run: sudo modprobe sctp"
        echo "  -> Add 'sctp' to /etc/modules for persistence"
    fi
}

# Check ports
check_ports() {
    echo -n "Checking port availability... "
    PORTS_IN_USE=""
    for PORT in 36412 2152 8080; do
        if ss -tuln | grep -q ":$PORT "; then
            PORTS_IN_USE="$PORTS_IN_USE $PORT"
        fi
    done
    if [ -z "$PORTS_IN_USE" ]; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAILED${NC}"
        echo "  -> Ports in use:$PORTS_IN_USE"
        ((ERRORS++))
    fi
}

# Check disk space
check_disk() {
    echo -n "Checking disk space... "
    AVAILABLE=$(df -BG . | awk 'NR==2 {print $4}' | tr -d 'G')
    if [ "$AVAILABLE" -ge 5 ]; then
        echo -e "${GREEN}OK${NC} (${AVAILABLE}GB available)"
    else
        echo -e "${RED}FAILED${NC}"
        echo "  -> Need at least 5GB, have ${AVAILABLE}GB"
        ((ERRORS++))
    fi
}

# Run all checks
check_docker
check_compose
check_sctp
check_ports
check_disk

echo ""
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}All preflight checks passed!${NC}"
    exit 0
else
    echo -e "${RED}$ERRORS check(s) failed. Please fix before continuing.${NC}"
    exit 1
fi
