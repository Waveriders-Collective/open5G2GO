# Open5G2GO Docker Compose - Architecture Diagrams & Reference

**Date:** 2025-12-27
**Purpose:** Visual reference for docker-compose design decisions

---

## Network Topology Diagram

### Complete System View

```
┌─────────────────────────────────────────────────────────────────┐
│                     LAB NETWORK (DHCP)                          │
│                   192.168.0.0/24 (example)                      │
│                                                                  │
│  ┌──────────────┐        ┌──────────────┐                       │
│  │ Admin Laptop │        │ Baicells     │                       │
│  │ 192.168.0.10 │◄──────►│ eNodeB       │                       │
│  │              │        │ 192.168.0.40 │                       │
│  └──────────────┘        └──────┬───────┘                       │
│         │                       │                               │
│         │ HTTP:8080             │ S1AP:36412/SCTP               │
│         │ or 8000/tcp           │ GTP-U:2152/UDP                │
│         │                       │ GTP-C:2123/UDP                │
│         │                       │                               │
│         └───────────┬───────────┘                               │
│                     │                                           │
│                     ▼                                           │
│         ┌───────────────────────────┐                          │
│         │   NUC Linux Host          │                          │
│         │   eth0: 192.168.0.50/24   │ (DHCP assigned)         │
│         │   (Dynamic IP)            │                          │
│         │                           │                          │
│         │  Docker Engine Running    │                          │
│         │  (open5g2go network)      │                          │
│         └───────────────────────────┘                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘


                        ▼ Docker Host


┌─────────────────────────────────────────────────────────────────┐
│          NUC - Docker Container Runtime                         │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │     Docker Network "open5g2go" (bridge)                 │   │
│  │     Internal: 172.26.0.0/16 (Docker manages)            │   │
│  │                                                         │   │
│  │  ┌─────────────┐  ┌──────────┐  ┌──────────┐           │   │
│  │  │ mongodb     │  │ open5gs  │  │ fastapi  │           │   │
│  │  │ 172.26.0.2  │  │ 172.26.0 │  │ 172.26.0 │           │   │
│  │  │ :27017      │  │ .3       │  │ .4:8000  │           │   │
│  │  │             │  │ :36412   │  │          │           │   │
│  │  │ (internal)  │  │ :2123    │  │ (host    │           │   │
│  │  │             │  │ :2152    │  │  8000)   │           │   │
│  │  └─────────────┘  │ (host    │  └──────────┘           │   │
│  │                   │ ports)   │                          │   │
│  │                   └──────────┘  ┌──────────┐           │   │
│  │                                 │ frontend │           │   │
│  │                                 │ 172.26.0 │           │   │
│  │                                 │ .5:3000  │           │   │
│  │                                 │ (host    │           │   │
│  │                                 │  8080)   │           │   │
│  │                                 └──────────┘           │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Service Communication Diagram

### Internal Docker Network Flow

```
                    ┌─────────────┐
                    │   mongodb   │
                    │  172.26.0.2 │
                    └──────┬──────┘
                           │
                      [MongoDB URI]
                      (27017/TCP)
                           │
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
        ┌──────────────┐      ┌──────────────┐
        │ open5gs-mme  │      │ fastapi-     │
        │              │      │ backend      │
        │ 172.26.0.3   │◄────►│ 172.26.0.4   │
        │              │      │              │
        │ S1AP:36412   │      │ HTTP:8000    │
        │ GTP-C:2123   │      │              │
        │ GTP-U:2152   │      └──────┬───────┘
        └──────────────┘             │
                                     │
                            [HTTP REST API]
                            (8000/TCP)
                                     │
                            ┌────────▼────────┐
                            │  opensurf-      │
                            │  frontend       │
                            │  172.26.0.5     │
                            │  3000/TCP       │
                            └─────────────────┘
