# Open5G2GO Implementation Plan

**Date:** 2025-12-27
**Status:** Draft - Pending Approval
**Version:** 1.0

---

## Executive Summary

Open5G2GO is a homelab toolkit for private 4G cellular networks, combining:
- **Open5GS** (open-source mobile core) via docker_open5gs
- **openSurfControl** (forked from production surfcontrol-mcp)
- **Waveriders-tested configurations** for broadcast, CCTV, and event production

This plan delivers an MVP that enables a 60-minute deployment for homelab users.

---

## Project Goals

1. **Fork surfcontrol-mcp** as a **private repository**: **open5g2go** (invite-only beta → public release)
2. **Replace Attocore adapter** with Open5GS MongoDB adapter
3. **Single docker-compose deployment** combining Open5GS core + management UI
4. **Preserve UI/UX consistency** with Attocore version for seamless migration path
5. **Enable community experimentation** at $1,000 price point (vs $25K 5G2GO)

---

## MVP Scope

### Included

| Feature | Specification |
|---------|---------------|
| Network Type | 4G LTE only |
| Mobile Core | Open5GS (docker_open5gs) |
| PLMN | 315-010 (US private network) |
| Devices | 10 max, static IP assignment |
| UE IP Pool | 10.48.99.0/24 |
| QoS Profile | Single profile, best-effort (QCI 9) |
| Radio | Single Baicells eNodeB |
| Deployment | Single docker-compose.yml |
| Management | Web UI + MCP tools |

### Not Included (Future Phases)

- 5G SA support
- Multiple QoS profiles (Video, CCTV, POS)
- Multiple eNodeB support
- TLS/HTTPS (lab environment)
- Advanced authentication
- Prometheus monitoring

---

## Test Environment

| Resource | Details |
|----------|---------|
| Docker Host | 10.48.0.110 (single ethernet interface) |
| eNodeBs | 2x Baicells (use 1 for MVP validation) |
| UE Pool | 10.48.99.0/24 (direct routing) |
| S1AP Port | 36412/SCTP |
| GTP-U Port | 2152/UDP |

---

## Architecture

### Source: surfcontrol-mcp (Production Attocore)

```
surfcontrol-mcp/
├── surfcontrol_mcp/          # MCP server + 8 tools
│   ├── server.py             # MCP tools (SSH to Attocore CLI)
│   ├── ssh_client.py         # Paramiko SSH adapter
│   ├── parsers.py            # CLI output parsing
│   └── constants.py          # Network standards
├── web_backend/              # FastAPI REST API
│   ├── api/routes.py         # REST endpoints
│   └── services/             # Service layer
├── web_frontend/             # React TypeScript SPA
└── docker-compose.yml        # Multi-container deployment
```

### Target: open5g2go (Open5GS Fork)

```
open5g2go/
├── opensurfcontrol/          # MCP server + 8 tools (MODIFIED)
│   ├── server.py             # MCP tools (MongoDB adapter)
│   ├── mongodb_client.py     # NEW: PyMongo adapter
│   ├── parsers.py            # Response parsing (simplified)
│   └── constants.py          # Open5GS standards (315-010, etc.)
├── web_backend/              # FastAPI REST API (MINIMAL CHANGES)
│   ├── api/routes.py         # Same endpoints
│   └── services/             # Same service layer
├── web_frontend/             # React TypeScript SPA (MINIMAL CHANGES)
├── open5gs/                  # NEW: Open5GS configs
│   ├── config/               # Generated YAML configs
│   └── Dockerfile            # Open5GS container
└── docker-compose.yml        # Combined stack
```

### Key Architecture Changes

| Component | surfcontrol-mcp | open5g2go |
|-----------|-----------------|-----------|
| Core Adapter | SSH → Attocore CLI | MongoDB → Open5GS DB |
| Config Format | N/A (Attocore manages) | YAML generation |
| Subscriber DB | Attocore internal | MongoDB (open5gs db) |
| Service Restart | N/A | docker-compose restart |
| Network Config | CLI commands | YAML + env vars |

---

## Docker Compose Design

### Services

