# Open5G2GO Docker Compose Integration Design

**Date:** 2025-12-27
**Version:** 1.0
**Status:** Design Phase
**Scope:** MVP Phase 1 - Docker orchestration for 4G LTE with Baicells eNodeB

---

## Executive Summary

This design specifies a single `docker-compose.yml` that orchestrates the complete Open5G2GO system: Open5GS 4G LTE core + openSurfControl management web UI + MongoDB subscriber database. The architecture targets a **DHCP-enabled NUC in any lab network**, with eNodeB connecting directly via S1AP. Key design principle: **assume dynamic host IP, static internal Docker networking for Open5GS core**.

**Key Architectural Goals:**
1. Zero static IP configuration required on host
2. Works in any lab network (192.168.x.x, 10.x.x.x, etc.)
3. eNodeB discovers NUC IP dynamically, connects via S1AP
4. openSurfControl UI abstracts Open5GS complexity
5. MongoDB persistence for subscribers and configuration
6. Health checks and self-healing via compose restart policies

---

## System Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                     NUC (Linux Host)                              │
│                 Dynamic IP via DHCP (lab network)                 │
│                 eth0: x.x.x.x/24 (unknown at deploy time)        │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │         Docker Compose Network (open5g2go)                 │  │
│  │         Internal: 172.26.0.0/16 (Docker manages)           │  │
│  │                                                             │  │
│  │  ┌──────────────┐      ┌──────────────┐    ┌────────────┐ │  │
│  │  │  openSurf    │◄────►│  FastAPI API │◄──►│  MongoDB   │ │  │
│  │  │   Frontend   │      │   (Python)   │    │  Database  │ │  │
│  │  │ (Port 3000)  │      │ (Port 8000)  │    │ (Mongo     │ │  │
│  │  │              │      │ localhost)   │    │ Persisted) │ │  │
│  │  └──────────────┘      └──────────────┘    └────────────┘ │  │
│  │         ▲                      ▲                             │  │
│  │         │                      │                             │  │
│  │  REST API (localhost:8080)    Internal Socket/HTTP          │  │
│  │         │                      │                             │  │
│  │         └──────────┬───────────┘                             │  │
│  │                    ▼                                         │  │
│  │        ┌─────────────────────────┐                           │  │
│  │        │   Management Daemon     │                           │  │
│  │        │    (Python Service)     │                           │  │
│  │        │  (Internal localhost)   │                           │  │
│  │        └─────────────────────────┘                           │  │
│  │                    ▲                                         │  │
│  │                    │                                         │  │
│  │            YAML Config Generation                            │  │
│  │            MongoDB Subscriber Mgmt                           │  │
│  │                    │                                         │  │
│  │                    ▼                                         │  │
│  │        ┌─────────────────────────────────┐                  │  │
│  │        │      Open5GS Core (4G LTE)      │                  │  │
│  │        │                                 │                  │  │
│  │        │  ┌──────────────────────────┐   │                  │  │
│  │        │  │  MME (S1AP SCTP 36412)   │◄──┼──────────────┐   │  │
│  │        │  │  (Listening 0.0.0.0)     │   │              │   │  │
│  │        │  └──────────────────────────┘   │              │   │  │
│  │        │  ┌──────────────────────────┐   │              │   │  │
│  │        │  │  HSS (Diameter 3868)     │   │              │   │  │
│  │        │  └──────────────────────────┘   │              │   │  │
│  │        │  ┌──────────────────────────┐   │              │   │  │
│  │        │  │  SGW-C (GTP-C 2123)      │   │              │   │  │
│  │        │  └──────────────────────────┘   │              │   │  │
│  │        │  ┌──────────────────────────┐   │              │   │  │
│  │        │  │  SGW-U (GTP-U 2152)      │   │              │   │  │
│  │        │  └──────────────────────────┘   │              │   │  │
│  │        └─────────────────────────────────┘              │   │  │
│  │                                                          │   │  │
│  └──────────────────────────────────────────────────────────┼──┘  │
│                                                             │     │
│   eth0 (DHCP assigned, e.g., 192.168.1.50)                │     │
│   Ports exposed: 36412/SCTP, 2123/UDP, 2152/UDP           │     │
│   Port 8080 (web UI): accessible from lab network          │     │
│                                                             ▼     │
│                    Baicells eNodeB                             │
│                  (discovers NUC IP)                            │
│              (connects to eth0 IP:36412 SCTP)                 │
└──────────────────────────────────────────────────────────────────┘