```

---

## Port Mapping & eNodeB Connectivity

### Port Exposure Model

```
Baicells eNodeB                Lab Network (192.168.0.0/24)
    │
    │ S1AP SCTP:36412 ──────┐
    │ GTP-U UDP:2152        │
    │ GTP-C UDP:2123        │
    │                       │
    └──────────┬────────────┘
               │
               ▼ (connects to NUC eth0)
          192.168.0.50:36412 (DHCP assigned IP)
          192.168.0.50:2123
          192.168.0.50:2152
               │
               │ Host kernel netfilter
               │ (Docker iptables rules)
               │
               ▼ Automatic port forwarding

    docker0 bridge (172.17.0.0/16) ─┐
                                     │
    open5g2go bridge (172.26.0.0/16) ├─ Host routes traffic inbound
                                     │  to container ports
                                     │
                                ┌────▼─────┐
                                │ open5gs   │
                                │ container │
                                │ 172.26.0.3│
                                │ :36412    │
                                │ :2123     │
                                │ :2152     │
                                └───────────┘
```

### Port Binding Details

| Protocol | Host Port | Container Port | Binding | Accessible From |
|----------|-----------|----------------|---------|-----------------|
| SCTP | 36412 | 36412 | 0.0.0.0:36412 | eNodeB in lab network |
| UDP | 2123 | 2123 | 0.0.0.0:2123 | eNodeB in lab network |
| UDP | 2152 | 2152 | 0.0.0.0:2152 | eNodeB in lab network |
| TCP | 8000 | 8000 | 127.0.0.1:8000* | Admin (localhost or lab network) |
| TCP | 8080 | 3000 | 0.0.0.0:8080 | Admin from lab network |

*Note: API port can be made public for remote admin by changing bind to 0.0.0.0:8000 in docker-compose.yml

---

## Data Flow Diagrams

### Subscriber Provisioning

```
┌─────────────────────────────────────────────────────────────────┐
│                    Admin Browser                                 │
│          http://<nuc-ip>:8080                                   │
│                                                                  │
│     Form: Add Device                                            │
│     Name: CAM-01                                                │
│     IMSI: 315010000000001                                       │
│     K: 8baf473f2f5fce0dca3baf473f2f5fce                         │
│     OPC: e8ed289deba952e4283b54e88e6183ca                       │
└─────────────────────────────────────────────────────────────────┘
                           │
                           │ HTTP POST /api/devices
                           │ JSON body
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│             opensurf-frontend Container                          │
│                 (React/Vite)                                    │
│                                                                  │
│  Validates form, sends to backend                              │
└─────────────────────────────────────────────────────────────────┘
                           │
                           │ HTTP POST
                           │ (internal Docker DNS)
                           │ http://fastapi-backend:8000/api/devices
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│            fastapi-backend Container                             │
│                (Python/FastAPI)                                 │
│                                                                  │
│  1. Validate IMSI (15 digits), K (32 hex), OPC (32 hex)        │
│  2. Create DeviceConfig pydantic model                          │
│  3. Convert to Open5GSSubscriber with QoS policy                │
│  4. Insert into MongoDB                                         │
│  5. Generate/update Open5GS config files                        │
│  6. Return 200 OK with subscriber_id                            │
└─────────────────────────────────────────────────────────────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
        ┌──────────────┐      ┌──────────────┐
        │  MongoDB     │      │  ./configs/  │
        │  (insert)    │      │  (write YAML)│
        │              │      │              │
        │ subscribers  │      │  mme.yaml    │
        │ collection   │      │  hss.yaml    │
        └──────────────┘      └──────────────┘
                │                     │
                │ Persistent data     │ Volume mounted
                │ (mongodb_data)      │ (bind mount)
                │                     │
                └─────────┬───────────┘
                          │
                          ▼
        ┌─────────────────────────────────────┐
        │     open5gs-mme container          │
        │   Reads MongoDB for subscriber      │
        │   Reads YAML config files           │
        │   S1AP registration for eNodeB      │
        │   Device gets IP from pool          │
        │   (172.26.99.0/24)                  │
        └─────────────────────────────────────┘
