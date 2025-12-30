# Troubleshooting

This guide covers common issues and solutions for Open5G2GO deployments.

## eNodeB S1AP Connection Issues

**Symptom:** eNodeB shows "Disconnected" or no S1Setup messages in logs

**Checks:**
- Verify firewall allows port 36412/SCTP
- Confirm SCTP kernel module is loaded: `lsmod | grep sctp`

**Fix:**
```bash
sudo modprobe sctp
```

## SCTP Module Not Loaded

**Symptom:** MME fails to start or no SCTP connections establish

**Quick Fix:**
```bash
sudo modprobe sctp
```

**Permanent Fix:**

Add `sctp` to your kernel modules file to load it on boot:

```bash
echo "sctp" | sudo tee -a /etc/modules
```

## Port Conflicts

**Symptom:** Container fails to start with "port already in use" error

**Check which ports are in use:**
```bash
ss -tuln | grep -E '36412|2152|8080'
```

**Fix:**
- Stop the conflicting service, or
- Modify the port mapping in `docker-compose.prod.yml`

## Docker Permission Errors

**Symptom:** "permission denied" when running docker commands

**Fix:**
```bash
sudo usermod -aG docker $USER && newgrp docker
```

You may need to log out and back in for the group membership to take effect.

## Subscriber Not Getting IP

**Symptom:** Device connects successfully but cannot access data

**Checks:**
- Review UPF (User Plane Function) logs for PFCP session establishment
- Verify subscriber exists in the database via the Web UI
- Confirm correct APN configuration

**View logs:**
```bash
docker compose -f docker-compose.prod.yml logs upf
```

## Viewing Logs

### All Services
```bash
docker compose -f docker-compose.prod.yml logs -f
```

### Specific Service
```bash
docker compose -f docker-compose.prod.yml logs mme
```

### Backend API
```bash
docker compose -f docker-compose.prod.yml logs backend
```

Use the `-f` flag to follow logs in real-time. Use `--tail=100` to view the last 100 lines.

## Full Reset

!!! warning "Destructive Operation"
    This procedure deletes all subscriber data and system state. Use only when necessary.

To perform a complete reset of the system:

```bash
cd ~/openSurfcontrol
docker compose -f docker-compose.prod.yml down -v
./scripts/pull-and-run.sh
```

The `-v` flag removes all volumes (databases and persistent data). The system will reinitialize with default configuration on restart.