Lab Network (192.168.0.0/24 or 10.0.0.0/8, etc.)
    │
    ├─ NUC (eth0 via DHCP)          ← S1AP/GTP traffic
    ├─ Baicells eNodeB              ← Configures S1AP target
    └─ Admin laptop                 ← Access http://nuc-ip:8080
```

---

## Network Philosophy: Two Networks, One Interface

**Problem:** How do we keep Open5GS internal networking simple (predictable IPs) while letting the host get DHCP-assigned IP?

**Solution:** Decouple them:
- **Host eth0**: DHCP dynamic IP (lab network, 192.168.x.x or 10.x.x.x)
  - eNodeB discovers this IP via DNS or manual config
  - All S1AP/GTP traffic targets this IP

- **Docker internal**: Static 172.26.0.0/16 bridge
  - Open5GS containers always at same IPs
  - Subscribers always get same device pool (172.26.99.0/24 internally)
  - **But don't expose this to eNodeB** - eNodeB talks to host IP

**Why it works:** Docker port exposure automatically bridges from host interface → container. When Open5GS binds to `0.0.0.0:36412`, it's reachable via `eth0 IP:36412` automatically.

---

## Docker Compose Service Definitions

### 1. Network Architecture

**Network Name:** `open5g2go`
**Type:** User-defined bridge
**IP Range:** 172.26.0.0/16 (internal Docker network only)
**Key Decision:** All inter-container communication via hostnames, NOT exposed to host network

**Rationale:**
- Container IPs assigned dynamically but predictably
- Hostname DNS resolution is stable within Docker network
- Open5GS ports bind to 0.0.0.0 for eNodeB access via **host** eth0
- Host DHCP IP doesn't affect Docker internal networking

---

### 2. Service: `mongodb`

```yaml
mongodb:
  image: mongo:6.0-alpine
  container_name: open5g2go_mongodb
  volumes:
    - mongodb_data:/data/db
    - mongodb_config:/data/configdb
  networks:
    - open5g2go
  restart: unless-stopped
  healthcheck:
    test: ["CMD", "mongo", "--eval", "db.adminCommand('ping')"]
    interval: 10s
    timeout: 5s
    retries: 5
    start_period: 30s
```

**Role:** Subscriber database and configuration store
**Network Exposure:** Internal only (no ports exposed to host)
**Data Persistence:** Named volume `mongodb_data` (survives container restart)
**Access:** FastAPI/Open5GS connect via hostname `mongodb:27017` (Docker DNS)
**Initialization:** Empty at startup; subscribers created via API

---

### 3. Service: `open5gs-mme`

```yaml
open5gs-mme:
  image: open5gs:latest  # Reference docker_open5gs build
  container_name: open5g2go_mme
  volumes:
    - /var/lib/open5gs:/var/lib/open5gs
    - /var/log/open5gs:/var/log/open5gs
    - ./configs/mme.yaml:/etc/open5gs/mme.yaml:ro
    - ./configs/hss.yaml:/etc/open5gs/hss.yaml:ro
    - ./configs/sgwc.yaml:/etc/open5gs/sgwc.yaml:ro
    - ./configs/sgwu.yaml:/etc/open5gs/sgwu.yaml:ro
    - ./configs/fd.conf:/etc/freeDiameter/mme.conf:ro
  ports:
    - "36412:36412/sctp"  # S1AP (SCTP) - eNodeB connection
    - "2123:2123/udp"     # GTP-C (UDP) - signaling
    - "2152:2152/udp"     # GTP-U (UDP) - user data downlink
  networks:
    - open5g2go
  environment:
    - MONGO_URI=mongodb://mongodb:27017/open5gs
    - CORE_CTRL_IP=172.26.0.3  # Internal Docker IP
    - DEVICE_POOL=172.26.99.0/24  # Device pool (internal)
    - DEVICE_GATEWAY=172.26.99.1
    - PLMN_MCC=315
    - PLMN_MNC=010
  restart: unless-stopped
  depends_on:
    mongodb:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "netstat", "-tuln", "|", "grep", "36412"]
    interval: 30s
    timeout: 10s
    retries: 3