```

### eNodeB S1AP Registration

```
┌──────────────────────────────┐
│  Baicells eNodeB             │
│  (192.168.0.40)              │
│                              │
│  Configured S1AP Target:     │
│  192.168.0.50:36412          │
└──────────────────────────────┘
           │
           │ S1Setup Request
           │ SCTP:36412
           │
           ▼ (to NUC eth0)
        192.168.0.50:36412
           │
           │ [kernel routing & iptables]
           │ Docker port-forward rule
           │
           ▼
┌──────────────────────────────┐
│  open5gs-mme Container       │
│  listening 0.0.0.0:36412/sctp│
│  (effectively 172.26.0.3)    │
│                              │
│  [S1AP state machine]        │
│  ├─ S1Setup response         │
│  ├─ MME ID exchange          │
│  ├─ eNodeB registered        │
│  └─ Ready for UE attach      │
└──────────────────────────────┘
           │
           │ S1Setup Accept
           │ SCTP:36412 (reverse)
           │
           ▼ (to eNodeB)
┌──────────────────────────────┐
│  Baicells eNodeB             │
│  eNodeB now registered       │
│  Ready to attach devices     │
└──────────────────────────────┘
```

---

## Startup Sequence Diagram

### Cold Start (First Boot)

```
Time  Service            Status           Health Check                  Notes
──────────────────────────────────────────────────────────────────────────
T+0   docker-compose up  STARTING         -                             All services spawned
      All services                        (no wait)

T+1   mongodb            STARTING         mongo ping → FAIL             Awaiting DB startup
      others waiting                                                    (depends_on not yet healthy)

T+2   mongodb            STARTING         mongo ping → FAIL             DB initializing

T+10  mongodb            STARTING         mongo ping → OK               MongoDB ready!
                        HEALTHY          ✓ (start_period=30s)

T+11  open5gs-mme        STARTING         netstat 36412 → FAIL         Waits for mongodb
      fastapi-backend    STARTING         curl /api/health → FAIL      healthy signal


T+15  fastapi-backend    INITIALIZING     curl /api/health → FAIL      Loading config, init DB
                                                                        Starting Uvicorn

T+20  fastapi-backend    RUNNING          curl /api/health → OK        API ready
                        HEALTHY          ✓ (start_period=10s)

T+21  opensurf-frontend  STARTING         curl /index.html → FAIL      Depends on fastapi
      (explicit dep)                                                    Building React app

T+30  open5gs-mme        RUNNING          netstat 36412 → OK           S1AP port listening
                        HEALTHY          ✓ (first check passes)        Subscribers loaded
                                                                        from MongoDB

T+35  opensurf-frontend  RUNNING          curl /index.html → OK        Frontend serving
                        HEALTHY          ✓ (start_period=15s)          React app bundled

T+36  ALL SERVICES       RUNNING          All healthy                   System ready for eNodeB
      HEALTHY            ✓✓✓✓                                          attach


Total startup: ~35-40 seconds
```

### Warm Restart (Container reuse, volumes persist)

```
Time  Service            Event
────────────────────────────────────────────────────────────────
T+0   docker-compose up  Containers recreated

T+3   mongodb            Ready (no re-init, data in volume)

T+5   fastapi-backend    Connected to MongoDB, generators ready

T+8   opensurf-frontend  Rebuilt, served

T+10  open5gs-mme        Loaded config, attached to MongoDB

T+10  ALL SERVICES       Healthy


