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

# For SGWU: Similar network setup
if [ "$1" = "open5gs-sgwud" ]; then
    echo "Setting up SGWU networking..."

    if [ ! -e /dev/net/tun ]; then
        mkdir -p /dev/net
        mknod /dev/net/tun c 10 200
        chmod 600 /dev/net/tun
    fi
fi

echo "Starting $1..."
exec "$@"