```

**Role:** 4G LTE core (MME, HSS, SGW-C, SGW-U bundled)

**Critical Networking Points:**
1. **S1AP (36412/SCTP):** Exposed to host, eNodeB connects here
   - eNodeB discovers NUC's DHCP IP (e.g., 192.168.1.50)
   - eNodeB sends S1AP traffic to 192.168.1.50:36412
   - Docker automatically forwards 192.168.1.50:36412 → container:36412

2. **GTP-C (2123/UDP):** Exposed to host, signaling from SGW
3. **GTP-U (2152/UDP):** Exposed to host, downlink data from SGW-U

4. **Internal IPs:**
   - `CORE_CTRL_IP=172.26.0.3` is container's internal IP
   - Open5GS binds S1AP to 0.0.0.0, accessible via all interfaces
   - MongoDB accessed via `mongodb://mongodb:27017` (Docker DNS)

**Config Generation:** Management daemon generates YAML at startup

---

### 4. Service: `fastapi-backend`

```yaml
fastapi-backend:
  build:
    context: ./api
    dockerfile: Dockerfile
  container_name: open5g2go_api
  volumes:
    - ./api:/app/api:ro
    - ./daemon:/app/daemon:ro
    - ./configs:/app/configs
    - open5gs_logs:/var/log/open5gs:ro
  ports:
    - "8000:8000"  # HTTP API (exposed to host for development)
  networks:
    - open5g2go
  environment:
    - MONGO_URI=mongodb://mongodb:27017/open5gs
    - CORE_ADDRESS=172.26.0.3  # Internal address
    - DEVICE_POOL=172.26.99.0/24
    - DEVICE_GATEWAY=172.26.99.1
    - PLMN_MCC=315
    - PLMN_MNC=010
    - PYTHONUNBUFFERED=1
  restart: unless-stopped
  depends_on:
    mongodb:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
    interval: 15s
    timeout: 5s
    retries: 3
    start_period: 10s
```

**Role:** REST API + Management Daemon interface

**Responsibilities:**
- FastAPI server for web UI communication
- CoreAdapter implementation for Open5GS integration
- Subscriber CRUD operations (MongoDB)
- Config generation from WaveridersConfig schema
- Health monitoring and log aggregation

**Port Exposure:** 8000/TCP (available to frontend and host admin)
**Internal Network:** Communicates with MongoDB and Open5GS via internal Docker network

---

### 5. Service: `opensurf-frontend`

```yaml
opensurf-frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
    args:
      REACT_APP_API_URL: http://localhost:8000/api
  container_name: open5g2go_frontend
  ports:
    - "8080:3000"  # Web UI (port 8080 on host, 3000 in container)
  networks:
    - open5g2go
  environment:
    - REACT_APP_API_URL=http://localhost:8000/api
    - NODE_ENV=production
  restart: unless-stopped
  depends_on:
    - fastapi-backend
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:3000"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 15s
```

**Role:** Web UI for network management

**Technology:** React + TypeScript + Vite

**Access from Lab:**
- Get NUC's DHCP IP: `hostname -I` or check lab network DHCP table
- Open browser: `http://<nuc-dhcp-ip>:8080`

**API Communication:** Calls `fastapi-backend:8000/api` internally via Docker DNS

---

## Network Configuration Strategy

### IP Addressing Schema

