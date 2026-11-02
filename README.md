# Open5G2GO

Homelab toolkit for private 4G LTE and 5G SA cellular networks, combining:
- **Open5GS** (open-source mobile core) via docker_open5gs
- **openSurfControl** (web-based management UI)
- **Waveriders-tested configurations** for broadcast, CCTV, and event production

## Quick Start

### Before You Begin

The setup wizard will prompt you for the following information. Have these ready:

| Item | Description | Where to Get It |
|------|-------------|-----------------|
| **SIM Ki Key** | 32-character hex authentication key | From your SIM vendor, or generate for a programmable SIM during setup |
| **SIM OPc Key** | 32-character hex derived operator key | From your SIM vendor, or derive with Ki and a generated source OP during setup |
| **PLMN** | Network identity (MCC-MNC) matching your SIMs | Usually 315-010 for US CBRS |
| **eNodeB/gNodeB IP Address** | Management IP of your base station | From base station web interface or DHCP |
| **Host IP Address** | IP of the machine running Open5G2GO | Auto-detected, but verify it's reachable from base station |

**Need SIMs?** Order pre-programmed SIMs with matching Ki/OPc at: https://waveriders.live/sims

### One-Line Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/Waveriders-Collective/open5G2GO/main/install.sh | bash
```

This will:
1. Check required tools and offer to install missing packages with your approval
2. Clone the repository
3. Run interactive setup wizard
4. Pull pre-built Docker images
5. Start the stack

On Ubuntu and Debian, the installer lists missing packages and asks before running
`apt-get update` and installing them with `sudo` (or directly when run as root).
It checks Git, curl, OpenSSL, Docker, Docker Compose, and the Linux networking
tools used during setup. Missing Docker components are installed using Docker's
official [Ubuntu](https://docs.docker.com/engine/install/ubuntu/#install-using-the-apt-repository)
or [Debian](https://docs.docker.com/engine/install/debian/#install-using-the-apt-repository)
apt-repository instructions, including the signing key when needed. Existing
packages are not removed, and a full system upgrade is not run.
Run the command from an interactive terminal; declining the prompt stops before
the repository is cloned or an existing installation is changed.

If the local Docker service is stopped, the installer asks whether to start it
with `sudo systemctl start docker` or exit. After approval it starts Docker and
checks that it is accessible before continuing. A running daemon with a permission
error is reported separately, with instructions to configure access and log in
again. Remote and rootless Docker contexts require their own daemon setup; the
installer only offers to start the local systemd service. On other Linux
distributions, install missing dependencies using your distribution's package
manager.

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
- Ports: 36412/sctp (4G S1AP), 38412/sctp (5G NGAP), 2152/udp, 8080/tcp

### Updates

```bash
cd ~/open5G2GO
./scripts/update.sh
```

## Project Status

**Version:** 0.2.0-beta
**Status:** Phase 2 Complete - 5G SA Support

### MVP Scope

| Feature | Specification |
|---------|---------------|
| Network Type | 4G LTE + 5G SA |
| Mobile Core | Open5GS |
| PLMN | Configurable (315-010, 001-01, 999-99, 999-01) |
| Devices | 10 max, static IP assignment |
| UE IP Pool | 10.48.99.0/24 |
| QoS Profile | Single profile, best-effort (QCI 9 / 5QI 9) |
| Radio (4G) | Single Baicells eNodeB |
| Radio (5G) | Single gNodeB (any vendor) |

### Network Modes

The setup wizard prompts you to choose a network mode:

- **4G LTE** — Deploys the EPC core (MME, HSS, SGWC, SGWU, SMF, UPF, PCRF). Base station connects via S1AP on port 36412.
- **5G SA** — Deploys the 5G SA core (AMF, NRF, UDM, UDR, AUSF, PCF, NSSF, SMF, UPF). Base station connects via NGAP on port 38412.

The web UI, API, and all management features work identically in both modes.

### Not Included (Future Phases)
- Multiple QoS profiles
- Multiple eNodeB/gNodeB support
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
├── docker-compose.yml    # 4G stack deployment
└── docker-compose.5g.yml # 5G SA stack deployment
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

Use a vendor-programmed SIM with known Ki and OPc, or a SIM you can program with
matching credentials. Generating new credentials cannot recover the keys on an
existing SIM.

During full setup, choose either existing Ki/OPc values (saved in `.env` as
subscriber defaults) or **generate Ki, source OP, and OPc**. Generation uses secure
random 128-bit Ki and OP values and derives Milenage OPc as
`AES-128(Ki, OP) XOR OP`, following
[3GPP TS 35.206](https://www.etsi.org/deliver/etsi_ts/135200_135299/135206/18.00.00_60/ts_135206v180000p.pdf).
If needed, setup asks permission to install the optional `python3` and
`python3-cryptography` packages on Ubuntu/Debian.

Generated credentials appear **once, directly in the terminal**. The wizard warns
you to save all three securely and requires you to type `COPIED` before continuing.
Blank or other responses repeat only the confirmation prompt; `CANCEL` or end of
input stops setup before configuration is written. After confirmation, **Ki and
OPc are saved in `.env`** as the normal subscriber defaults, so web UI provisioning
works with the generated values. The wizard restricts `.env` and `.env.backup`
permissions to the owner. Network-only reconfiguration preserves these defaults.

**Source OP is never saved.** It remains in the generator process and its one
terminal display; it is never returned to the wizard, put in `.env` or backups,
or passed to Docker. Keep your own secure copy for SIM programming. Terminal
scrollback or session recording may retain the display. Program your SIM with
matching credentials before using the subscriber provisioned by the core.

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
- Python 3.15 recommended (minimum 3.11; CI also covers 3.12)
- Node.js 26
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

The [CI workflow](.github/workflows/ci.yml) checks every pull request and push to
`main`: Python lint and tests on Python 3.11/3.12, Bash syntax and ShellCheck,
Compose configuration validation, and frontend lint and production build.
See [local CI commands](CONTRIBUTING.md#running-ci-checks-locally) to reproduce the checks.

[CodeQL](.github/workflows/codeql.yml) scans Python, JavaScript/TypeScript, and
GitHub Actions. [Dependency audits](.github/workflows/dependencies.yml) run on
pull requests, pushes to `main`, and weekly; Dependabot proposes updates after
its configuration is merged. The API never returns SIM keys; to program SIMs, use
the Ki and OPc saved in `.env` (see [SIM Configuration](#sim-configuration)).

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