```yaml
services:
  mongodb:
    image: mongo:6.0
    volumes:
      - mongodb_data:/data/db
    networks:
      - open5g2go

  open5gs:
    build: ./open5gs
    depends_on:
      - mongodb
    ports:
      - "36412:36412/sctp"    # S1AP (eNodeB)
      - "2152:2152/udp"       # GTP-U
    volumes:
      - ./open5gs/config:/etc/open5gs
    networks:
      - open5g2go

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    depends_on:
      - mongodb
      - open5gs
    environment:
      - MONGODB_URI=mongodb://mongodb:27017/open5gs
      - OPEN5GS_CONFIG_PATH=/etc/open5gs
    networks:
      - open5g2go

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    depends_on:
      - backend
    ports:
      - "8080:80"
    networks:
      - open5g2go

networks:
  open5g2go:
    driver: bridge

volumes:
  mongodb_data:
```

### Network Topology

```
Lab Network (10.48.0.x)
│
├── Baicells eNodeB ──────────────────┐
│   S1AP target: 10.48.0.110:36412    │
│                                      │
└── Docker Host (10.48.0.110) ────────┤
    │                                  │
    └── Docker Network (172.26.0.0/16) │
        │                              │
        ├── mongodb (172.26.0.2)       │
        ├── open5gs (172.26.0.3) ◄─────┘
        │   └── S1AP: 36412/sctp
        │   └── GTP-U: 2152/udp
        ├── backend (172.26.0.4:8000)
        └── frontend (172.26.0.5:80) → exposed :8080
```

---

## Open5GS Adapter Design

### MongoDB Client (replaces SSH)

```python
# opensurfcontrol/mongodb_client.py

from pymongo import MongoClient
from typing import List, Optional
import os

class Open5GSClient:
    """MongoDB adapter for Open5GS subscriber management."""

    def __init__(self):
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.client = MongoClient(uri)
        self.db = self.client.open5gs
        self.subscribers = self.db.subscribers

    def list_subscribers(self) -> List[dict]:
        """List all provisioned subscribers."""
        return list(self.subscribers.find({}, {"_id": 0}))

    def get_subscriber(self, imsi: str) -> Optional[dict]:
        """Get subscriber by IMSI."""
        return self.subscribers.find_one({"imsi": imsi}, {"_id": 0})

    def add_subscriber(
        self,
        imsi: str,
        k: str,
        opc: str,
        apn: str = "internet",
        ip: str = None,
        ambr_ul: int = 50000000,  # 50 Mbps
        ambr_dl: int = 100000000  # 100 Mbps
    ) -> dict:
        """Add new subscriber with QoS settings."""
        subscriber = {
            "imsi": imsi,
            "security": {
                "k": k,
                "amf": "8000",
                "op": None,
                "opc": opc
            },
            "ambr": {
                "uplink": {"value": ambr_ul // 1000, "unit": 0},
                "downlink": {"value": ambr_dl // 1000, "unit": 0}
            },
            "slice": [{
                "sst": 1,
                "default_indicator": True,
                "session": [{
                    "name": apn,
                    "type": 3,  # IPv4
                    "qos": {
                        "index": 9,  # QCI 9 (best effort)
                        "arp": {
                            "priority_level": 8,
                            "pre_emption_capability": 1,
                            "pre_emption_vulnerability": 1
                        }
                    },
                    "ambr": {
                        "uplink": {"value": ambr_ul // 1000, "unit": 0},
                        "downlink": {"value": ambr_dl // 1000, "unit": 0}
                    },
                    "ue": {
                        "addr": ip
                    } if ip else {}
                }]
            }]
        }
        self.subscribers.update_one(
            {"imsi": imsi},
            {"$set": subscriber},
            upsert=True
        )
        return subscriber

    def update_subscriber(self, imsi: str, **updates) -> bool:
        """Update subscriber fields."""
        result = self.subscribers.update_one(
            {"imsi": imsi},
            {"$set": updates}
        )
        return result.modified_count > 0

    def delete_subscriber(self, imsi: str) -> bool:
        """Remove subscriber."""
        result = self.subscribers.delete_one({"imsi": imsi})
        return result.deleted_count > 0

    def get_system_status(self) -> dict:
        """Get subscriber counts."""
        total = self.subscribers.count_documents({})
        return {
            "total_subscribers": total,
            "core_status": "healthy"  # TODO: Add actual health checks
        }
```

### MCP Tool Updates

