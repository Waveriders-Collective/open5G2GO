# Open5G2GO

Homelab toolkit for private 4G cellular networks, combining:
- **Open5GS** (open-source mobile core) via docker_open5gs
- **openSurfControl** (web-based management UI)
- **Waveriders-tested configurations** for broadcast, CCTV, and event production

## Quick Start

### Before You Begin

The setup wizard will prompt you for the following information. Have these ready:

| Item | Description | Where to Get It |
|------|-------------|-----------------|
| **SIM Ki Key** | 32-character hex authentication key | From your SIM vendor |
| **SIM OPc Key** | 32-character hex operator key | From your SIM vendor |
| **PLMN** | Network identity (MCC-MNC) matching your SIMs | Usually 315-010 for US CBRS |
| **eNodeB IP Address** | Management IP of your Baicells eNodeB | From eNodeB web interface or DHCP |
| **Host IP Address** | IP of the machine running Open5G2GO | Auto-detected, but verify it's reachable from eNodeB |

**Need SIMs?** Order pre-programmed SIMs with matching Ki/OPc at: https://waveriders.live/sims

### One-Line Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/Waveriders-Collective/open5G2GO/main/install.sh | bash
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
git clone https://github.com/Waveriders-Collective/open5G2GO.git
cd open5G2GO

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
cd ~/open5G2GO
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
| PLMN | Configurable (315-010, 001-01, 999-99, 999-01) |
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
├── opensurfcontrol/      # Core library
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

You need pre-programmed SIM cards with Ki and OPc authentication keys.

**Requirements:**
- Ki (Authentication Key) - 32 hex characters
- OPc (Operator Key) - 32 hex characters
- IMSI programmed to match your selected PLMN

**Setup Wizard PLMN Options:**
- 315-010 - US CBRS Private LTE (default)
- 001-01 - Test Network (sysmocom/programmable SIMs)
- 999-99 - Test Network
- 999-01 - Test Network

When adding devices, enter the full 15-digit IMSI from your SIM card:
```
Example: 315010000000001
```

Need SIMs? Order pre-programmed SIMs at: https://waveriders.live/sims

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
