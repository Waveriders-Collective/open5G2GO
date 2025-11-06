# openSurfControl - Design Document

**Date:** 2025-10-31
**Version:** 1.0
**Status:** Design Approved

## Executive Summary

openSurfControl is a web-based management platform for private 4G/5G cellular networks, designed to abstract complex 3GPP network engineering into plain-English, intent-based networking for non-network engineers. The platform enables broadcast, event production, and tactical deployment engineers to deploy and operate private LTE/5G networks without cellular networking expertise.

**Target Users:** Broadcast engineers, event production crews, public safety personnel - technical professionals in their own domains but without cellular networking background.

**Core Value Proposition:** Deploy your own private cellular network in 5 minutes using familiar IT/networking concepts, then seamlessly transition to commercial systems using the same interface.

## Project Context

### Problem Statement

Waveriders Collective's 5G2GO rapid deployment system enables professional private network deployment but costs $25,000. To build an early adopter community, we need to enable homeLab experimentation at accessible price points:
- **4G LTE systems:** $1,000 or less
- **5G SA systems:** $3,500 or less

These users need tools that:
1. Abstract 3GPP complexity into domain-familiar concepts
2. Follow Waveriders proven architecture (no-NAT, directly routable devices, standard QoS)
3. Enable lab experimentation that directly translates to field deployment confidence
4. Prepare them for commercial 5G2GO operations

### Strategic Goals

1. **Community Enablement:** Lower barrier to entry for private cellular networking
2. **Architecture Familiarization:** Users learn Waveriders network patterns in their lab
3. **Skill Transfer:** Lab experience → field deployment readiness
4. **Platform Migration:** Smooth path from open-source (Open5GS) → commercial cores (Attocore, Ataya Chorus, Highway 9)
5. **Interface Consistency:** Same UI whether running $1K homeLab or $25K 5G2GO system

## System Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Frontend (React/Vue)                  │
│              Plain English UI, Wizards, Dashboards          │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ HTTPS/REST API
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Python)                   │
│         RESTful API, Auth, Waveriders Schema Manager        │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ Internal API (Unix Socket/HTTP)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│           Core Management Daemon (Python Service)            │
│    CoreAdapter Interface → Core-Specific Implementations     │
│         Config Translation, Monitoring, Subscriber Mgmt      │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ YAML, MongoDB, Systemd, Logs
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Mobile Core (Open5GS / Attocore / etc)         │
│                    4G EPC or 5G SA Network                   │
└─────────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

**1. Unified Configuration Schema**
- Single Waveriders configuration schema abstracts all mobile cores
- Users configure network intent, not 3GPP parameters
- Core Management Daemon translates to core-specific formats
- **Benefit:** Learn once, run anywhere (Open5GS, Attocore, etc.)

**2. Agent/Daemon Pattern**
- Management daemon runs alongside mobile core as separate service
- Provides clean API boundary for all core operations
- Enables safer concurrent access and better error handling
- Easier testing and future core support
- **Benefit:** Cleaner separation, better reliability, simpler testing

**3. Plain English Terminology**
- No MME/AMF, eNodeB/gNB, UE, PLMN, QCI/5QI in user interface
- Use: Core, Radio Sites, Devices, Device Pool, Service Quality
- Map cellular concepts to familiar IT/networking terms
- **Benefit:** Zero cellular knowledge required to operate

**4. Monitoring Evolution Path**
- **MVP:** Log parsing and periodic polling (works with any core, simple)
- **Production:** Prometheus integration with unified metrics schema
- **Rationale:** Fast MVP delivery, professional production monitoring later

## Waveriders Unified Configuration Schema

### Network Configuration Object