Total restart: ~10 seconds
```

---

## Configuration File Structure

### Generated at FastAPI Startup

```
repository root/
│
├── docker-compose.yml          (Specifies all services)
├── .env                        (PLMN, pool, etc.)
├── Dockerfile (api/)           (FastAPI image build)
├── Dockerfile (frontend/)      (React image build)
│
├── daemon/
│   ├── core/
│   │   └── open5gs/
│   │       ├── config_generator.py     (Creates YAML)
│   │       └── subscriber_manager.py   (MongoDB ops)
│   └── models/
│       └── schema.py            (Pydantic models)
│
├── configs/                    (Generated by daemon)
│   ├── mme.yaml                ✓ Generated at startup
│   ├── hss.yaml                ✓ Generated at startup
│   ├── sgwc.yaml               ✓ Generated at startup
│   ├── sgwu.yaml               ✓ Generated at startup
│   └── fd.conf                 (FreeDiameter config)
│
└── volumes/ (Docker managed)
    ├── mongodb_data            (Persistent subscriber DB)
    ├── mongodb_config          (Replica set config)
    ├── open5gs_lib             (State files)
    └── open5gs_logs            (Service logs)
```

---

## IP Address Assignment Lifecycle

### Device IP Allocation Flow

```
┌─────────────────────────────────────────┐
│  Baicells eNodeB (192.168.0.40)         │
│  Attaches UE (Device IMSI)              │
│  S1AP to MME (192.168.0.50:36412)       │
└─────────────────────────────────────────┘
          │
          │ S1 AttachRequest
          │ IMSI: 315010000000001
          │
          ▼
┌─────────────────────────────────────────┐
│  open5gs-mme (172.26.0.3)               │
│  1. Looks up IMSI in MongoDB            │
│     → Found: CAM-01 (subscriber)        │
│  2. Validates K, OPC credentials       │
│  3. Creates context                    │
│  4. Sends CreateSessionRequest to SGW  │
└─────────────────────────────────────────┘
          │
          │ GTP-C (2123)
          │ (internal Docker network)
          │
          ▼
┌─────────────────────────────────────────┐
│  sgwc (same container, 127.0.0.6)       │
│  Processes request                      │
│  Allocates IP from pool                 │
│  (172.26.99.0/24)                       │
│  → Assigns: 172.26.99.10                │
└─────────────────────────────────────────┘
          │
          │ CreateSessionResponse
          │ IP: 172.26.99.10
          │
          ▼
┌─────────────────────────────────────────┐
│  open5gs-mme                            │
│  Sends S1 AttachAccept                  │
│  IP: 172.26.99.10                       │
│  APN: "internet"                        │
│  DNS: 8.8.8.8, 8.8.4.4                 │
└─────────────────────────────────────────┘
          │
          │ S1AP (SCTP)
          │ (reverse path)
          │
          ▼
┌─────────────────────────────────────────┐
│  Baicells eNodeB                        │
│  Device assigned IP: 172.26.99.10       │
│  PDN connectivity active                │
│  (via GTP-U tunnel to SGW-U)            │
└─────────────────────────────────────────┘

Device now has:
- IP: 172.26.99.10 (internal Docker pool)
- Gateway: 172.26.99.1
- DNS: 8.8.8.8, 8.8.4.4 (external)
- Tunnel: GTP-U encrypted to SGW-U
```

---

## Database Schema Overview

### MongoDB Collections

```
open5gs (database)
│
├── subscribers (collection)
│   │
│   └── Documents (one per device):
│       {
│         "_id": ObjectId("..."),
│         "imsi": "315010000000001",
│         "name": "CAM-01",
│         "k": "8baf473f...",
│         "opc": "e8ed289d...",
│         "slice_qos": {
│           "qos_index": 9,                    ← QCI 9 (best-effort)
│           "session": [{
│             "name": "internet",
│             "type": 3,                       ← IPv4
│             "qos": {
│               "index": 9,
│               "arp": {
│                 "priority_level": 9,
│                 "pre_emption_capability": 1,
│                 "pre_emption_vulnerability": 1
│               }
│             },
│             "ambr": {
│               "uplink": {"value": 1000, "unit": 1},   ← 1 Mbps (kbps)
│               "downlink": {"value": 1000, "unit": 1}
│             }
│           }]
│         },
│         "ambr": {
│           "uplink": {"value": 1000, "unit": 1},
│           "downlink": {"value": 1000, "unit": 1}
│         },
│         "security": {
│           "k": "8baf473f...",
│           "amf": "8000",
│           "op": null,
│           "opc": "e8ed289d..."
│         },
│         "schema_version": 1
│       }
│
└── [other Open5GS collections handled by core]
    ├── plmn
    ├── imei
    ├── access_profile
    └── ...
