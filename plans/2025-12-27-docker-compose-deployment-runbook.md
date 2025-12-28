# Open5G2GO Docker Compose Deployment Runbook

**Date:** 2025-12-27
**Audience:** DevOps engineers, field deployment teams
**Time to Value:** 10-15 minutes (assuming Docker pre-installed)

---

## Table of Contents

1. [Pre-Flight Checklist](#pre-flight-checklist)
2. [Quick Start (5 min)](#quick-start-5-min)
3. [Detailed Setup Steps](#detailed-setup-steps)
4. [eNodeB Configuration](#enodeb-configuration)
5. [Verification & Testing](#verification--testing)
6. [Troubleshooting](#troubleshooting)
7. [Cleanup & Teardown](#cleanup--teardown)

---

## Pre-Flight Checklist

**Before starting, confirm you have:**

- [ ] NUC or Linux host with 4+ GB RAM, 20+ GB disk
- [ ] Docker 20.10+ installed (`docker --version`)
- [ ] Docker Compose 2.0+ installed (`docker-compose --version`)
- [ ] Ubuntu 22.04+ (or compatible Linux)
- [ ] Network connectivity (DHCP on eth0)
- [ ] Baicells eNodeB on same lab network (optional for testing)
- [ ] Admin machine on lab network with web browser
- [ ] Git installed (`git --version`)
- [ ] SSH access to NUC (for remote deployment)

**Optional but recommended:**
- [ ] curl installed (for API testing)
- [ ] netstat/ss installed (for port verification)
- [ ] MongoDB Compass (GUI for subscriber viewing)

---

## Quick Start (5 min)

### For Impatient Users

```bash
# On NUC
ssh nuc
sudo apt update && sudo apt install -y curl netstat-tools

# Clone repo
git clone https://github.com/waveriders/opensurfcontrol.git
cd opensurfcontrol

# Deploy
docker-compose build
docker-compose up -d

# Wait ~90s for services to start
sleep 90

# Get NUC IP and test
NUC_IP=$(hostname -I | awk '{print $1}')
curl http://$NUC_IP:8000/api/health
# Should return: {"status": "healthy"}

# Open web UI
echo "Web UI ready at http://$NUC_IP:8080"
# (Open in browser from admin machine)
```

**That's it!** Proceed to [eNodeB Configuration](#enodeb-configuration) if you have a Baicells.

---

## Detailed Setup Steps

### Step 1: Prepare NUC

#### 1.1 Connect to NUC

```bash
# Option A: SSH access
ssh <nuc-user>@<nuc-ip>

# Option B: Local console
# (physical login to NUC)
```

#### 1.2 Verify Network Setup

```bash
# Check DHCP IP is assigned
ip addr show eth0
# Expected output:
# inet 192.168.1.50/24 brd 192.168.1.255 scope global dynamic eth0

# Note the IP (e.g., 192.168.1.50)
# You'll need this for eNodeB configuration
NUC_IP=$(ip addr show eth0 | grep "inet " | awk '{print $2}' | cut -d/ -f1)
echo "NUC IP: $NUC_IP"
```

#### 1.3 Enable SCTP Kernel Support

```bash
# Check if SCTP already enabled
lsmod | grep sctp
# If empty, enable it:

sudo modprobe sctp

# Make persistent (survives reboot)
echo "sctp" | sudo tee -a /etc/modules

# Verify
lsmod | grep sctp
# Should show "sctp" in output
```

#### 1.4 Configure Firewall (if enabled)

```bash
# Check UFW status
sudo ufw status

# If "Status: inactive", skip this section
# If "Status: active", add rules:

sudo ufw allow 36412/sctp comment "S1AP eNodeB"
sudo ufw allow 2123/udp comment "GTP-C signaling"
sudo ufw allow 2152/udp comment "GTP-U data"
sudo ufw allow 8080/tcp comment "Web UI"
sudo ufw allow 8000/tcp comment "API (dev)"

# Verify rules added
sudo ufw status numbered
```

#### 1.5 Verify Docker Installation

```bash
docker --version
# Expected: Docker version 20.10+ or 24.x

docker-compose --version
# Expected: Docker Compose version 2.0+

docker run hello-world
# Should succeed without errors

# Verify sudo not needed (user in docker group)
groups $USER | grep docker
# If no "docker" group, add user:
sudo usermod -aG docker $USER
# Then logout/login for changes to take effect
```

### Step 2: Clone Repository

```bash
# Choose directory (e.g., /home/user/projects)
cd ~/projects

# Clone repository
git clone https://github.com/waveriders/opensurfcontrol.git
cd opensurfcontrol

# Verify structure
ls -la
# Expected:
# drwxr-xr-x daemon/
# drwxr-xr-x api/
# drwxr-xr-x frontend/
# drwxr-xr-x tests/
# -rw-r--r-- docker-compose.yml
# -rw-r--r-- .env (if provided)
```

### Step 3: Create Configuration

#### 3.1 Create .env File

```bash
# If .env exists from template, skip to 3.2
# Otherwise create:

cat > .env << 'EOF'
# Open5G2GO Configuration
# Generated: $(date)

# PLMN (Public Land Mobile Network)
PLMN_MCC=315
PLMN_MNC=010

# Device Pool (internal Docker network)
# Used for UE IP assignment
DEVICE_POOL=172.26.99.0/24
DEVICE_GATEWAY=172.26.99.1

# DNS for attached devices
DNS_1=8.8.8.8
DNS_2=8.8.4.4

# MongoDB
MONGO_INITDB_DATABASE=open5gs
EOF

cat .env
# Verify contents
```

#### 3.2 Customize .env (Optional)

Edit `.env` if your lab network uses different parameters:

```bash
nano .env
# Edit:
# - PLMN_MCC/MNC if different operator
# - DEVICE_POOL if conflicts with lab network
# - DNS_1/DNS_2 if using internal corporate DNS

# Save: Ctrl+O, Enter, Ctrl+X
```

### Step 4: Build Docker Images

```bash
# Build all images (takes 3-5 minutes)
docker-compose build

# Expected output:
# [+] Building 45.2s (42/42) FINISHED
# => [mongodb] ...
# => [open5gs-mme] ...
# => [fastapi-backend] ...
# => [opensurf-frontend] ...

# Verify images created
docker images | grep -E "open5gs|opensurfcontrol"
```

### Step 5: Start Services

```bash
# Start in background (daemon mode)
docker-compose up -d

# Expected output:
# [+] Running 5/5
#   ✔ Network open5g2go Created
#   ✔ Container open5g2go_mongodb Started
#   ✔ Container open5g2go_mme Started
#   ✔ Container open5g2go_api Started
#   ✔ Container open5g2go_frontend Started
```

### Step 6: Wait for Startup

```bash
# Monitor startup (watch logs in real-time)
docker-compose logs -f

# Watch for these key messages:
# [mongodb] waiting for connections on port 27017
# [open5gs-mme] S1AP listening on 0.0.0.0:36412
# [fastapi-backend] Application startup complete
# [opensurf-frontend] Built successfully

# Startup takes ~60-90 seconds
# Press Ctrl+C when all services show "healthy"
```

### Step 7: Verify All Services

```bash
# Check service health
docker-compose ps

# Expected output:
# NAME                     STATUS
# open5g2go_mongodb        Up 2 min (healthy)
# open5g2go_mme            Up 1 min 50s (healthy)
# open5g2go_api            Up 1 min 40s (healthy)
# open5g2go_frontend       Up 1 min 30s (healthy)

# All should show "healthy", not "(health: starting)"
# If not, wait 30 more seconds and re-run
```

### Step 8: Record NUC IP for Future Reference

```bash
# Get NUC's DHCP IP
NUC_IP=$(ip addr show eth0 | grep "inet " | awk '{print $2}' | cut -d/ -f1)

# Save to file for easy reference
echo "NUC_IP=$NUC_IP" >> ~/.bashrc

# Display and save
echo "Open5G2GO NUC IP: $NUC_IP"
echo "Web UI: http://$NUC_IP:8080"
echo "API: http://$NUC_IP:8000/api"
echo ""
echo "For eNodeB S1AP: Configure target as $NUC_IP:36412 (SCTP)"
```

---

## eNodeB Configuration

### Baicells eNodeB Setup

**Prerequisite:** eNodeB and NUC on same lab network (can ping each other)

#### Step 1: Discover eNodeB IP

```bash
# From NUC, discover eNodeB IP
# Option A: Scan network
nmap -sn 192.168.1.0/24
# Look for "Baicells" or unknown device

# Option B: Check lab network DHCP server logs
# (Ask network admin for eNodeB IP)

# Option C: Physical console
# (Login to eNodeB physically, check network settings)

ENODEB_IP="192.168.1.40"  # Example, replace with actual
echo "eNodeB IP: $ENODEB_IP"
```

#### Step 2: Verify Connectivity

```bash
# Ping eNodeB from NUC
ping -c 3 $ENODEB_IP
# Should receive 3 pong responses

# If no response, check:
# - eNodeB powered on
# - Network cable connected
# - Same lab network (same subnet mask)
```

#### Step 3: Access eNodeB Web UI

```bash
# From admin machine on lab network:
# Open browser: http://$ENODEB_IP
# (May require default credentials, check Baicells docs)

# Navigate to:
# Network → S1AP Configuration
# OR
# Settings → Core Network → S1AP Server

# Note: Interface varies by Baicells model/firmware
```

#### Step 4: Configure S1AP Target

In eNodeB UI, find S1AP configuration section:

```
Field: S1AP Server IP        Value: <NUC_IP>  (e.g., 192.168.1.50)
Field: S1AP Port             Value: 36412     (SCTP port)
Field: S1AP Transport        Value: SCTP      (NOT TCP)
Field: GTP-U Server IP       Value: <NUC_IP>  (same as above)
Field: GTP-U Port            Value: 2152      (UDP)
Field: GTP-U Bind Interface  Value: eth0 or auto

Click: Save / Apply / Confirm
```

#### Step 5: Verify S1AP Handshake

On NUC, monitor S1AP connection:

```bash
# Option A: Watch MME logs
docker-compose logs -f open5gs-mme | grep -i "s1ap"

# Look for messages like:
# [mme] S1Setup from eNodeB accepted
# [mme] Registered eNodeB 0xbaicells123456

# Option B: Check if port is accessible
nc -vz <ENODEB_IP> 36412 -u 2152
# Should show "open" (connection possible)

# Handshake takes 5-15 seconds after eNodeB restart
```

#### Step 6: Monitor eNodeB Registration

```bash
# From eNodeB web UI, check:
# Status → eNodeB Status → Core Connection Status
# Should show: "Connected" (not "Connecting")

# Or from NUC:
docker exec open5g2go_mme bash -c "netstat -tlnp | grep 36412"
# Should show a connection established
```

---

## Verification & Testing

### Test 1: API Health Check

```bash
# Get NUC IP
NUC_IP=$(ip addr show eth0 | grep "inet " | awk '{print $2}' | cut -d/ -f1)

# Test API
curl -X GET http://$NUC_IP:8000/api/health

# Expected response:
# {"status": "healthy", "timestamp": "2025-12-27T12:34:56Z"}
```

### Test 2: Web UI Access

```bash
# From admin machine on lab network:
# Open browser: http://<NUC_IP>:8080

# You should see:
# - openSurfControl dashboard
# - Network status panel
# - Device management section
# - (Empty device list initially)
```

### Test 3: Add Test Device (via API)

```bash
NUC_IP=$(ip addr show eth0 | grep "inet " | awk '{print $2}' | cut -d/ -f1)

# Add a device
curl -X POST http://$NUC_IP:8000/api/devices \
  -H "Content-Type: application/json" \
  -d '{
    "name": "TEST-DEVICE-01",
    "imsi": "315010000000001",
    "k": "465b5ce8b199b49faa5f0a2ee238a6bc",
    "opc": "cd63cb13d44e6b4a3ecb76d56b313508"
  }'

# Expected response:
# {
#   "subscriber_id": "...",
#   "imsi": "315010000000001",
#   "name": "TEST-DEVICE-01",
#   "status": "provisioned"
# }
```

### Test 4: Verify Device in MongoDB

```bash
# Connect to MongoDB (from NUC)
docker exec open5g2go_mongodb mongo \
  --eval "db.open5gs.subscribers.findOne()"

# Alternative: Use MongoDB Compass (GUI)
# Connection: mongodb://localhost:27017/open5gs
```

### Test 5: Monitor eNodeB Attachment (with real device)

If you have a physical UE/device:

```bash
# Configure device IMSI, K, OPC to match provisioned entry
# Connect device to eNodeB
# Monitor MME logs:

docker-compose logs -f open5gs-mme | grep -i "attach"

# You should see:
# [mme] UE 315010000000001 attached
# [mme] Assigned IP: 172.26.99.10
```

---

## Troubleshooting

### Issue: Services Not Starting

**Symptoms:** `docker-compose ps` shows some containers not running or "(health: starting)"

**Diagnosis:**

```bash
docker-compose logs

# Look for errors like:
# - "port already in use"
# - "MongoDB connection refused"
# - "module not found"
```

**Solutions:**

```bash
# Option 1: Kill existing containers
docker-compose down
docker-compose up -d

# Option 2: Free up ports (if port conflict)
sudo netstat -tlnp | grep -E "36412|2123|2152|8000|8080"
# If occupied by other service, stop it or change port in docker-compose.yml

# Option 3: Rebuild if code changed
docker-compose down
docker-compose build
docker-compose up -d
```

### Issue: eNodeB Cannot Connect to S1AP

**Symptoms:** eNodeB shows "Connecting" (not "Connected"), no S1Setup messages in logs

**Diagnosis:**

```bash
# 1. Verify NUC IP is correct
NUC_IP=$(ip addr show eth0 | grep "inet " | awk '{print $2}' | cut -d/ -f1)
echo $NUC_IP
# Make sure this matches eNodeB S1AP config

# 2. Verify S1AP port is listening
docker-compose ps open5gs-mme
# Should show "healthy"

# 3. Verify firewall allows SCTP
sudo netstat -tlnp | grep 36412
# Should show "SCTP" listening on 0.0.0.0:36412

# 4. Verify eNodeB can reach NUC
ssh eNodeB 'ping -c 1 $NUC_IP'
# Should succeed (requires eNodeB SSH access)

# 5. Check netfilter rules
sudo iptables -L -n | grep 36412
# Should show port forwarding rules
```

**Solutions:**

```bash
# Solution 1: Check eNodeB config again
# - Verify S1AP IP matches NUC DHCP IP (not hardcoded old IP)
# - Verify port is 36412 (not typo)
# - Verify protocol is SCTP (not TCP)
# - Restart eNodeB after config change

# Solution 2: Check firewall
sudo ufw allow 36412/sctp
sudo ufw reload

# Solution 3: Monitor MME startup
docker-compose logs open5gs-mme | grep -i "s1ap\|listen"
# Should show "S1AP listening on 0.0.0.0:36412"

# Solution 4: Restart MME container
docker-compose restart open5gs-mme
# Wait 30s, then check eNodeB
```

### Issue: API Unreachable

**Symptoms:** `curl http://<nuc-ip>:8000/api/health` fails with "Connection refused"

**Diagnosis:**

```bash
# 1. Check if FastAPI container is running
docker-compose ps open5gs-api

# 2. Check logs
docker-compose logs fastapi-backend | tail -20

# 3. Verify port binding
docker port open5g2go_api
# Should show "8000/tcp -> 0.0.0.0:8000"
```

**Solutions:**

```bash
# Solution 1: Restart FastAPI
docker-compose restart fastapi-backend
sleep 10
curl http://localhost:8000/api/health

# Solution 2: Check if MongoDB is ready
docker-compose logs mongodb | grep "waiting for connections"

# Solution 3: Rebuild if code changed
docker-compose build fastapi-backend
docker-compose restart fastapi-backend
```

### Issue: Web UI Blank Page

**Symptoms:** Opens http://<nuc-ip>:8080 but page is blank or shows error

**Diagnosis:**

```bash
# 1. Check frontend container
docker-compose ps opensurf-frontend

# 2. Check browser console (F12 → Console tab)
# Look for JavaScript errors or API failures

# 3. Check frontend logs
docker-compose logs opensurf-frontend | tail -20

# 4. Test API reachability from frontend
docker exec open5g2go_frontend curl http://fastapi-backend:8000/api/health
```

**Solutions:**

```bash
# Solution 1: Clear browser cache and reload
Ctrl+Shift+R (hard refresh)

# Solution 2: Rebuild frontend
docker-compose build opensurf-frontend
docker-compose restart opensurf-frontend

# Solution 3: Check API URL config
# In docker-compose.yml, verify:
# REACT_APP_API_URL=http://localhost:8000/api
# (change localhost to NUC IP if accessing from remote)
```

### Issue: Device Not Getting IP

**Symptoms:** eNodeB shows UE attached but no IP assigned (or fails to attach)

**Diagnosis:**

```bash
# 1. Check if subscriber provisioned
docker exec open5g2go_mongodb mongo \
  --eval "db.open5gs.subscribers.find({imsi: '315010000000001'})"

# 2. Check MME logs for SGW errors
docker-compose logs open5gs-mme | grep -i "gtp\|sgw"

# 3. Check if device pool is exhausted
docker-compose logs open5gs-mme | grep -i "pool\|ip.*full"
```

**Solutions:**

```bash
# Solution 1: Provision device first
# Use web UI or API to add device with matching IMSI

# Solution 2: Check device pool size
# In .env, verify: DEVICE_POOL=172.26.99.0/24 (256 total, ~250 usable)
# If more devices needed, expand pool in Phase 2

# Solution 3: Restart Open5GS
docker-compose restart open5gs-mme
# Wait 30s, then try UE attach again
```

### Issue: Cannot SSH to NUC

**Symptoms:** `ssh <nuc-user>@<nuc-ip>` fails with "Connection refused"

**Diagnosis:**

```bash
# 1. Verify NUC IP is correct
# Check lab network DHCP server or physical console

# 2. Verify NUC is on network
ping <nuc-ip>
# Should succeed

# 3. Verify SSH is enabled
# (Usually enabled by default on Ubuntu)
```

**Solutions:**

```bash
# Solution 1: Use physical console instead
# (Connect monitor, keyboard to NUC)

# Solution 2: Enable SSH on NUC (if disabled)
sudo systemctl enable ssh
sudo systemctl start ssh

# Solution 3: Check firewall allows SSH
sudo ufw allow 22/tcp
```

### Issue: Port Already in Use

**Symptoms:** `docker-compose up -d` fails with "port 36412 already allocated"

**Diagnosis:**

```bash
# Find what's using the port
sudo netstat -tlnp | grep 36412
# OR
sudo lsof -i :36412
```

**Solutions:**

```bash
# Solution 1: Stop the conflicting service
# (Depends on what's using it; check diagnosis output)

# Solution 2: Use different host port (not recommended for S1AP)
# Edit docker-compose.yml:
# - "36413:36412/sctp"  # Use 36413 on host, 36412 in container
# Then update eNodeB config to use 36413

# Solution 3: Wait if port in TIME_WAIT state
# TIME_WAIT is temporary; wait 30-60s and retry
```

---

## Cleanup & Teardown

### Stop Services (Preserve Data)

```bash
# Stop all containers (data persisted in volumes)
docker-compose down

# Later, restart without rebuilding:
docker-compose up -d
```

### Full Cleanup (Delete Everything)

```bash
# WARNING: This deletes all subscriber data!
# Only do this for lab resets

docker-compose down -v

# Also clean up images (optional)
docker rmi -f $(docker images | grep "open5gs\|opensurfcontrol" | awk '{print $3}')
```

### Cleanup Specific Components

```bash
# Delete only MongoDB data (keep containers)
docker-compose exec mongodb mongo --eval "db.dropDatabase()"

# Delete only logs
docker volume rm open5gs_logs

# Delete container but keep volumes
docker-compose down --remove-orphans
```

---

## Monitoring & Operations

### Daily Health Check

```bash
# Automated health check script
cat > check_health.sh << 'EOF'
#!/bin/bash

NUC_IP=$(hostname -I | awk '{print $1}')

echo "=== Open5G2GO Health Check ==="
echo "Time: $(date)"
echo ""

echo "1. Docker Services:"
docker-compose ps

echo ""
echo "2. API Health:"
curl -s http://localhost:8000/api/health | jq .

echo ""
echo "3. Subscriber Count:"
docker exec open5g2go_mongodb mongo \
  --eval "db.open5gs.subscribers.count()" 2>/dev/null

echo ""
echo "4. S1AP Status:"
docker-compose logs open5gs-mme 2>/dev/null | \
  grep -i "s1ap\|registered" | tail -3

echo ""
echo "5. Web UI Access:"
echo "http://$NUC_IP:8080"

echo ""
echo "=== End Health Check ==="
EOF

chmod +x check_health.sh
./check_health.sh
```

### View Live Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f open5gs-mme

# Last 50 lines
docker-compose logs --tail=50 fastapi-backend

# Since specific time
docker-compose logs --since "5m"  # Last 5 minutes
```

### Performance Monitoring

```bash
# Resource usage
docker stats

# Container disk usage
docker system df

# Network traffic
iftop -i eth0  # (if installed)
```

---

## Support & Documentation

### Logs Location (Inside Containers)

```
Container: open5gs-mme
Path: /var/log/open5gs/mme.log
Path: /var/log/open5gs/hss.log

Container: fastapi-backend
Console: docker-compose logs fastapi-backend

Container: mongodb
Console: docker-compose logs mongodb
```

### External References

- Open5GS: https://open5gs.org
- Docker Compose: https://docs.docker.com/compose/
- Baicells: https://www.baicells.com
- This design: See main design document `2025-12-27-open5g2go-docker-compose-design.md`

### Contact & Issues

- Report issues: GitHub Issues (if public repo)
- Ask questions: Waveriders Slack / Forum
- Commercial support: https://waveriders.io

---

**Deployment Complete!**

Your Open5G2GO system is now ready for:
1. Lab testing with real eNodeB
2. Device provisioning and management
3. Performance benchmarking
4. Field deployment planning

**Next Steps:**
- Add more devices via Web UI
- Monitor logs for insights
- Plan Phase 2 features (HA, advanced QoS, etc.)
- Prepare field deployment documentation

