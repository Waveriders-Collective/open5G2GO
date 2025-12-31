#!/bin/bash
# scripts/pull-and-run.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# =============================================================================
# Host Network Setup for UE Data Path
# =============================================================================
# The UPF container handles UE traffic on the ogstun interface (10.48.99.0/24).
# The host needs routing and NAT rules to forward this traffic to the internet.

setup_host_networking() {
    echo "Configuring host networking for UE data path..."

    # UE subnet and UPF container IP (on Docker bridge)
    UE_SUBNET="10.48.99.0/24"
    UPF_IP="172.26.0.15"

    # Detect primary interface (the one with default route)
    PRIMARY_IF=$(ip route | grep default | awk '{print $5}' | head -1)
    if [ -z "$PRIMARY_IF" ]; then
        echo "  Warning: Could not detect primary network interface"
        PRIMARY_IF="eth0"
    fi

    # Enable IP forwarding
    if [ "$(cat /proc/sys/net/ipv4/ip_forward)" != "1" ]; then
        echo "  Enabling IP forwarding..."
        sysctl -w net.ipv4.ip_forward=1 > /dev/null
    fi

    # Add route for UE subnet via UPF container
    if ! ip route show | grep -q "$UE_SUBNET"; then
        echo "  Adding route for UE subnet ($UE_SUBNET) via UPF ($UPF_IP)..."
        ip route add $UE_SUBNET via $UPF_IP 2>/dev/null || true
    fi

    # Add NAT rule for UE subnet
    if ! iptables -t nat -C POSTROUTING -s $UE_SUBNET -o $PRIMARY_IF -j MASQUERADE 2>/dev/null; then
        echo "  Adding NAT rule for UE subnet on $PRIMARY_IF..."
        iptables -t nat -A POSTROUTING -s $UE_SUBNET -o $PRIMARY_IF -j MASQUERADE
    fi

    echo "  Host networking configured successfully"
}

# Run network setup (requires root)
if [ "$EUID" -eq 0 ]; then
    setup_host_networking
else
    echo "Note: Run as root to configure host networking for UE data path"
fi

# =============================================================================
# Docker Compose Deployment
# =============================================================================

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

# Run network setup again after containers are up (route needs Docker bridge to exist)
if [ "$EUID" -eq 0 ]; then
    setup_host_networking
fi

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