```

---

## Environment Variable Resolution

### At Startup (.env → Service)

```
.env file (version controlled, template)
│
├── PLMN_MCC=315
├── PLMN_MNC=010
├── DEVICE_POOL=172.26.99.0/24
├── DEVICE_GATEWAY=172.26.99.1
└── ...
│
▼ docker-compose reads .env and expands ${VAR}
│
docker-compose.yml (processed)
│
├── services:
│   ├── open5gs-mme:
│   │   environment:
│   │     - PLMN_MCC=315              ← from .env
│   │     - PLMN_MNC=010              ← from .env
│   │     - CORE_CTRL_IP=172.26.0.3   ← hardcoded (internal)
│   │
│   └── fastapi-backend:
│       environment:
│         - PLMN_MCC=315              ← from .env
│         - PLMN_MNC=010              ← from .env
│         - DEVICE_POOL=172.26.99.0/24 ← from .env
│         - PYTHONUNBUFFERED=1        ← hardcoded
│
▼ Container entrypoint reads env vars
│
daemon/core/open5gs/config_generator.py
│
├── mcc = os.getenv("PLMN_MCC", "315")
├── mnc = os.getenv("PLMN_MNC", "010")
├── device_pool = os.getenv("DEVICE_POOL", "172.26.99.0/24")
└── Generates configs with these values

▼
Config files written to ./configs/
│
├── mme.yaml (includes MCC/MNC in GUMMEI)
├── hss.yaml
├── sgwc.yaml
└── sgwu.yaml

▼ open5gs-mme reads config files
│
MME running with PLMN 315-010, device pool 172.26.99.0/24
```

---

## Firewall Rules Required

### On NUC (ufw)

```
BEFORE (default deny all inbound)
│
├─ S1AP SCTP:36412 CLOSED  ❌
├─ GTP-C UDP:2123 CLOSED   ❌
├─ GTP-U UDP:2152 CLOSED   ❌
├─ Web UI TCP:8080 CLOSED  ❌
└─ API TCP:8000 CLOSED     ❌
│
    docker-compose up triggers UFW dialog (if enabled)
    OR
    sudo ufw allow 36412/sctp
    sudo ufw allow 2123/udp
    sudo ufw allow 2152/udp
    sudo ufw allow 8080/tcp
    sudo ufw allow from 192.168.0.0/24 to any port 8000  (optional)
│
AFTER (rules enabled)
│
├─ S1AP SCTP:36412 OPEN  ✓ (eNodeB connects)
├─ GTP-C UDP:2123 OPEN   ✓ (signaling)
├─ GTP-U UDP:2152 OPEN   ✓ (user data)
├─ Web UI TCP:8080 OPEN  ✓ (admin from lab)
└─ API TCP:8000 OPEN     ✓ (admin from lab)
```

---

## Error Recovery Scenarios

### Scenario 1: MongoDB Crashes

```
docker-compose up -d

[mongodb]
│
├─ Detects crash
├─ Automatic restart (unless-stopped policy)
└─> Recovers from volume (mongodb_data) within 10s

[fastapi-backend]
├─ Connection fails → logs error
├─ Retries automatically (depends_on healthy check)
└─> Reconnects when MongoDB healthy

[open5gs-mme]
├─ Can continue running with cached subscribers
├─ May eventually fail on config refresh
└─> Restarts via policy, reconnects to MongoDB

System self-heals: No manual intervention needed
```

### Scenario 2: eNodeB Loses Connection

```
eNodeB disconnects (power loss, network issue)

[open5gs-mme]
├─ S1AP detects socket close
├─ Logs: "S1AP connection lost from eNodeB"
├─ Removes eNodeB from registered list
└─> Waits for S1Setup from eNodeB

