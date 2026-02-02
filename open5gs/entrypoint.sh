#!/bin/bash
# Open5GS container entrypoint script
# Handles environment variable substitution and service startup

set -e

# Default MongoDB URI if not set
DB_URI=${DB_URI:-mongodb://localhost/open5gs}

# Update HSS config with MongoDB URI if HSS config exists
if [ -f /etc/open5gs/hss.yaml ]; then
    sed -i "s|^db_uri:.*|db_uri: ${DB_URI}|g" /etc/open5gs/hss.yaml 2>/dev/null || true
fi

# For UPF: Setup TUN interface if running as upfd
if [ "$1" = "open5gs-upfd" ]; then
    echo "Setting up UPF networking..."

    # Create TUN device if not exists
    if [ ! -e /dev/net/tun ]; then
        mkdir -p /dev/net
        mknod /dev/net/tun c 10 200
        chmod 600 /dev/net/tun
    fi

    # Enable IP forwarding
    sysctl -w net.ipv4.ip_forward=1 2>/dev/null || true

    # Setup NAT for UE traffic (10.48.99.0/24 is our UE pool)
    iptables -t nat -A POSTROUTING -s 10.48.99.0/24 ! -o ogstun -j MASQUERADE 2>/dev/null || true

    # Background task to configure ogstun after UPF creates it
    (
        echo "Waiting for ogstun interface..."
        for i in $(seq 1 30); do
            if ip link show ogstun >/dev/null 2>&1; then
                echo "Configuring ogstun interface..."
                ip link set ogstun up
                ip addr add 10.48.99.1/24 dev ogstun 2>/dev/null || true
                echo "ogstun configured: $(ip addr show ogstun | grep inet)"
                exit 0
            fi
            sleep 1
        done
        echo "WARNING: ogstun interface not found after 30 seconds"
    ) &
fi

# For SGWU: Network setup
# Note: The advertise IP should be pre-configured by setup-wizard.sh
# We no longer modify the config at runtime since it's mounted read-only
if [ "$1" = "open5gs-sgwud" ]; then
    echo "Setting up SGWU networking..."

    # Verify advertise IP is configured (informational only)
    if [ -n "$HOST_IP" ] && [ -f /etc/open5gs/sgwu.yaml ]; then
        if grep -q "advertise:" /etc/open5gs/sgwu.yaml 2>/dev/null; then
            CONFIGURED_IP=$(grep "advertise:" /etc/open5gs/sgwu.yaml | awk '{print $2}' | head -1)
            if [ "$CONFIGURED_IP" = "$HOST_IP" ]; then
                echo "SGWU advertise IP correctly configured: $HOST_IP"
            else
                echo "WARNING: SGWU advertise IP ($CONFIGURED_IP) differs from HOST_IP ($HOST_IP)"
                echo "If eNodeB cannot connect, run: ./scripts/setup-wizard.sh"
            fi
        fi
    fi

    if [ ! -e /dev/net/tun ]; then
        mkdir -p /dev/net
        mknod /dev/net/tun c 10 200
        chmod 600 /dev/net/tun
    fi
fi

echo "Starting $1..."
exec "$@"