```yaml
network_type: "4G_LTE" | "5G_Standalone"

network_identity:
  country_code: "315"              # MCC → country_code
  network_code: "010"              # MNC → network_code
  area_code: 1                     # TAC → area_code
  network_name: "Waveriders Production Net"

ip_addressing:
  architecture: "direct_routing"   # Waveriders standard: no NAT
  core_address: "10.48.0.5"        # Control plane IP (MME/AMF)
  device_pool: "10.48.99.0/24"     # UE IP pool → device pool
  device_gateway: "10.48.99.1"     # Gateway IP (ogstun)
  dns_servers: ["8.8.8.8", "8.8.4.4"]

radio_parameters:
  network_name: "internet"         # APN (4G) / DNN (5G)
  frequency_band: "CBRS_Band48" | "3.5GHz_CBRS" | "custom"

  # 5G Specific (hidden unless 5G_Standalone selected)
  network_slice:
    service_type: 1                # SST → service_type (eMBB)
    slice_id: "000001"             # SD → slice_id

service_quality: "standard" | "high_priority" | "low_latency" | "custom"

template_source: "waveriders_4g_standard" | "waveriders_5g_standard" | "custom"
```

### Device and Group Management

```yaml
device_groups:
  - name: "Uplink_Cameras"                    # User-defined group name
    description: "Camera feeds to cloud"
    qos_policy: "high_priority"
    bandwidth_limit:
      uplink_mbps: 50
      downlink_mbps: 5
    devices:
      - imsi: "315010000000001"
        name: "CAM-01"
        ip: "10.48.99.10"
      - imsi: "315010000000002"
        name: "CAM-02"
        ip: "10.48.99.11"

  - name: "Crew_Devices"
    description: "Tablets and communications"
    qos_policy: "standard"
    bandwidth_limit:
      uplink_mbps: 10
      downlink_mbps: 10
    devices: [...]

qos_policies:
  high_priority:
    description: "Time-sensitive production traffic"
    priority_level: 1
    guaranteed_bandwidth: true
    # Backend maps to: QCI 3 (4G) or 5QI 3 (5G), ARP priority 1

  standard:
    description: "Normal internet access"
    priority_level: 5
    guaranteed_bandwidth: false
    # Backend maps to: QCI 9 (4G) or 5QI 9 (5G), ARP priority 10

  low_latency:
    description: "Real-time coordination"
    priority_level: 2
    guaranteed_bandwidth: true
    # Backend maps to: QCI 1 (4G) or 5QI 1 (5G), ARP priority 2
```

### Key Principles

1. **Plain English Naming:** No 3GPP jargon in configuration
2. **Waveriders Opinions Baked In:** Defaults to proven architecture patterns
3. **Hide Complexity:** User sets "4G_LTE", system configures MME/HSS/SGW/PGW
4. **Template Inheritance:** Load proven configs, customize if needed
5. **Unified Groups/QoS:** Same interface whether 4G or 5G backend

## Core Management Daemon

### Purpose

The daemon is the abstraction boundary - it translates Waveriders intent into core-specific reality.

### Architecture

```
opensurfcontrol-daemon/
├── core/
│   ├── abstract.py              # CoreAdapter abstract base class
│   ├── open5gs.py               # Open5GS implementation
│   ├── attocore.py              # Attocore implementation (future)
│   └── factory.py               # Core detection and adapter selection
│
├── services/
│   ├── config_manager.py        # Waveriders schema → core configs
│   ├── subscriber_manager.py    # Device/group/QoS operations
│   ├── monitor.py               # Health, connections, throughput
│   └── template_engine.py       # Template processing
│
├── api/
│   ├── server.py                # Internal API (Unix socket or localhost)
│   └── schemas.py               # Pydantic models for API contracts
│
└── daemon.py                    # Main service entry point
```

### CoreAdapter Interface

Every mobile core implementation must provide:

```python
class CoreAdapter(ABC):
    """Abstract interface for mobile core management"""

    @abstractmethod
    def apply_network_config(self, config: WaveridersConfig) -> Result:
        """Deploy network configuration to core"""
        pass

    @abstractmethod
    def get_core_status(self) -> CoreStatus:
        """Return: healthy/degraded/down + component details"""
        pass

    @abstractmethod
    def get_connected_radios(self) -> List[RadioSite]:
        """Return: connected eNB/gNB with IPs, names, status"""
        pass

    @abstractmethod
    def get_connected_devices(self) -> List[Device]:
        """Return: active devices with IP, throughput, group"""
        pass

    @abstractmethod
    def add_device(self, imsi: str, device_config: DeviceConfig) -> Result:
        """Provision new device with QoS policy"""
        pass

    @abstractmethod
    def update_device_qos(self, imsi: str, qos_policy: QoSPolicy) -> Result:
        """Change device QoS (e.g., group move)"""
        pass

    @abstractmethod
    def remove_device(self, imsi: str) -> Result:
        """Deprovision device"""
        pass
```

### Open5GS Implementation

The Open5GS adapter interacts with:
- **YAML configs** (`/etc/open5gs/*.yaml`) - Network configuration
- **MongoDB** (`open5gs` database) - Subscriber data
- **Systemd services** - Service lifecycle management
- **Log files** (`/var/log/open5gs/*.log`) - Event monitoring

**Example Implementation:**

```python
class Open5GSAdapter(CoreAdapter):
    def __init__(self):
        self.config_path = "/etc/open5gs"
        self.mongo_client = MongoClient("mongodb://localhost:27017")
        self.db = self.mongo_client.open5gs

    def apply_network_config(self, config: WaveridersConfig):
        # Backup existing configs
        self._backup_configs()

        # Generate YAML configs from Waveriders schema
        if config.network_type == "4G_LTE":
            self._generate_epc_configs(config)
        else:
            self._generate_5g_configs(config)

        # Validate generated configs
        self._validate_configs()

        # Restart services in correct order
        self._restart_services()

        return Result(success=True)

    def get_connected_devices(self):
        # Parse MME/AMF logs for active sessions
        # Query MongoDB for subscriber data
        # Get interface stats for throughput
        devices = []

        for line in self._tail_log("/var/log/open5gs/mme.log", n=1000):
            if "Attach complete" in line:
                device = self._parse_attach_event(line)
                devices.append(device)

        return devices

    def add_device(self, imsi: str, device_config: DeviceConfig):
        # Translate Waveriders QoS policy to Open5GS subscriber entry
        subscriber = {
            "imsi": imsi,
            "security": {
                "k": device_config.k,
                "opc": device_config.opc
            },
            "ambr": {
                "uplink": device_config.qos_policy.uplink_mbps * 1000000,
                "downlink": device_config.qos_policy.downlink_mbps * 1000000
            },
            "slice": [{
                "sst": 1,
                "default_indicator": True,
                "session": [{
                    "name": "internet",
                    "type": "IPv4",
                    "qos": {
                        "index": self._map_qos_to_qci(device_config.qos_policy),
                        "arp": {
                            "priority_level": device_config.qos_policy.priority_level
                        }
                    }
                }]
            }]
        }

        self.db.subscribers.insert_one(subscriber)
        return Result(success=True)
```

### Daemon API (Internal)

The daemon exposes an internal API for the FastAPI backend to consume:

**Transport:** Unix socket `/var/run/opensurfcontrol/daemon.sock` or `localhost:5001`

**Endpoints:**
```
POST   /config/apply          - Apply network configuration
GET    /status/core           - Core health status
GET    /status/radios         - Connected radio sites
GET    /status/devices        - Connected devices with stats
POST   /devices/add           - Provision device
PUT    /devices/{imsi}/qos    - Update device QoS
DELETE /devices/{imsi}        - Remove device
POST   /groups/create         - Create device group
PUT    /groups/{id}/members   - Bulk group operations
```

### Service Management