```
┌──────────────────────────────────────────────────────────────┐
│  Lab Network (DHCP): 192.168.x.x/24 (example, varies)        │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  NUC eth0 (DHCP):    192.168.1.50 (discovered at runtime)    │
│                      ↑ eNodeB configures S1AP target here    │
│                      ↑ Admin accesses web UI here:8080        │
│                      ↑ Admin calls API here:8000 (optional)   │
│                                                               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  Docker Internal Network (172.26.0.0/16)                      │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  MongoDB:            172.26.0.2:27017                        │
│  Open5GS MME:        172.26.0.3                              │
│  FastAPI Backend:    172.26.0.4:8000 (internal)              │
│  Frontend:           172.26.0.5:3000 (internal)              │
│                                                               │
│  Device Pool:        172.26.99.0/24 (for UEs)                │
│    - Gateway:        172.26.99.1                             │
│    - Device 1:       172.26.99.10 (assigned by Open5GS)      │
│    - Device 2:       172.26.99.11                            │
│    - ...                                                      │
│    - Device 10:      172.26.99.19                            │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Port Mapping Diagram (eNodeB → Open5GS)

```
┌─────────────────────────────────────────────────────────┐
│ Baicells eNodeB (192.168.1.30 in lab network)           │
│ Configuration: Configure S1AP target as NUC's DHCP IP   │
└─────────────────────────────────────────────────────────┘
        │
        │ S1AP SCTP:36412
        │ GTP-U UDP:2152
        │
        ▼ (targets NUC eth0 DHCP IP)

192.168.1.50:36412 (eNodeB → NUC)
192.168.1.50:2152  (GTP-U)
        │
        │ Docker port forwarding (automatic)
        │
        ▼

open5gs-mme:36412/sctp (container)
open5gs-mme:2152/udp (container)

Internal to container:
- Open5GS binds to 0.0.0.0:36412
- Accessible via any interface (0.0.0.0)
- Docker forwards host interface → container
```

### Discovery and Configuration

| Role | Discovers | How |
|------|-----------|-----|
| Admin | NUC IP | `ssh nuc` then `hostname -I` or check DHCP server |
| eNodeB | NUC IP | Manual config in eNodeB UI, OR dynamic DNS if available |
| Docker | Container IPs | Internal bridge, automatic DNS (172.26.0.2, etc.) |

---

## Environment Variable Strategy

### Deployment Workflow

**Step 1: Create `.env` file**
```bash
# .env (commit-safe, filled at deployment time)
PLMN_MCC=315
PLMN_MNC=010
DEVICE_POOL=172.26.99.0/24
DEVICE_GATEWAY=172.26.99.1
DNS_1=8.8.8.8
DNS_2=8.8.4.4
MONGO_INITDB_DATABASE=open5gs
```

**Step 2: docker-compose.yml uses .env**
```yaml
environment:
  - MONGO_URI=mongodb://mongodb:27017/open5gs
  - CORE_ADDRESS=172.26.0.3
  - DEVICE_POOL=${DEVICE_POOL}
  - DEVICE_GATEWAY=${DEVICE_GATEWAY}
  - PLMN_MCC=${PLMN_MCC}
  - PLMN_MNC=${PLMN_MNC}
```

**Step 3: FastAPI reads env vars**
```python
# daemon/core/open5gs/config_generator.py
device_pool = os.getenv("DEVICE_POOL", "172.26.99.0/24")
core_address = os.getenv("CORE_ADDRESS", "172.26.0.3")
plmn = f"{os.getenv('PLMN_MCC', '315')}{os.getenv('PLMN_MNC', '010')}"
```

**Key Principle:** Internal network IPs hardcoded to 172.26.0.x range (known Docker bridge). No DHCP for containers.

---

## Port Mapping and Firewall Strategy

### Host Ports Exposed

| Port | Protocol | Direction | Purpose |
|------|----------|-----------|---------|
| 36412 | SCTP | Inbound | S1AP from eNodeB |
| 2123 | UDP | Inbound | GTP-C from SGW (signaling) |
| 2152 | UDP | Inbound/Outbound | GTP-U (user data) |
| 8080 | TCP | Inbound | Web UI from admin |
| 8000 | TCP | Inbound | API (optional, for testing) |

### Firewall Configuration

On NUC (Ubuntu):
```bash
# Enable SCTP kernel support
sudo modprobe sctp

