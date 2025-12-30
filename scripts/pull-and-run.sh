#!/bin/bash
# scripts/pull-and-run.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Pulling Docker images from ghcr.io..."
docker compose -f docker-compose.prod.yml pull

echo "Starting Open5G2GO stack..."
docker compose -f docker-compose.prod.yml up -d

echo "Waiting for services to become healthy..."
sleep 10

# Wait for backend health check
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        break
    fi
    ((ATTEMPT++))
    echo "  Waiting for backend... ($ATTEMPT/$MAX_ATTEMPTS)"
    sleep 3
done

HOST_IP=$(grep DOCKER_HOST_IP .env 2>/dev/null | cut -d= -f2 || echo "localhost")

echo ""
echo "========================================"
echo "  Open5G2GO is running!"
echo "========================================"
echo ""
echo "  Web UI: http://${HOST_IP}:8080"
echo "  API:    http://${HOST_IP}:8080/api/v1"
echo ""
echo "  View logs: docker compose -f docker-compose.prod.yml logs -f"
echo "  Stop:      docker compose -f docker-compose.prod.yml down"
echo ""