```ini
# /etc/systemd/system/opensurfcontrol-daemon.service
[Unit]
Description=openSurfControl Core Management Daemon
After=network.target mongodb.service open5gs-mmed.service

[Service]
Type=simple
User=opensurfcontrol
ExecStart=/usr/bin/opensurfcontrol-daemon
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## FastAPI Backend

### Structure

```
opensurfcontrol-api/
├── api/
│   ├── main.py                    # FastAPI app entry point
│   ├── routes/
│   │   ├── config.py              # Network configuration endpoints
│   │   ├── devices.py             # Device/group management
│   │   ├── monitoring.py          # Status/metrics endpoints
│   │   └── templates.py           # Template management
│   ├── models/
│   │   ├── waveriders_schema.py   # Pydantic models for unified schema
│   │   └── responses.py           # API response models
│   └── dependencies.py             # Auth, daemon client
│
├── services/
│   ├── daemon_client.py           # Client for daemon API
│   └── auth.py                    # User authentication
│
└── static/                         # Built frontend files
```

### Key API Endpoints

```python
# Configuration
POST   /api/v1/config/wizard        # Step-by-step configuration
POST   /api/v1/config/template      # Deploy from template
GET    /api/v1/config/current       # Current network config
PUT    /api/v1/config/update        # Update configuration

# Templates
GET    /api/v1/templates            # List available templates
POST   /api/v1/templates            # Save custom template
GET    /api/v1/templates/{id}       # Get template details

# Monitoring (Plain English)
GET    /api/v1/status/core          # Core: Healthy/Degraded/Down
GET    /api/v1/status/radios        # Connected radio sites
GET    /api/v1/status/devices       # Connected devices with throughput
GET    /api/v1/metrics/summary      # Overall network stats

# Device/Group Management
GET    /api/v1/devices              # All devices
POST   /api/v1/devices              # Add device
PUT    /api/v1/devices/{imsi}       # Update device
DELETE /api/v1/devices/{imsi}       # Remove device

GET    /api/v1/groups               # All groups
POST   /api/v1/groups               # Create group
PUT    /api/v1/groups/{id}/members  # Bulk add/remove devices
PUT    /api/v1/groups/{id}/qos      # Change group QoS policy

# QoS Management
GET    /api/v1/qos/policies         # Available QoS policies
POST   /api/v1/qos/policies         # Create custom policy
```

## Web Frontend

### Technology Choice

**Recommendation:** React with TypeScript
- Large ecosystem, mature component libraries
- Good tooling for plain-English dashboards
- Easy to find developers for future contributions

**Alternative:** Vue.js 3
- Simpler learning curve for contributors
- Excellent documentation
- Good component ecosystem

### Structure

```
frontend/
├── src/
│   ├── pages/
│   │   ├── Dashboard.tsx          # Main status overview
│   │   ├── ConfigWizard.tsx       # Step-by-step network setup
│   │   ├── Templates.tsx          # Template browser/editor
│   │   ├── Devices.tsx            # Device/group management
│   │   └── Monitoring.tsx         # Detailed metrics
│   │
│   ├── components/
│   │   ├── StatusCard.tsx         # Core/Radio/Device status cards
│   │   ├── DeviceTable.tsx        # Device list with throughput
│   │   ├── GroupManager.tsx       # Drag-drop group assignment
│   │   ├── QoSEditor.tsx          # Simple QoS policy editor
│   │   └── ThroughputChart.tsx    # Real-time bandwidth graphs
│   │
│   └── services/
│       └── api.ts                 # API client wrapper
```

### User Experience Flow

**First-Time Setup (Configuration Wizard):**

```
Step 1: Welcome
  "Let's set up your private network"

Step 2: Network Type
  ○ 4G LTE - Mature technology, lower cost ($1K)
  ○ 5G Standalone - Next generation, higher performance ($3.5K)

Step 3: Network Identity
  Country Code: [315] (USA)
  Network Code: [010] (Your private network)
  Area Code: [1]
  Network Name: [Waveriders Network]