# UFW firewall rules (if enabled)
sudo ufw allow 36412/sctp comment "S1AP eNodeB"
sudo ufw allow 2123/udp comment "GTP-C signaling"
sudo ufw allow 2152/udp comment "GTP-U data"
sudo ufw allow 8080/tcp comment "Web UI"
# Optional: sudo ufw allow from 192.168.0.0/16 to any port 8080

# Verify
sudo ufw status
```

### Docker Networking on Host

Docker automatically:
1. Listens on all host interfaces (0.0.0.0)
2. Forwards traffic: `eth0:36412 → open5gs-mme:36412`
3. Maintains translation in netfilter rules

No manual port forwarding needed.

---

## Health Check Strategy

### Startup Sequencing

```
1. MongoDB starts
   └─> Waits: mongo ping OK (30s max)
   └─> Signal: "healthy"

2. Open5GS MME waits for mongodb healthy
   └─> Dependency: mongodb:service_healthy
   └─> Waits: netstat shows 36412 listening (30s polling)
   └─> Signal: "healthy" (after S1AP ready)

3. FastAPI waits for mongodb healthy
   └─> Dependency: mongodb:service_healthy
   └─> Waits: HTTP 200 from /api/health (10s startup + polling)
   └─> Signal: "healthy"

4. Frontend waits for fastapi-backend (basic)
   └─> Dependency: fastapi-backend (simple readiness)
   └─> Waits: HTTP 200 from /index.html (15s startup)
   └─> Signal: "healthy"