[devices]
├─ Lose service temporarily
├─ UE attach will fail until eNodeB reconnects
└─> On eNodeB restart: S1Setup → UE re-attach

System monitoring: Check docker logs open5gs-mme for "S1Setup"
```

### Scenario 3: Out of IP Addresses

```
Device Pool: 172.26.99.0/24 (256 total IPs)
└─ .0 = network
└─ .1 = gateway
└─ .2 to .254 = allocable (253 devices max)

10 devices connected:
├─ 172.26.99.10 (CAM-01)
├─ 172.26.99.11 (CAM-02)
├─ ...
└─ 172.26.99.19 (CAM-10)

MVP Phase 1 Limit: 10 devices (plenty of pool space)

If pool exhausted:
├─ SGW rejects CreateSessionRequest
├─ Device attach fails with "ESM PDN setup failure"
└─> Solution: Extend pool in .env (Phase 2 feature)
```

---

## Docker Compose Command Reference

```bash
# Start system (background)
docker-compose up -d

# View logs (all services)
docker-compose logs -f

# View logs (specific service)
docker-compose logs -f open5gs-mme
docker-compose logs -f fastapi-backend

# List running services
docker-compose ps

# Stop system (containers paused, volumes preserved)
docker-compose down

# Stop + remove volumes (CAREFUL: deletes subscriber DB!)
docker-compose down -v

# Rebuild images (if code changed)
docker-compose build

# Restart service
docker-compose restart open5gs-mme

# Execute command in container
docker exec open5g2go_api curl http://localhost:8000/api/health

# Shell into container
docker exec -it open5g2go_api /bin/bash

# Cleanup dangling images/containers
docker system prune

# View resource usage
docker stats

# Monitor S1AP handshake
docker-compose logs open5gs-mme | grep -i s1ap
```

---

## Kubernetes Migration Path (Future)

### Phase 4: Helm Chart Structure (Preview)

```
open5g2go-helm/
│
├── Chart.yaml
├── values.yaml                    (Replaces .env)
│
├── templates/
│   ├── mongodb-deployment.yaml    (StatefulSet with PVC)
│   ├── open5gs-deployment.yaml    (Deployment with PVC)
│   ├── fastapi-deployment.yaml    (Deployment)
│   ├── frontend-deployment.yaml   (Deployment)
│   ├── services/
│   │   ├── mongodb-service.yaml   (ClusterIP)
│   │   ├── open5gs-service.yaml   (LoadBalancer or NodePort)
│   │   ├── api-service.yaml       (ClusterIP)
│   │   └── frontend-service.yaml  (LoadBalancer or Ingress)
│   └── configmaps/
│       ├── open5gs-config.yaml    (YAML templates)
│       └── environment.yaml       (Shared env vars)
│
└── README.md                      (Deployment guide)

Migration checklist:
├─ Replace docker-compose volume → K8s PersistentVolumeClaim
├─ Replace docker healthcheck → K8s livenessProbe/readinessProbe
├─ Replace environment vars → ConfigMap + Secret
├─ Replace port binding → Service type LoadBalancer/NodePort
├─ Add ingress for web UI (http://<domain>)
└─ Multi-replica for HA (pending Phase 3)
```

---

## Quick Reference: Where Things Live

| Component | Location | Container | Internal IP | Port |
|-----------|----------|-----------|-------------|------|
| Subscribers | `/data/db` (volume) | mongodb | 172.26.0.2 | 27017 |
| MME Config | `./configs/mme.yaml` | bind mount | 172.26.0.3 | 36412 |
| API Code | `./api/` | bind mount | 172.26.0.4 | 8000 |
| Frontend | `./frontend/` | bind mount | 172.26.0.5 | 3000 |
| Logs | `/var/log/open5gs/` (volume) | open5gs-mme | (read by FastAPI) | - |
| Deployed Configs | Mounted in container | open5gs-mme | (read at startup) | - |

---

**Visual Reference Complete**
Use these diagrams alongside the main design document for architectural clarity.