Step 4: IP Addressing
  Core Address: [10.48.0.5]
  Device Pool: [10.48.99.0/24]
  Device Gateway: [10.48.99.1]
  DNS Servers: [8.8.8.8, 8.8.4.4]

  ⓘ Your devices will be directly accessible on your LAN
  ⓘ Add this static route to your gateway: 10.48.99.0/24 via 10.48.0.5

Step 5: Radio Parameters
  Network Name: [internet]
  Frequency Band: [CBRS Band 48 ▼]

Step 6: Review Configuration
  ✓ 4G LTE Network
  ✓ Country: USA (315), Network: 010
  ✓ Core at 10.48.0.5
  ✓ Devices get IPs from 10.48.99.0/24
  ✓ CBRS Band 48 operation

  [Deploy Network]

Step 7: Deploying...
  ⏳ Configuring core services...
  ⏳ Starting authentication system...
  ⏳ Starting 4G EPC...
  ✓ Your network is ready!

  Next: Add devices to start connecting
```

**Dashboard View:**

```
┌───────────────────────────────────────────────────────────────┐
│ ⚡ Waveriders Private Network          Status: Healthy ✓      │
│                                         [Settings] [Help]      │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │    CORE     │  │ RADIO SITES │  │   DEVICES   │          │
│  │             │  │             │  │             │          │
│  │  All Up ✓   │  │ 2 Connected │  │  8 Active   │          │
│  │  4G EPC     │  │ Camera-1    │  │  3 Groups   │          │
│  │  Auth ✓     │  │ Booth-2     │  │             │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│                                                                │
├───────────────────────────────────────────────────────────────┤
│  CONNECTED DEVICES                              BANDWIDTH     │
│                                                                │
│  ▼ Uplink_Cameras (3 devices)            ↑ 125  ↓ 8 Mbps    │
│     CAM-01     10.48.99.10  Online       ↑ 45   ↓ 2         │
│     CAM-02     10.48.99.11  Online       ↑ 42   ↓ 3         │
│     CAM-03     10.48.99.12  Online       ↑ 38   ↓ 3         │
│     [High Priority QoS]                                       │
│                                                                │
│  ▼ Crew_Devices (2 devices)              ↑ 3    ↓ 10 Mbps   │
│     TABLET-1   10.48.99.20  Online       ↑ 2    ↓ 6         │
│     TABLET-2   10.48.99.21  Online       ↑ 1    ↓ 4         │
│     [Standard QoS]                                            │
│                                                                │
│  ▼ Production (3 devices)                ↑ 5    ↓ 15 Mbps   │
│     [...collapsed...]                                         │
│                                                                │
│  [+ Add Device]  [Create Group]                               │
└───────────────────────────────────────────────────────────────┘
```

**Device Management:**

- **Add Device:** Modal with IMSI, Name, Assign to Group, K/OPc keys
- **Drag-and-Drop:** Move devices between groups visually
- **Bulk Operations:** "Select all devices with IMSI prefix 315010... → Move to Group"
- **Device Details:** Click device → View connection history, edit name, change group

**Group Management:**

- **Create Group:** Name, Description, QoS Policy selector
- **QoS Policies:**
  - High Priority (guaranteed bandwidth, time-sensitive)
  - Standard (best effort internet)
  - Low Latency (real-time coordination)
  - Custom (advanced users can tune)
- **Custom QoS Editor:**
  - Uplink Speed: [50 Mbps] slider
  - Downlink Speed: [10 Mbps] slider
  - Priority Level: [1-10] slider
  - Guaranteed Bandwidth: [✓] checkbox
  - Preview: "This guarantees 50 Mbps uplink for all devices in this group"

## Deployment and Packaging

### Community Distribution: Waveriders Private Network Appliance

**VM Image:** `Waveriders-PrivateNetwork-v1.0.qcow2`

**Base System:**
- Ubuntu 22.04 LTS
- Open5GS 2.7.6+ (pre-configured for 4G and 5G)
- MongoDB 6.0+
- Python 3.11+
- Nginx (reverse proxy)

**Pre-installed Software:**
- opensurfcontrol-daemon (systemd service)
- opensurfcontrol-api (FastAPI backend, systemd service)
- opensurfcontrol-web (React frontend, served by nginx)

**Pre-loaded Templates:**
- `waveriders_4g_standard.json` - CBRS Band 48, PLMN 315-010
- `waveriders_5g_standard.json` - Test network PLMN 999-773

**Default Configuration:**
- Web UI: http://<vm-ip>:8048
- Default credentials: admin / waveriders (force change on first login)
- Open5GS services installed but not started until wizard completes

### Quick Start Experience

**For Community Users:**

1. Download `Waveriders-PrivateNetwork-v1.0.qcow2` from waveriders.io/community
2. Import to Proxmox:
   ```bash
   qm importdisk <vmid> Waveriders-PrivateNetwork-v1.0.qcow2 <storage>
   qm set <vmid> --scsi0 <storage>:vm-<vmid>-disk-0
   qm set <vmid> --boot c --bootdisk scsi0
   qm set <vmid> --net0 virtio,bridge=vmbr0
   ```
3. Configure VM: 2 vCPU, 4GB RAM, attach network bridge
4. Start VM
5. Access http://<vm-ip>:8048
6. Complete 5-minute configuration wizard
7. Start connecting devices

**Network Requirements (clearly documented):**
- VM needs network bridge connected to LAN (vmbr0)
- Assign static IP or DHCP reservation for core_address
- Configure static route on LAN gateway:
  ```bash
  ip route add 10.48.99.0/24 via <core_address>
  ```
- Open firewall ports:
  - 8048/tcp - Web UI
  - 36412/sctp - 4G eNodeB S1AP
  - 38412/sctp - 5G gNB NGAP
  - 2152/udp - GTP-U user plane

### File System Layout

```
/opt/opensurfcontrol/
├── daemon/                      # Core management daemon
├── api/                         # FastAPI backend
├── web/                         # Frontend static files
├── templates/                   # Configuration templates
│   ├── waveriders_4g_standard.json
│   ├── waveriders_5g_standard.json
│   └── community/               # User-shared templates
├── configs/                     # Active Waveriders configs (JSON)
│   └── current.json
└── logs/                        # Application logs
    ├── daemon.log
    └── api.log