Total Startup: ~60-90s (cold), ~10s (warm restart)
```

### Health Check Implementations

#### MongoDB
```yaml
healthcheck:
  test: ["CMD", "mongo", "--eval", "db.adminCommand('ping')"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 30s
```

#### Open5GS MME
```yaml
healthcheck:
  test: ["CMD", "bash", "-c", "netstat -tuln | grep 36412"]
  interval: 30s
  timeout: 10s
  retries: 3
```

#### FastAPI
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
  interval: 15s
  timeout: 5s
  retries: 3
  start_period: 10s
```

#### Frontend
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:3000/"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 15s
```

---

## Configuration Generation at Startup

### Initialization Flow

```
┌────────────────────────────────────┐
│  docker-compose up -d              │
└────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────┐
│  FastAPI container starts          │
│  - Load .env variables             │
│  - Initialize logging              │
└────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────┐
│  Connect to MongoDB (hostname)      │
│  mongodb://mongodb:27017/open5gs   │
│  (waits if MongoDB not ready)       │
└────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────┐
│  Create WaveridersConfig object:    │
│  - network_type: "4G_LTE"           │
│  - service_quality: "standard"      │
│  - plmn: "315010"                   │
│  - device_pool: 172.26.99.0/24      │
│  - core_address: 172.26.0.3         │
└────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────┐
│  Generate Open5GS configs:          │
│  - mme.yaml                         │
│  - hss.yaml                         │
│  - sgwc.yaml                        │
│  - sgwu.yaml                        │
│  Write to ./configs/ directory      │
└────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────┐
│  FastAPI /api/health ready         │
│  REST API serving at 0.0.0.0:8000  │
└────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────┐
│  Open5GS reads ./configs/mme.yaml   │
│  Starts MME (S1AP on 0.0.0.0:36412) │
│  Loads subscribers from MongoDB     │
└────────────────────────────────────┘
```

---

## Complete docker-compose.yml Template

```yaml
version: '3.9'

services:
  mongodb:
    image: mongo:6.0-alpine
    container_name: open5g2go_mongodb
    volumes:
      - mongodb_data:/data/db
      - mongodb_config:/data/configdb
    networks:
      - open5g2go
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "mongo", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  open5gs-mme:
    image: open5gs:latest
    container_name: open5g2go_mme
    volumes:
      - open5gs_lib:/var/lib/open5gs
      - open5gs_logs:/var/log/open5gs
      - ./configs/mme.yaml:/etc/open5gs/mme.yaml:ro
      - ./configs/hss.yaml:/etc/open5gs/hss.yaml:ro
      - ./configs/sgwc.yaml:/etc/open5gs/sgwc.yaml:ro
      - ./configs/sgwu.yaml:/etc/open5gs/sgwu.yaml:ro
      - ./configs/fd.conf:/etc/freeDiameter/mme.conf:ro
    ports:
      - "36412:36412/sctp"  # S1AP (eNodeB)
      - "2123:2123/udp"     # GTP-C
      - "2152:2152/udp"     # GTP-U
    networks:
      - open5g2go
    environment:
      - MONGO_URI=mongodb://mongodb:27017/open5gs
      - CORE_CTRL_IP=172.26.0.3
      - DEVICE_POOL=172.26.99.0/24
      - PLMN_MCC=${PLMN_MCC:-315}
      - PLMN_MNC=${PLMN_MNC:-010}
    restart: unless-stopped
    depends_on:
      mongodb:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "bash", "-c", "netstat -tuln | grep 36412"]
      interval: 30s
      timeout: 10s
      retries: 3

  fastapi-backend:
    build:
      context: ./api
      dockerfile: Dockerfile
    container_name: open5g2go_api
    volumes:
      - ./api:/app/api:ro
      - ./daemon:/app/daemon:ro
      - ./configs:/app/configs
      - open5gs_logs:/var/log/open5gs:ro
    ports:
      - "8000:8000"
    networks:
      - open5g2go
    environment:
      - MONGO_URI=mongodb://mongodb:27017/open5gs
      - CORE_ADDRESS=172.26.0.3
      - DEVICE_POOL=172.26.99.0/24
      - DEVICE_GATEWAY=172.26.99.1
      - PLMN_MCC=${PLMN_MCC:-315}
      - PLMN_MNC=${PLMN_MNC:-010}
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
    depends_on:
      mongodb:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s

  opensurf-frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        REACT_APP_API_URL: http://localhost:8000/api
    container_name: open5g2go_frontend
    ports:
      - "8080:3000"
    networks:
      - open5g2go
    environment:
      - REACT_APP_API_URL=http://localhost:8000/api
      - NODE_ENV=production
    restart: unless-stopped
    depends_on:
      - fastapi-backend
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s

networks:
  open5g2go:
    driver: bridge
    ipam:
      config:
        - subnet: 172.26.0.0/16

volumes:
  mongodb_data:
  mongodb_config:
  open5gs_lib:
  open5gs_logs:
```

---

## Deployment Instructions (MVP Phase 1)

### Prerequisites

```bash
# On NUC (Ubuntu 22.04+)
- Docker 20.10+
- Docker Compose 2.0+
- SCTP kernel module support
- DHCP client on eth0 (standard setup)
```

### Pre-Deployment Setup

```bash
# 1. Enable SCTP on NUC
sudo modprobe sctp
sudo bash -c 'echo "sctp" >> /etc/modules'  # Persist after reboot

# 2. Verify DHCP assignment
ip addr show eth0
# Example output: inet 192.168.1.50/24

# 3. Note the DHCP IP (e.g., 192.168.1.50)
# You'll configure eNodeB to target this IP for S1AP

# 4. Verify lab network connectivity
ping 8.8.8.8

# 5. Clone repository
git clone <repo> openSurfcontrol
cd openSurfcontrol

