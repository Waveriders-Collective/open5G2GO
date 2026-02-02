# Open5G2GO

Homelab toolkit for private 4G cellular networks, combining:
- **Open5GS** (open-source mobile core) via docker_open5gs
- **openSurfControl** (web-based management UI)
- **Waveriders-tested configurations** for broadcast, CCTV, and event production

## Quick Start

### One-Line Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/Waveriders-Collective/openSurfcontrol/main/install.sh | bash
```

This will:
1. Check system prerequisites
2. Clone the repository
3. Run interactive setup wizard
4. Pull pre-built Docker images
5. Start the stack

### Manual Install

```bash
# Clone repository
git clone https://github.com/Waveriders-Collective/openSurfcontrol.git
cd openSurfcontrol

# Run setup
./scripts/preflight-check.sh
./scripts/setup-wizard.sh
./scripts/pull-and-run.sh
```

### Requirements

- Ubuntu 22.04+ (or similar Linux with Docker)
- Docker 24.0+
- Docker Compose v2+
- 5GB free disk space
- Ports: 36412/sctp, 2152/udp, 8080/tcp

### Updates

```bash
cd ~/openSurfcontrol
./scripts/update.sh
```

## Project Status

**Version:** 0.1.0-beta
**Status:** Phase 1 Complete - Repository Setup

### MVP Scope

| Feature | Specification |
|---------|---------------|
| Network Type | 4G LTE only |
| Mobile Core | Open5GS |
| PLMN | 315-010 (US private network) |
| Devices | 10 max, static IP assignment |
| UE IP Pool | 10.48.99.0/24 |
| QoS Profile | Single profile, best-effort (QCI 9) |
| Radio | Single Baicells eNodeB |

### Not Included (Future Phases)
- 5G SA support
- Multiple QoS profiles
- Multiple eNodeB support
- TLS/HTTPS (lab environment)
- Prometheus monitoring

## Architecture

```
open5g2go/
├── opensurfcontrol/      # MCP server + MongoDB adapter
│   ├── server.py         # MCP tools
│   ├── mongodb_client.py # Open5GS database adapter
│   ├── constants.py      # Network configuration
│   └── ...
├── web_backend/          # FastAPI REST API
│   ├── main.py           # API server
│   └── api/              # Routes and models
├── web_frontend/         # React TypeScript SPA
│   └── src/              # UI components
├── open5gs/              # Open5GS configurations
└── docker-compose.yml    # Full stack deployment
```

## Components

### openSurfControl (MCP Server)
Python package providing tools for Open5GS subscriber management:
- `list_subscribers` - List all provisioned devices
- `get_subscriber` - Get device details by IMSI
- `add_subscriber` - Provision new device
- `update_subscriber` - Update device configuration
- `delete_subscriber` - Remove device
- `get_system_status` - System health dashboard
- `get_network_config` - Network configuration

### Web Backend (FastAPI)
REST API exposing subscriber management:
- `GET /api/v1/subscribers` - List devices
- `POST /api/v1/subscribers` - Add device
- `GET /api/v1/subscribers/{imsi}` - Get device
- `PUT /api/v1/subscribers/{imsi}` - Update device
- `DELETE /api/v1/subscribers/{imsi}` - Delete device
- `GET /api/v1/status` - System status
- `GET /api/v1/config` - Network config

### Web Frontend (React)
Single-page application with:
- Dashboard with system status
- Device management (CRUD)
- Network configuration view

## SIM Configuration

Waveriders provides pre-programmed SIMs with:
- PLMN: 315-010
- IMSI range: 315010000000001 - 315010000009999

Users enter only the last 4 digits when adding a device:
```
User enters: 0001
Full IMSI:   315010000000001
```

## Development

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker & Docker Compose

### Local Development

```bash
# Install Python dependencies
poetry install

# Install frontend dependencies
cd web_frontend && npm install && cd ..

# Run backend (development mode)
DEBUG=true poetry run opensurfcontrol-web

# Run frontend (development mode)
cd web_frontend && npm run dev
```

### Testing

```bash
# Run Python tests
poetry run pytest

# Run frontend linting
cd web_frontend && npm run lint
```

## License

Open5G2GO is licensed under the [GNU Affero General Public License v3.0](LICENSE) (AGPLv3).

Copyright © 2025 Waveriders Collective Inc.

### Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) and sign our [Contributor License Agreement](CLA.md) before submitting a pull request.

## Support

- [GitHub Issues](https://github.com/Waveriders-Collective/open5G2GO/issues) - Bug reports and feature requests
- [GitHub Discussions](https://github.com/Waveriders-Collective/open5G2GO/discussions) - Questions and community support