| Tool | surfcontrol-mcp | open5g2go |
|------|-----------------|-----------|
| list_subscribers | SSH listues | MongoDB find() |
| get_subscriber | SSH getue --imsi | MongoDB find_one() |
| add_subscriber | SSH createue | MongoDB upsert |
| update_subscriber | SSH createue (upsert) | MongoDB update_one |
| delete_subscriber | SSH deleteue | MongoDB delete_one |
| get_system_status | SSH countuesubs | MongoDB count + health |
| get_active_connections | SSH listuestate | Log parsing (Phase 2) |
| get_network_config | SSH getshareddata | Read YAML configs |

---

## Implementation Phases

### Phase 1: Repository Setup (2 days)

**Goal:** Create private fork with clean structure

**Tasks:**
1. Create private repo `open5g2go` under Waveriders-Collective
2. Copy surfcontrol-mcp codebase (not GitHub fork - avoids public fork chain)
3. Rename directories (surfcontrol_mcp → opensurfcontrol)
4. Update package names and imports
5. Remove Attocore-specific code (ssh_client.py, gnodeb_*)
6. Update constants.py for Open5GS defaults
7. Update README (mark as private beta)

**Deliverables:**
- [ ] Private GitHub repository
- [ ] Clean directory structure
- [ ] Updated package configuration (pyproject.toml, package.json)

### Phase 2: MongoDB Adapter (3 days)

**Goal:** Replace SSH adapter with MongoDB client

**Tasks:**
1. Create mongodb_client.py with Open5GSClient class
2. Update server.py MCP tools to use MongoDB
3. Update parsers.py for Open5GS document format
4. Add connection health checks
5. Unit tests for CRUD operations

**Deliverables:**
- [ ] Working mongodb_client.py
- [ ] Updated MCP tools (8 tools)
- [ ] Unit tests passing

### Phase 3: Docker Integration (3 days)

**Goal:** Single docker-compose deployment

**Tasks:**
1. Create docker-compose.yml with all services
2. Create Open5GS Dockerfile with 4G EPC config
3. Update backend Dockerfile (remove SSH, add pymongo)
4. Configure environment variables
5. Add health checks for all services
6. Test full stack startup

**Deliverables:**
- [ ] docker-compose.yml
- [ ] All Dockerfiles
- [ ] Successful `docker-compose up`

### Phase 4: Web UI Updates (2 days)

**Goal:** Adapt frontend for Open5GS context

**Tasks:**
1. Update branding (openSurfControl for Open5GS)
2. Remove gNodeB-specific UI (4G only for MVP)
3. Update API service for Open5GS responses
4. Simplify subscriber form (single APN, static IP)
5. Update status dashboard

**Deliverables:**
- [ ] Updated React frontend
- [ ] Working subscriber management UI
- [ ] Status dashboard showing Open5GS health

### Phase 5: Integration Testing (3 days)

**Goal:** Validate with real hardware

**Tasks:**
1. Deploy to test host (10.48.0.110)
2. Configure Baicells eNodeB S1AP target
3. Provision test subscriber via UI
4. Attach real UE and verify connectivity
5. Test CRUD operations end-to-end
6. Document any issues and fixes

**Deliverables:**
- [ ] Successful eNodeB S1AP connection
- [ ] UE attachment and IP assignment
- [ ] End-to-end data connectivity
- [ ] Integration test report

### Phase 6: Documentation & Private Beta (2 days)

**Goal:** Prepare for invite-only beta release

**Tasks:**
1. Write deployment guide (Quick Start)
2. Document eNodeB configuration
3. Create troubleshooting guide
4. Invite initial beta testers (5-10 users)
5. Tag v0.1.0-beta release

**Deliverables:**
- [ ] README with quick start
- [ ] Deployment documentation
- [ ] GitHub release v0.1.0-beta (private repo)

---

## Effort Summary

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| 1. Repository Setup | 2 days | None |
| 2. MongoDB Adapter | 3 days | Phase 1 |
| 3. Docker Integration | 3 days | Phase 2 |
| 4. Web UI Updates | 2 days | Phase 2 |
| 5. Integration Testing | 3 days | Phases 3, 4 |
| 6. Documentation | 2 days | Phase 5 |
| **Total** | **15 days** | |

---

## Success Criteria

### Functional