# 6. Create .env file
cat > .env << EOF
PLMN_MCC=315
PLMN_MNC=010
DEVICE_POOL=172.26.99.0/24
DEVICE_GATEWAY=172.26.99.1
DNS_1=8.8.8.8
DNS_2=8.8.4.4
MONGO_INITDB_DATABASE=open5gs
EOF
```

### Deploy Open5G2GO

```bash
# 1. Build images
docker-compose build

# 2. Start all services (background mode)
docker-compose up -d

# 3. Monitor startup (watch for all services healthy)
docker-compose logs -f
# Watch for:
# - mongodb: "Waiting for connections on port 27017"
# - open5gs-mme: S1AP listening on 0.0.0.0:36412
# - fastapi-backend: "Application startup complete"
# - opensurf-frontend: web server listening

# 4. Verify all services are healthy
docker-compose ps
# All should show "healthy" status

# 5. Get NUC's DHCP IP
NUCIIP=$(hostname -I | awk '{print $1}')
echo "NUC IP: $NUCIPI"
# Use this for eNodeB S1AP target and web UI access
```

### Configure eNodeB

On Baicells eNodeB management interface:
```
1. Navigate to Network → S1AP Configuration
2. Set S1AP Server: <NUC-DHCP-IP>  (e.g., 192.168.1.50)
3. Set S1AP Port: 36412 (SCTP)
4. Set GTP-U Server: <NUC-DHCP-IP>  (same)
5. Set GTP-U Port: 2152 (UDP)
6. Click Apply/Save
7. Watch MME logs for S1AP attach: docker-compose logs open5gs-mme
```

### Access Web UI

From any machine on the lab network:
```
1. Get NUC DHCP IP: ssh nuc 'hostname -I'
2. Open browser: http://<nuc-ip>:8080
3. You should see openSurfControl dashboard
4. Add devices via UI or API
```

### Verify eNodeB Connectivity

```bash
# On NUC, monitor S1AP handshake
docker-compose logs -f open5gs-mme | grep -i s1ap

# If eNodeB connects, you'll see:
# [mme] S1Setup from eNodeB accepted
# [mme] Registered eNodeB 0x123456
```

---

## Adding First Device (Example)

### Via FastAPI Directly

```bash
curl -X POST http://localhost:8000/api/devices \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CAM-01",
    "imsi": "315010000000001",
    "k": "8baf473f2f5fce0dca3baf473f2f5fce",
    "opc": "e8ed289deba952e4283b54e88e6183ca"
  }'
```

### Via Web UI

1. Open http://<nuc-ip>:8080
2. Click "Add Device"
3. Fill in:
   - Name: CAM-01
   - IMSI: 315010000000001
   - K (auth key): 8baf...
   - OPC: e8ed...
4. Click "Provision"

---

## Device Network Addressing

### How Devices Get IPs

```
Device (eNodeB attachment) → MME validates IMSI → SGW assigns IP from pool
                                                  (172.26.99.0/24)

Device always gets IP from Docker pool (172.26.99.x), NOT host network.
This is by design: devices are virtual within Docker network.

