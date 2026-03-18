# Open5G2GO Documentation

Welcome to Open5G2GO – a homelab toolkit for building private 4G LTE and 5G SA cellular networks.

## Project Overview

Open5G2GO is designed to make it simple and accessible to set up your own private 4G LTE or 5G SA cellular network. Perfect for learning, testing, and experimenting with mobile networks in a homelab environment.

## What's Included

- **Open5GS Mobile Core**: A complete 4G EPC or 5G SA core with all essential services
- **Subscriber Management UI**: Web-based interface to manage subscriber accounts and configurations
- **Pre-built Docker Images**: Ready-to-deploy containerized components for quick setup

## Current Scope

The current release supports both 4G LTE and 5G SA deployments:

- **Technology**: 4G LTE + 5G SA (wizard-selectable)
- **Maximum Devices**: 10 connected devices
- **Base Station (4G)**: Single Baicells eNodeB via S1AP
- **Base Station (5G)**: Single gNodeB via NGAP
- **Network Identifier (PLMN)**: Configurable (315-010, 001-01, 999-99, 999-01)

## Get Started

Ready to build your private network? Check out the [Quick Start Guide](./quickstart.md) to get up and running in minutes.

## Documentation

- [Quick Start Guide](./quickstart.md) - Installation and first device setup
- [User Guide](./user-guide.md) - Web UI walkthrough
- [eNodeB Setup](./enodeb-setup.md) - 4G base station configuration
- [gNodeB Setup](./gnodeb-setup.md) - 5G base station configuration
- [Operations Guide](./operations.md) - Upgrades, network changes, and maintenance
- [API Reference](./api-reference.md) - REST API documentation
- [Troubleshooting](./troubleshooting.md) - Common issues and solutions