- [ ] Deploy from fresh clone in < 15 minutes
- [ ] eNodeB connects via S1AP and registers
- [ ] Add subscriber via Web UI
- [ ] UE attaches and gets IP from 10.48.99.0/24 pool
- [ ] UE has internet connectivity (ping 8.8.8.8)
- [ ] Delete subscriber via Web UI
- [ ] All 8 MCP tools functional

### Non-Functional

- [ ] Docker-compose starts all services in < 90 seconds
- [ ] Web UI responsive on mobile
- [ ] Clear error messages in logs
- [ ] Data persists across container restart

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Open5GS config complexity | High | Start with docker_open5gs reference configs |
| eNodeB S1AP compatibility | High | Test early with real hardware |
| MongoDB schema mismatch | Medium | Validate against Open5GS WebUI |
| Frontend breaking changes | Low | Minimal UI changes for MVP |

---

## Future Phases (Post-MVP)

### Phase 2.0: 5G SA Support
- Add 5G core components (AMF, SMF, UPF)
- Support gNodeB registration
- Update UI for 5G terminology

### Phase 2.1: Multiple QoS Profiles
- Add Live Video, CCTV, POS profiles
- QoS policy editor in UI
- QCI/5QI mapping

### Phase 2.2: Enhanced Monitoring
- Prometheus metrics integration
- Real-time device status
- Throughput graphs

### Phase 2.3: Security Hardening
- TLS/HTTPS for web UI
- JWT authentication
- MongoDB authentication

---

## Release Strategy

### Private Development (Current)
- Repository: `git@github.com:Waveriders-Collective/open5g2go.git` (private)
- Access: Waveriders team only
- Focus: Core functionality, integration testing

### Invite-Only Beta (v0.1.0-beta)
- Repository remains private
- Invite 5-10 trusted community members
- Add as GitHub collaborators with read access
- Gather feedback on:
  - Deployment experience
  - Documentation clarity
  - Bug reports
  - Feature requests

### Public Release Criteria
Before making repo public, ensure:
- [ ] Stable deployment on 3+ different environments
- [ ] Documentation covers common issues
- [ ] No hardcoded secrets or internal references
- [ ] License file in place (recommend Apache 2.0 or MIT)
- [ ] CONTRIBUTING.md for community contributions
- [ ] At least 2 beta testers successfully deployed

### Public Release (v1.0.0)
- Change repository visibility to public
- Announce on Waveriders community channels
- Transfer to `Waveriders-Collective` org (if not already)
- Enable GitHub Discussions for community support

---

## Appendix: SIM Template & Device Provisioning

### Simplified IMSI Entry

Users enter only the **last 4 digits** of the IMSI when creating a device. The system auto-generates the full 15-digit IMSI:

```
User enters: 0001
Full IMSI:   315010000000001
             ├─────┤├───────┤
             Prefix  User input (zero-padded)
```

### Waveriders SIM Template

Waveriders provides pre-programmed SIMs with:
- PLMN: 315-010
- IMSI range: 315010000000001 - 315010000009999
- Shared K/OPc keys (per batch)

Users receive a simple mapping card:
```
SIM #  | Last 4 Digits | Label for Device
-------|---------------|------------------
SIM 01 | 0001          | CAM-01
SIM 02 | 0002          | CAM-02
...
SIM 10 | 0010          | TABLET-01
```

### Add Device UI Flow

```
┌─────────────────────────────────────┐
│ Add New Device                       │
├─────────────────────────────────────┤
│                                      │
│ Device Number (last 4 of IMSI):     │
│ ┌────────────────────────────────┐  │
│ │ 0001                           │  │
│ └────────────────────────────────┘  │
│                                      │
│ Device Name:                         │
│ ┌────────────────────────────────┐  │
│ │ CAM-01                         │  │
│ └────────────────────────────────┘  │
│                                      │
│ IP Address (optional):               │
│ ┌────────────────────────────────┐  │
│ │ 10.48.99.10                    │  │
│ └────────────────────────────────┘  │
│ ⓘ Leave blank for auto-assign       │
│                                      │
│            [Cancel]  [Add Device]    │
└─────────────────────────────────────┘
```

---

## Appendix: Constants Configuration

