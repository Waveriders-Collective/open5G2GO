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

## 5G UE Authentication Failures

**Symptom:** AMF logs show `Authentication failure [21]` (MAC failure)

This usually means a **SQN desync** — the SIM's sequence number is ahead of the core's. This happens when the subscriber database is reset but the SIM retains its counter.

**Fix:** Toggle airplane mode on the UE. The SIM will send an AUTS resynchronization token and the core will recover automatically on the next attempt.

If auth continues to fail, verify:
- Ki and OPc keys match between the SIM and subscriber record
- The `op_type` is correct (OPc vs OP)

## 5G Downlink Data Not Reaching UE

**Symptom:** UE registers and gets an IP, uplink works (DNS queries leave UE), but no downlink data arrives at the UE

**Checks:**

1. Verify GTP-U is flowing in both directions:
   ```bash
   sudo tcpdump -i <interface> 'udp port 2152' -n -c 10
   ```
   You should see packets in both directions between the host and gNodeB.

2. If downlink GTP-U reaches the gNodeB but data doesn't reach the UE, check:
   - **gNodeB N2/N3 IPs**: Some gNodeBs require separate IPs for signaling (N2) and user plane (N3). If both are on the same IP, downlink may silently fail.
   - **UPF advertise address**: Verify the UPF config has the correct host IP in the `advertise` field, not `0.0.0.0`.
   - **Firmware**: Update gNodeB firmware to the latest version.

3. If no downlink GTP-U leaves the host at all:
   ```bash
   sudo iptables -L FORWARD -n -v   # Check FORWARD chain for drops
   sudo iptables -t nat -L POSTROUTING -n -v   # Check NAT rules
   ```

## LAN Hosts Cannot Reach UE Devices

**Symptom:** The core host can ping a UE (e.g., 10.48.99.100) but other LAN hosts cannot

**Fix:** Add a static route on your LAN router pointing the UE subnet at the core host:

```
# On your router (example for core host at 192.168.8.5):
ip route add 10.48.99.0/24 via 192.168.8.5
```

The core host's UPF entrypoint automatically configures NAT exceptions for LAN traffic so that UE source IPs are preserved.

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