/etc/open5gs/                    # Generated configs (don't edit!)
├── *.yaml                       # Generated from openSurfControl
└── *.yaml.backup-*              # Automatic backups before changes

/var/lib/opensurfcontrol/
└── database.sqlite              # openSurfControl state
    ├── users                    # User accounts
    ├── templates                # Custom templates
    └── history                  # Configuration history
```

### Installation Package (DIY Builders)

For users installing on existing Ubuntu systems:

```bash
# Add Waveriders repository
sudo add-apt-repository ppa:waveriders/opensurfcontrol
sudo apt update

# Install openSurfControl
sudo apt install opensurfcontrol

# Run interactive setup
sudo opensurfcontrol-setup
# → Configures services
# → Sets up firewall rules
# → Generates admin credentials
# → Optionally installs Open5GS if not present

# Start services
sudo systemctl enable --now opensurfcontrol-daemon
sudo systemctl enable --now opensurfcontrol-api

# Access Web UI
http://localhost:8048
```

### Updates and Versioning

- **Semantic Versioning:** v1.0.0, v1.1.0, v2.0.0
- **Update Mechanism:** `apt update && apt upgrade opensurfcontrol`
- **Config Migration:** Automatic schema migrations with rollback support
- **Rollback Safety:** Previous configs backed up automatically
- **Release Channels:**
  - Stable (community)
  - Beta (early adopters)
  - Nightly (developers)

### Documentation Package

**Quick Start Guide (PDF, 10 pages):**
- Hardware requirements and compatibility
- VM installation steps
- Network configuration requirements
- Wizard walkthrough
- Adding first device
- Troubleshooting common issues

**Video Walkthrough (15 minutes):**
- Platform overview
- Installation demonstration
- Configuration wizard walkthrough
- Adding devices and creating groups
- Monitoring and management

**Hardware Compatibility List:**
- Tested eNodeB/gNB models
- Recommended SIM/USIM cards
- Network interface requirements
- Proxmox versions tested

**Community Resources:**
- GitHub repository
- Discussion forum
- Template sharing portal
- Video tutorial library

## Monitoring Strategy

### MVP Approach: Log Parsing + Periodic Polling

**Rationale:** Works with any mobile core, simple to implement, gets us to market fast.

**Implementation:**
- Parse Open5GS log files for events:
  - eNodeB/gNB connections (S1AP/NGAP setup)
  - Device attachments/detachments (EMM/NAS)
  - Session establishments (bearer setup)
- Poll system state every 5-10 seconds:
  - Active sessions from MongoDB
  - Network interface throughput (ogstun)
  - Service status (systemd)
- Cache results for dashboard responsiveness

**Latency:** 5-30 seconds (acceptable for MVP)

**Limitations:**
- May miss transient events
- Limited historical data
- Manual log parsing per core type

### Production Approach: Prometheus Integration

**Evolution Path:**
- Open5GS exposes Prometheus metrics (MME:9090, SMF:9090, UPF:9090)
- Define Waveriders unified metrics schema
- Each CoreAdapter implements Prometheus exporter or transformation
- openSurfControl queries unified schema, not core-specific metrics

**Benefits:**
- Professional-grade monitoring
- Rich historical data
- Alerting capabilities
- Multi-core support through metric transformation

**Timeline:** Post-MVP, add after log parsing proves the concept

### Monitoring Terminology Translation

**3GPP Terms → Plain English:**

| 3GPP Term | Plain English |
|-----------|---------------|
| MME/AMF | Core - Control |
| SGW/UPF | Core - User Plane |
| HSS/UDM | Core - Authentication |
| eNodeB/gNB | Radio Site |
| UE | Device |
| Attach/Registration | Connection |
| Bearer/Session | Data Connection |
| QCI/5QI | Service Quality |
| AMBR | Bandwidth Limit |
| PLMN | Network Identity |
| TAC | Area Code |

## Security Considerations

### Authentication and Authorization

- **Default Credentials:** admin / waveriders (force change on first login)
- **User Roles:**
  - Admin: Full access (config, devices, monitoring)
  - Operator: Device management and monitoring only
  - Viewer: Read-only monitoring access
- **Session Management:** JWT tokens with refresh, 24-hour expiry
- **API Security:** All API endpoints require authentication

### Network Security

- **Web UI:** HTTPS with self-signed cert (let user provide own cert)
- **Daemon API:** Unix socket (localhost only) or mutual TLS
- **MongoDB:** Localhost only, authentication enabled
- **Firewall:** Only expose necessary ports (8048, 36412, 38412, 2152)

### Configuration Safety

- **Automatic Backups:** Config backed up before every change
- **Validation:** All configs validated before applying to core
- **Rollback:** One-click rollback to previous working config
- **Change History:** Audit log of all configuration changes

## Implementation Phases

### Phase 1: MVP - Open5GS Support (8-12 weeks)

**Deliverables:**
- Core Management Daemon with Open5GSAdapter
- FastAPI backend with core endpoints
- Basic web UI (wizard, dashboard, device management)
- Log-based monitoring
- Waveriders 4G/5G templates
- VM image for Proxmox
- Quick start documentation

**Success Criteria:**
- Deploy network in < 5 minutes via wizard
- Add/remove devices through UI
- View connected radios and devices
- Create and manage groups with QoS
- No 3GPP terminology in UI

### Phase 2: Community Features (4-6 weeks)

**Deliverables:**
- Template import/export
- Community template sharing
- Custom QoS policy editor
- Enhanced monitoring dashboards
- Video tutorials
- Community forum launch

**Success Criteria:**
- Users can share templates
- Custom QoS policies work correctly
- 90% of support questions answered in docs/videos

### Phase 3: Prometheus Monitoring (4-6 weeks)

**Deliverables:**
- Prometheus metrics integration
- Historical data and trending
- Alerting system
- Performance dashboards
- Capacity planning tools

**Success Criteria:**
- Real-time metrics (< 2 second latency)
- Historical data retention (30 days)
- Alert on core/radio failures

### Phase 4: Commercial Core Support (6-8 weeks each)

**Deliverables per Core:**
- CoreAdapter implementation (Attocore, Ataya Chorus, Highway 9)
- Core-specific config translation
- Monitoring integration
- Testing and validation

**Success Criteria:**
- Same UI experience across all cores
- Config portability between cores
- Feature parity where possible

## Success Metrics

### Community Adoption
- 100 active deployments in first 6 months
- 50% of users complete wizard successfully
- Template library reaches 20+ community templates
- Forum activity: 10+ posts/week

### User Experience
- Time to first device connection: < 10 minutes
- User satisfaction: 4.5+ / 5 stars
- Support ticket volume: < 5/week
- Documentation clarity: 90% can self-service

### Technical Performance
- Core management daemon uptime: 99.9%
- API response time: < 500ms p95
- Monitoring latency: < 30s (MVP), < 2s (Prometheus)
- Config apply success rate: > 95%

### Platform Growth
- Attocore support: 3 months after MVP
- Secondary core support: 6 months after MVP
- Commercial customer conversion: 10% of community users

## Risk Mitigation

### Technical Risks

**Risk:** Open5GS config format changes break adapter
**Mitigation:** Version-specific adapters, config validation, automated testing

**Risk:** Log parsing misses events or produces incorrect data
**Mitigation:** Extensive testing, fallback to MongoDB queries, Prometheus roadmap

**Risk:** Multi-core abstraction proves too limiting
**Mitigation:** Core-specific advanced settings page, escape hatch to native config

### Adoption Risks

**Risk:** Users find UI too simplified, want more control
**Mitigation:** Advanced mode with more knobs, template customization

**Risk:** Hardware compatibility issues frustrate users
**Mitigation:** Comprehensive compatibility list, pre-flight checks, diagnostic tools

**Risk:** Community doesn't convert to commercial customers
**Mitigation:** Clear value proposition for 5G2GO, migration incentives, success stories

## Future Enhancements

### Post-MVP Features
- Multi-site federation (manage multiple deployments)
- VPN integration for device backhaul
- Roaming between sites
- Advanced traffic shaping and policy routing
- Integration with existing network monitoring (Zabbix, Nagios)
- Mobile app for field management
- Automated compliance reporting
- Backup/restore functionality
- High availability configuration

### Platform Extensions
- Kubernetes deployment option
- Cloud-hosted control plane (self-hosted core)
- SaaS offering for small deployments
- Marketplace for third-party integrations
- Professional services portal

## Conclusion

openSurfControl democratizes private cellular networking by abstracting 3GPP complexity into intent-based, plain-English configuration and management. The unified Waveriders schema provides a consistent interface across open-source and commercial mobile cores, enabling community members to build lab expertise that directly translates to field deployment confidence.

The platform's agent-based architecture cleanly separates concerns: users express intent through the web UI, the FastAPI backend manages the unified schema, and core-specific adapters translate to each mobile core's native configuration. This design enables rapid addition of new core support while maintaining interface consistency.

By lowering the barrier to entry from $25,000 commercial systems to $1,000-$3,500 homeLab deployments, openSurfControl cultivates an early adopter community that will drive innovation in private cellular applications across broadcast, events, public safety, and tactical deployments.

---

**Next Steps:**
1. Review and approve design
2. Set up development repository
3. Create implementation plan (superpowers:writing-plans)
4. Begin Phase 1: MVP development
