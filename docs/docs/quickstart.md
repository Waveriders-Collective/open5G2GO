# Quick Start Guide

Get up and running with Open5G2GO in minutes.

## Prerequisites

Before you begin, ensure your system meets these requirements:

- **Operating System**: Ubuntu 22.04 LTS or similar Linux distribution
- **Docker**: Version 24.0 or later
- **Docker Compose**: v2 or later
- **Disk Space**: At least 5GB free space
- **Static IP**: The host must have a static IP address (not DHCP) — your base station and UE traffic depend on it
- **SCTP Kernel Module**: Required for base station connections — `sudo modprobe sctp`
- **Network Ports**: The following ports must be available:
  - `36412/sctp` - S1AP traffic (4G mode)
  - `38412/sctp` - NGAP traffic (5G mode)
  - `2152/udp` - GTP-U traffic
  - `8080/tcp` - Web UI and API
- **SIM Cards**: Pre-programmed SIMs with known Ki and OPc authentication keys

## Installation

### One-liner Install (Recommended)

For the quickest setup, use the automated installation script:

```bash
curl -fsSL https://raw.githubusercontent.com/Waveriders-Collective/open5G2GO/main/install.sh | bash
```

This script will handle all setup steps automatically.

### Manual Install

If you prefer manual installation or need more control over the setup process:

1. Clone the repository:
   ```bash
   git clone https://github.com/Waveriders-Collective/open5G2GO.git
   cd open5G2GO
   ```

2. Run the preflight check to verify your system:
   ```bash
   ./scripts/preflight-check.sh
   ```

3. Run the setup wizard (you will be prompted to choose 4G or 5G mode):
   ```bash
   ./scripts/setup-wizard.sh
   ```

4. Pull images and start the services:
   ```bash
   ./scripts/pull-and-run.sh
   ```

## First Device Provisioning

Once the system is running, you can add your first device:

1. **Access the Web UI**: Open your browser and navigate to `http://YOUR_IP:8080` (replace `YOUR_IP` with your server's IP address)

2. **Navigate to Devices**: Click on the "Devices" page in the navigation menu

3. **Add Device**: Click the "Add Device" button

4. **Enter Device Information**:
   - **IMSI**: Enter the full 15-digit IMSI from your SIM card (e.g., `315010000000001`)
   - **Device Name**: Give it a friendly name (e.g., "Camera-01")

5. **Confirm**: The device will appear in the devices list once successfully provisioned

## Verification

### Check Container Health

Verify that all Docker containers are running and healthy:

```bash
docker compose -f docker-compose.prod.yml ps
```

All containers should show a status of "Up" or "healthy".

### Check API Health

Verify the API is responding correctly:

```bash
curl http://localhost:8080/api/v1/health
```

A successful response indicates the system is operational.

### Firewall Rules

Depending on your chosen network mode, ensure the appropriate ports are open:

**4G LTE mode:**
```bash
sudo ufw allow 36412/sctp   # S1AP (eNodeB → MME)
sudo ufw allow 2152/udp     # GTP-U
sudo ufw allow 8080/tcp     # Web UI
```

**5G SA mode:**
```bash
sudo ufw allow 38412/sctp   # NGAP (gNodeB → AMF)
sudo ufw allow 2152/udp     # GTP-U
sudo ufw allow 8080/tcp     # Web UI
```

## LAN Access to UE Devices

By default, UE devices (phones, modems) connected through the cellular network get IP addresses in the `10.48.99.0/24` subnet. To make them reachable from other hosts on your LAN, add a static route on your router pointing the UE subnet at the core host:

```
# Example for a router with the core host at 192.168.8.5:
ip route add 10.48.99.0/24 via 192.168.8.5
```

The core host automatically configures NAT and forwarding rules so that UE traffic can reach the internet and LAN hosts can reach UEs.

## Optional: Local Speed Testing

Deploy [OpenSpeedTest](https://openspeedtest.com) on the core host for throughput testing over the cellular link without depending on internet bandwidth:

```bash
sudo docker run --restart=unless-stopped --name openspeedtest -d -p 3000:3000 openspeedtest/latest
```

Then navigate to `http://<host-ip>:3000` from a UE.

## Next Steps

- Review the [User Guide](./user-guide.md) for detailed UI walkthrough
- See the [eNodeB Setup Guide](./enodeb-setup.md) for 4G base station configuration
- See the [gNodeB Setup Guide](./gnodeb-setup.md) for 5G base station configuration
- Read the [Operations Guide](./operations.md) for upgrades and network changes
- Check [Troubleshooting](./troubleshooting.md) for common issues
