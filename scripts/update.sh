#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Waveriders Collective Inc.
# scripts/update.sh - Open5G2GO Update Script
# Pulls latest code and images, restarts services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Colors
GREEN='[0;32m'
YELLOW='[1;33m'
BOLD='[1m'
NC='[0m'

echo ""
echo -e "${BOLD}========================================"
echo "  Open5G2GO Update"
echo -e "========================================${NC}"
echo ""

# Step 1: Pull latest code
echo -e "${YELLOW}Step 1:${NC} Pulling latest code..."
if git pull; then
    echo -e "  Code updated: ${GREEN}OK${NC}"
else
    echo -e "  ${YELLOW}Warning: Could not pull latest code (may not be a git repo)${NC}"
fi

# Step 2: Pull latest images
echo ""
echo -e "${YELLOW}Step 2:${NC} Pulling latest Docker images..."
docker compose -f docker-compose.prod.yml pull
echo -e "  Images updated: ${GREEN}OK${NC}"

# Step 3: Restart services
echo ""
echo -e "${YELLOW}Step 3:${NC} Restarting services..."
docker compose -f docker-compose.prod.yml up -d
echo -e "  Services restarted: ${GREEN}OK${NC}"

# Step 4: Wait for health check
echo ""
echo -e "${YELLOW}Step 4:${NC} Waiting for services to become healthy..."
sleep 5

MAX_ATTEMPTS=20
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo -e "  Backend healthy: ${GREEN}OK${NC}"
        break
    fi
    ((ATTEMPT++))
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo -e "  ${YELLOW}Warning: Backend health check timed out${NC}"
    echo "  Check logs: docker compose -f docker-compose.prod.yml logs backend"
fi

# Summary
HOST_IP=$(grep DOCKER_HOST_IP .env 2>/dev/null | cut -d= -f2 || echo "localhost")

echo ""
echo -e "${BOLD}========================================"
echo "  Update Complete!"
echo -e "========================================${NC}"
echo ""
echo "  Web UI: http://${HOST_IP}:8080"
echo ""
