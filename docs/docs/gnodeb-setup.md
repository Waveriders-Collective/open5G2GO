# gNodeB Configuration for Open5G2GO

## Overview

A gNodeB (next generation Node B) is a base station in 5G NR (New Radio) networks that handles radio transmission and reception for user equipment (UEs). To integrate a gNodeB with Open5G2GO in 5G SA mode, the gNodeB must establish a connection to the AMF (Access and Mobility Management Function) using the NGAP protocol over SCTP.

The NGAP protocol is responsible for:
- gNodeB registration and configuration
- Mobility management
- Session management
- Signaling between the gNodeB and 5G core network

## Step 1: Register Your gNodeB in Open5G2GO

Before configuring the gNodeB hardware, register it in Open5G2GO's configuration file.

### Edit the gNodeB Configuration File

Open the configuration file:

```bash
nano config/gnodebs.yaml
```

### Update the gNodeB Entry

Replace the example values with your gNodeB's actual information:

```yaml
gnodebs:
  - name: "My-gNodeB"
    ip_address: "YOUR_GNODEB_IP"       # Management IP of the gNodeB
    location: "Office Building A"      # Physical location
    enabled: true
```

| Field | Where to Find It |
|-------|------------------|
| `name` | Choose any friendly name |
| `ip_address` | Your gNodeB's management IP (check your network config) |
| `location` | Physical location description |

### Apply the Configuration

After saving the file, restart the backend service:

```bash
sudo docker compose -f docker-compose.5g.prod.yml restart backend
```

The dashboard will now recognize and monitor your gNodeB.

---

## Step 2: Gather Connection Parameters

Before configuring your gNodeB, gather the following information:

| Parameter | Value | Notes |
|-----------|-------|-------|
| AMF IP Address | Your Docker host IP (e.g., 10.48.0.110) | This is the IP address where your Open5G2GO AMF service is running |
| NGAP SCTP Port | 38412 | Standard SCTP port for NGAP protocol |
| MCC (Mobile Country Code) | 315 | US CBRS Private LTE (or your configured MCC) |
| MNC (Mobile Network Code) | 010 | Private network operator code (or your configured MNC) |
| TAC (Tracking Area Code) | 1 | Area code for location management |
| SST (Slice/Service Type) | 1 | Network slice type (1 = eMBB) |

> **Tip:** To find your Docker host IP, run `hostname -I` on your host machine or check your network configuration.

## Step 3: Configure the gNodeB Hardware

Configuration varies by gNodeB vendor. The following parameters must be set on any gNodeB to connect to Open5G2GO:

### Required Settings

| Setting | Value |
|---------|-------|
| AMF IP Address | Your Docker host IP |
| NGAP Port | 38412 |
| MCC | Your configured MCC (e.g., 315 for US CBRS, 999 for test) |
| MNC | Your configured MNC (e.g., 010, 70) |
| TAC | 1 |
| SST | 1 |

Consult your gNodeB vendor's documentation for the specific configuration interface and procedure.

### N2/N3 Interface Configuration

Some gNodeBs require **separate IP addresses** for the N2 (NGAP/signaling) and N3 (GTP-U/user plane) interfaces. If your gNodeB has separate N2 and N3 settings:

- **N2 IP**: The gNodeB's management/signaling IP (used for SCTP to AMF)
- **N3 IP**: A different IP on the gNodeB for GTP-U user plane traffic

If downlink data doesn't reach the UE but uplink works, check whether your gNodeB requires distinct N2/N3 IPs.

!!! tip
    The gNodeB will need to establish a network connection to the AMF IP address. Ensure that:
    - The gNodeB and Docker host are on the same network or have routing configured
    - Firewall rules allow traffic on port 38412 (SCTP) and 2152 (UDP)
    - The Docker host's firewall is configured to accept NGAP and GTP-U connections
    - The SCTP kernel module is loaded: `sudo modprobe sctp`

---

## Verification

### Check gNodeB Connection Status

From your Docker host, examine the AMF logs for NG Setup messages:

```bash
docker compose -f docker-compose.5g.prod.yml logs amf | grep -E "(NG-Setup|gNB)"
```

You should see output similar to:

```
amf_1  | [NGAP] NG-Setup-Request received from gNB
amf_1  | [NGAP] gNB-N2 accepted
```

The presence of **"gNB-N2 accepted"** indicates successful registration of the gNodeB.

### Additional Verification Commands

View all AMF logs:
```bash
docker compose -f docker-compose.5g.prod.yml logs amf
```

Check NF registration status:
```bash
docker compose -f docker-compose.5g.prod.yml logs nrf | grep -i "registered"
```

## Troubleshooting

### gNodeB Shows "Disconnected" Status

1. Verify the AMF IP address is correct and reachable from the gNodeB
2. Check firewall rules on the Docker host to allow port 38412 (SCTP)
3. Review the AMF logs for error messages: `docker compose -f docker-compose.5g.prod.yml logs amf`

### NG Setup Failures

1. Confirm the PLMN configuration (MCC/MNC) matches between the gNodeB and AMF
2. Verify the TAC and SST values match
3. Check that the AMF service is running: `docker compose -f docker-compose.5g.prod.yml ps`

### Network Connectivity Issues

1. Test connectivity from the gNodeB to the Docker host:
   ```bash
   ping <docker_host_ip>
   ```
2. Verify SCTP module is loaded:
   ```bash
   lsmod | grep sctp
   ```
3. Check that port 38412 is listening:
   ```bash
   ss -ln | grep 38412
   ```

!!! note
    For additional support, check the AMF logs for specific error codes and consult your gNodeB vendor's documentation.

## Next Steps

Once the gNodeB is successfully connected:

1. Provision SIM cards via the Web UI (Devices page)
2. Insert SIMs into 5G NR capable devices
3. Monitor connections on the Dashboard
4. Check the [Troubleshooting Guide](./troubleshooting.md) if devices don't connect