For actual Baicells physical devices, they interact with eNodeB which
bridges to Open5GS via S1AP/GTP (container ports exposed to host).
```

---

## Troubleshooting Guide

| Issue | Diagnosis | Resolution |
|-------|-----------|-----------|
| eNodeB cannot find NUC | S1AP connection timeout | Check NUC firewall: `sudo ufw status`, verify eNodeB S1AP target IP/port correct |
| "Connection refused" on 36412 | Port not listening | `docker-compose logs open5gs-mme \| grep "S1AP"` or `docker-compose ps open5gs-mme` |
| MongoDB connection error | MongoDB not healthy | `docker-compose logs mongodb`, verify health: `docker-compose ps` |
| API returns 500 errors | FastAPI crash | `docker-compose logs fastapi-backend 2>&1 \| tail -50` |
| Web UI blank page | API unreachable | Check browser console (F12), verify REACT_APP_API_URL env var |
| Device not getting IP | GTP tunnel issue | `docker-compose logs open5gs-mme \| grep -i "gtp"` |
| Startup hangs | Service dependency issue | `docker-compose logs` (all), check which service isn't healthy |
| SCTP not supported | Kernel module missing | `sudo modprobe sctp`, check: `lsmod \| grep sctp` |

---

## Security Considerations

### MVP Phase 1 (Development/Lab)

| Control | Implementation | Notes |
|---------|----------------|-------|
| MongoDB Auth | Disabled | Internal Docker network only - acceptable for lab |
| API TLS | Not required | Frontend on same host/LAN, no sensitive data in transit |
| API Auth | Bearer token (hardcoded) | Will be configurable in Phase 2 |
| Container Isolation | Standard Docker | No special user namespaces; acceptable for lab |
| Network Policies | None | Single bridge network; all containers trusted |

### Phase 2 Security Upgrades (Planning)
- MongoDB authentication (username/password)
- FastAPI ↔ Frontend TLS (self-signed certificate)
- JWT token-based API authentication
- Container user namespaces (run as non-root)

---

## Scaling Considerations (Future)

### Phase 2: Multi-Device Support (10+)
- Subscriber pre-provisioning via CSV import
- Bulk device API operations
- Advanced QoS policy templates

### Phase 3: High Availability
- MongoDB replica set (multiple nodes)
- Multiple Open5GS MME instances (behind load balancer)
- Persistent volume backup/restore

### Phase 4: Cloud Deployment
- Migrate from Docker Compose to Kubernetes
- Cloud-native storage (AWS EBS, GCP Persistent Disk)
- Multi-region federation

---

## Key Architectural Decisions Summary

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| DHCP for host NUC | Assumes lab network, simplest deployment | Must configure eNodeB with discovered IP |
| Docker internal network 172.26.0.0/16 | Stable, non-conflicting with common labs (192.168, 10.x) | One more IP range to remember |
| Port exposure (36412, 2123, 2152) | eNodeB must reach core via host interface | Requires firewall rules |
| MongoDB in Docker | Simplicity, same deployment footprint | Data persistence requires volume management |
| Single Open5GS container | Monolithic, matches docker_open5gs design | Less granular scaling later |
| FastAPI health endpoints required | Self-healing, clear startup sequence | Requires API implementation |
| QCI 9 default | Matches Baicells PoC, simple MVP | Limited QoS options early |
| PLMN 315-010 hardcoded | Phased flexibility: hardcoded → env vars → UI config | Must change .env for different PLMN |

---

## Integration Checklist

Before deploying with real eNodeB:

- [ ] Clone openSurfcontrol repository
- [ ] Install Docker + Docker Compose
- [ ] Enable SCTP kernel module
- [ ] Create .env file with desired PLMN/pool IPs
- [ ] Build images: `docker-compose build`
- [ ] Start services: `docker-compose up -d`
- [ ] Wait ~90s for all services healthy
- [ ] Note NUC's DHCP IP: `hostname -I`
- [ ] Configure eNodeB S1AP target: `<nuc-ip>:36412`
- [ ] Access web UI: `http://<nuc-ip>:8080`
- [ ] Add first device via UI
- [ ] Verify eNodeB S1AP registration: `docker-compose logs open5gs-mme | grep S1Setup`
- [ ] Device should get IP from pool (172.26.99.x)

---

## Next Steps

1. **Implement docker-compose.yml** based on this template
2. **Create Dockerfiles** for:
   - FastAPI backend (`api/Dockerfile`)
   - React frontend (`frontend/Dockerfile`)
3. **Implement FastAPI endpoints:**
   - `GET /api/health` - liveness/readiness
   - `GET /api/devices` - list subscribers
   - `POST /api/devices` - add subscriber
   - `PUT /api/devices/{imsi}` - update QoS
   - `DELETE /api/devices/{imsi}` - remove subscriber
4. **Test locally** with docker-compose + mock eNodeB
5. **Deploy to NUC** with real Baicells eNodeB
6. **Document** discovered issues and workarounds
7. **Plan Phase 2** (multi-device, advanced QoS, HA)

