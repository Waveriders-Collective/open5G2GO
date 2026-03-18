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

## gNodeB NGAP Connection Issues (5G Mode)

**Symptom:** gNodeB shows "Disconnected" or no NG Setup messages in AMF logs

**Checks:**
- Verify firewall allows port 38412/SCTP
- Confirm SCTP kernel module is loaded: `lsmod | grep sctp`
- Verify PLMN matches between AMF config and gNodeB

**View AMF logs:**
```bash
docker compose -f docker-compose.5g.prod.yml logs amf | grep -E "(NG-Setup|gNB)"
```

Look for `gNB-N2 accepted` to confirm successful registration.

**Fix common issues:**
- Check that UPF advertise address matches the Docker host IP
- Verify the gNodeB is pointing to the correct AMF IP on port 38412
- Ensure the PLMN (MCC/MNC) configured on the gNodeB matches the AMF configuration

## 5G NF Registration Issues

**Symptom:** 5G network functions fail to register or services show errors

**Checks:**
- NRF must be healthy before other NFs can register
- Verify SBI connectivity on port 7777

**View NRF registration logs:**
```bash
docker compose -f docker-compose.5g.prod.yml logs nrf | grep -i "registered"
```

**Fix:**
1. Restart NRF first, wait for it to become healthy
2. Then restart the other NFs:
```bash
docker compose -f docker-compose.5g.prod.yml restart nrf
# Wait for NRF to be healthy, then restart other services
docker compose -f docker-compose.5g.prod.yml restart amf smf upf udm udr ausf pcf nssf
```

## Full Reset

!!! warning "Destructive Operation"
    This procedure deletes all subscriber data and system state. Use only when necessary.

To perform a complete reset of the system:

```bash
cd ~/open5G2GO
docker compose -f docker-compose.prod.yml down -v
./scripts/pull-and-run.sh
```

The `-v` flag removes all volumes (databases and persistent data). The system will reinitialize with default configuration on restart.
