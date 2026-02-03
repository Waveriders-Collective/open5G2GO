# Operations Guide

This guide covers common operational tasks for maintaining your Open5G2GO deployment.

## Upgrading Open5G2GO

When a new version of Open5G2GO is released, you can upgrade your deployment using one of two methods.

### Method 1: Using the Installer (Recommended)

If you originally installed using the one-liner, run it again:

```bash
curl -fsSL https://raw.githubusercontent.com/Waveriders-Collective/open5G2GO/main/install.sh | bash
```

The installer detects existing installations and prompts you to choose:
- **Update** - Pull latest code and images, restart services
- **Remove** - Stop services and remove the installation
- **Quit** - Exit without changes

### Method 2: Using the Update Script

If you cloned the repository manually, use the update script:

```bash
cd /path/to/open5G2GO
./scripts/update.sh
```

The update script performs these steps:
1. Pulls latest code via `git pull`
2. Pulls latest Docker images
3. Restarts all services
4. Waits for backend health check

### What Happens During Upgrade

| Component | Behavior |
|-----------|----------|
| Configuration (.env) | Preserved - not modified |
| eNodeB Config | Preserved - not modified |
| Subscriber Data (MongoDB) | Preserved - stored in Docker volume |
| Docker Images | Updated to latest versions |
| Application Code | Updated to latest version |

### Verifying the Upgrade

After upgrading, verify your deployment:

```bash
# Check container status
docker compose -f docker-compose.prod.yml ps

# Check API health
curl http://localhost:8080/api/v1/health

# Check logs for errors
docker compose -f docker-compose.prod.yml logs --tail=50
```

## Network Reconfiguration

If you move your Docker host to a new network or need to change the host IP address, use the setup wizard's network reconfiguration mode.

### When to Use Network Reconfiguration

- Docker host IP address has changed
- Moving the deployment to a different network
- Changing the UE IP pool subnet
- eNodeB needs to connect to a different IP

### Running Network Reconfiguration

```bash
./scripts/setup-wizard.sh
```

When the wizard detects an existing configuration, it offers three options:

```
Existing Open5G2GO configuration detected!

What would you like to do?
  [1] Full Setup - Complete reconfiguration (backs up existing settings)
  [2] Network Reconfiguration - Update host IP/network only (preserves SIM, PLMN, eNodeBs)
  [3] Cancel
```

Select option **2** for Network Reconfiguration.

### What Gets Updated

| Setting | Network Reconfig | Full Setup |
|---------|------------------|------------|
| Docker Host IP | Updated | Updated |
| UE Pool Subnet | Updated | Updated |
| SGWU Advertise IP | Updated | Updated |
| PLMN (MCC/MNC) | Preserved | Updated |
| SIM Keys (Ki/OPc) | Preserved | Updated |
| eNodeB Config | Preserved | Updated |
| Docker GID | Preserved | Updated |

### After Network Reconfiguration

After reconfiguring network settings, restart the stack:

```bash
docker compose -f docker-compose.prod.yml down
./scripts/pull-and-run.sh
```

The `pull-and-run.sh` script will:
1. Reapply host networking rules (IP forwarding, routes, NAT)
2. Start all services with the new configuration

### Update eNodeB Configuration

After changing the host IP, update your eNodeB to connect to the new IP:

1. Access your eNodeB management interface
2. Update the MME IP address to your new `DOCKER_HOST_IP`
3. The eNodeB should reconnect automatically

## Full Reconfiguration

Use full setup when you need to change settings that network reconfiguration preserves.

### When to Use Full Setup

- Changing PLMN (MCC/MNC) for different SIM cards
- Updating SIM authentication keys (Ki/OPc)
- Reconfiguring eNodeBs from scratch
- Starting fresh with new settings

### Running Full Setup

```bash
./scripts/setup-wizard.sh
```

Select option **1** (Full Setup) when prompted.

Your existing `.env` file is backed up to `.env.backup` before the wizard generates a new configuration.

### Restoring Previous Configuration

If you need to revert to your previous configuration:

```bash
# Stop services
docker compose -f docker-compose.prod.yml down

# Restore backup
cp .env.backup .env

# Restart services
./scripts/pull-and-run.sh
```

## Data Persistence

Understanding what data persists across different operations helps you plan maintenance activities.

### Persistent Data Locations

| Data | Storage | Location | Survives Upgrade | Survives Reconfig |
|------|---------|----------|------------------|-------------------|
| Subscribers | MongoDB | `mongodb_data` volume | Yes | Yes |
| Open5GS Logs | Files | `open5gs_logs` volume | Yes | Yes |
| Configuration | .env file | Project root | Yes | Updated |
| eNodeB Config | YAML file | `config/enodebs.yaml` | Yes | Preserved* |
| FreeDiameter Certs | PEM files | `open5gs/config/freeDiameter/` | Yes | Yes |

*Network reconfiguration preserves eNodeB config; full setup regenerates it.

### Docker Volumes

Open5G2GO uses Docker named volumes for persistent data:

```bash
# List volumes
docker volume ls | grep open5g

# Inspect a volume
docker volume inspect open5g2go_mongodb_data
```

### Backing Up Data

Before major changes, back up your data:

```bash
# Backup .env
cp .env .env.backup.$(date +%Y%m%d)

# Backup eNodeB config
cp config/enodebs.yaml config/enodebs.yaml.backup.$(date +%Y%m%d)

# Backup MongoDB (while running)
docker compose -f docker-compose.prod.yml exec mongodb mongodump --out /dump
docker cp $(docker compose -f docker-compose.prod.yml ps -q mongodb):/dump ./mongodb_backup_$(date +%Y%m%d)
```

### Restoring MongoDB Data

To restore a MongoDB backup:

```bash
# Copy backup into container
docker cp ./mongodb_backup_YYYYMMDD $(docker compose -f docker-compose.prod.yml ps -q mongodb):/dump

# Restore
docker compose -f docker-compose.prod.yml exec mongodb mongorestore /dump
```

## Troubleshooting Operations

### Upgrade Fails to Pull Images

If Docker image pulls fail:

```bash
# Check Docker Hub connectivity
docker pull hello-world

# Try pulling manually
docker compose -f docker-compose.prod.yml pull --ignore-pull-failures

# Check disk space
df -h
```

### Services Don't Start After Reconfiguration

If services fail to start after network reconfiguration:

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs

# Verify .env was generated
cat .env | grep DOCKER_HOST_IP

# Ensure networking rules were applied
sudo ip route | grep 10.48.99
sudo iptables -t nat -L | grep MASQUERADE
```

### eNodeB Won't Reconnect

If your eNodeB doesn't reconnect after IP change:

1. Verify MME is listening:
   ```bash
   docker compose -f docker-compose.prod.yml logs mme | grep S1AP
   ```

2. Check the eNodeB can reach the new IP:
   ```bash
   # From eNodeB network, test connectivity
   nc -zv YOUR_NEW_IP 36412
   ```

3. Verify SCTP is working:
   ```bash
   ss -ln | grep 36412
   ```