```python
# opensurfcontrol/constants.py

import os

# Open5GS MongoDB
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = "open5gs"

# Network Identity (PLMN 315-010)
MCC = "315"
MNC = "010"
PLMNID = f"{MCC}{MNC}"

# IMSI Format: 315010 + 9 digits (user enters last 4 only)
# Example: User enters "0001" → IMSI becomes "315010000000001"
IMSI_PREFIX = "31501000000"  # User appends 4 digits

# Default APN
DEFAULT_APN = "internet"

# UE IP Pool
UE_POOL_START = "10.48.99.2"
UE_POOL_END = "10.48.99.254"
UE_GATEWAY = "10.48.99.1"
UE_DNS = ["8.8.8.8", "8.8.4.4"]

# QoS (MVP: single best-effort profile)
DEFAULT_QCI = 9
DEFAULT_ARP_PRIORITY = 8
DEFAULT_AMBR_UL = 50000000   # 50 Mbps
DEFAULT_AMBR_DL = 100000000  # 100 Mbps

# Default Authentication Keys
DEFAULT_K = "465B5CE8B199B49FAA5F0A2EE238A6BC"
DEFAULT_OPC = "E8ED289DEBA952E4283B54E88E6183CA"

# Open5GS Paths
OPEN5GS_CONFIG_PATH = os.getenv("OPEN5GS_CONFIG_PATH", "/etc/open5gs")
```

---

## Appendix: Open5GS 4G EPC Config Template

```yaml
# open5gs/config/mme.yaml (key sections)

mme:
  freeDiameter: /etc/freeDiameter/mme.conf
  s1ap:
    - addr: 0.0.0.0
  gtpc:
    - addr: 127.0.0.2
  gummei:
    plmn_id:
      mcc: 315
      mnc: 010
    mme_gid: 2
    mme_code: 1
  tai:
    plmn_id:
      mcc: 315
      mnc: 010
    tac: 1
  security:
    integrity_order: [EIA2, EIA1, EIA0]
    ciphering_order: [EEA0, EEA1, EEA2]
```

---

## Appendix: Deployment Details

### Firewall & Network Configuration

**On NUC (Ubuntu, UFW):**

```bash
# Enable SCTP kernel support (required for S1AP)
sudo modprobe sctp
echo "sctp" | sudo tee -a /etc/modules

# Firewall rules (if UFW enabled)
sudo ufw allow 36412/sctp comment "S1AP eNodeB"
sudo ufw allow 2152/udp comment "GTP-U user data"
sudo ufw allow 8080/tcp comment "Web UI"
```

### eNodeB Configuration (Baicells)

In eNodeB web interface, configure **Network → S1AP Configuration**:

| Setting | Value |
|---------|-------|
| S1AP Server IP | 10.48.0.110 (NUC eth0 IP) |
| S1AP Port | 36412 (SCTP) |
| GTP-U Server IP | 10.48.0.110 |
| GTP-U Port | 2152 (UDP) |

After save/apply, monitor NUC:
```bash
docker-compose logs -f open5gs | grep -i "s1ap\|registered"
# Look for: "S1Setup from eNodeB accepted"
```

### Quick Deployment (Fixed IP Scenario)

```bash
# 1. Clone and deploy
git clone git@github.com:Waveriders-Collective/open5g2go.git
cd open5g2go

# 2. Build & start
docker-compose build && docker-compose up -d

# 3. Wait for startup (~90s) and verify
sleep 90 && docker-compose ps  # All should show "healthy"

# 4. Access Web UI
open http://10.48.0.110:8080
```

### Troubleshooting Quick Reference

| Issue | Diagnosis | Resolution |
|-------|-----------|-----------|
| eNodeB "Connecting" | S1AP port not reachable | Verify firewall, check eNodeB config IP/port |
| Port 36412 in use | Service conflict | `sudo netstat -tlnp \| grep 36412` |
| "SCTP not supported" | Kernel module missing | `sudo modprobe sctp` |
| Device not getting IP | Subscriber not provisioned | Add via Web UI or API |

### Health Monitoring

```bash
# Overall status
docker-compose ps

# Real-time logs
docker-compose logs -f

# Check subscriber count
docker exec open5g2go-mongodb mongo --eval "db.subscribers.count()"

# API health
curl http://10.48.0.110:8000/api/health
```

---

**Document End**
