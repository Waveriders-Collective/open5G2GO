# Quick Start Guide

Get up and running with Open5G2GO in minutes.

## Prerequisites

Before you begin, ensure your system meets these requirements:

- **Operating System**: Ubuntu 22.04 LTS or similar Linux distribution
- **Docker**: Version 24.0 or later
- **Docker Compose**: v2 or later
- **Disk Space**: At least 5GB free space
- **Network Ports**: The following ports must be available:
  - `36412/sctp` - SCTP traffic
  - `2152/udp` - GTP-U traffic
  - `8080/tcp` - Web UI and API

## Installation

### One-liner Install (Recommended)

For the quickest setup, use the automated installation script:

```bash
curl -fsSL https://raw.githubusercontent.com/Waveriders-Collective/openSurfcontrol/main/install.sh | bash
```

This script will handle all setup steps automatically.

### Manual Install

If you prefer manual installation or need more control over the setup process:

1. Clone the repository:
   ```bash
   git clone https://github.com/Waveriders-Collective/openSurfcontrol.git
   cd openSurfcontrol
   ```

2. Run the preflight check to verify your system:
   ```bash
   ./scripts/preflight-check.sh
   ```

3. Run the setup wizard:
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
   - Enter the last 4 digits of the IMSI (International Mobile Subscriber Identity)
   - Example: `0001` for IMSI ending in 0001

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

## Next Steps

- Review the [Configuration Guide](./configuration.md) for advanced setup options
- Check the [API Documentation](./api.md) for integration details
- See [Troubleshooting](./troubleshooting.md) for common issues
