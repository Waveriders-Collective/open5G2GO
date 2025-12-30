# eNodeB Configuration for Open5G2GO

## Overview

An eNodeB (evolved Node B) is a base station in LTE/4G networks that handles radio transmission and reception for user equipment (UEs). To integrate a Baicells eNodeB with Open5G2GO, the eNodeB must establish a connection to the MME (Mobility Management Entity) using the S1AP protocol over SCTP.

The S1AP protocol is responsible for:
- eNodeB registration and configuration
- Mobility management
- Session management
- Signaling between the eNodeB and core network

## Required Configuration Parameters

Before configuring your eNodeB, gather the following information:

| Parameter | Value | Notes |
|-----------|-------|-------|
| MME IP Address | Your Docker host IP (e.g., 10.48.0.110) | This is the IP address where your Open5G2GO MME service is running |
| MME SCTP Port | 36412 | Standard SCTP port for S1AP protocol |
| MCC (Mobile Country Code) | 315 | Mozambique country code |
| MNC (Mobile Network Code) | 010 | Mozambique network operator code |
| TAC (Tracking Area Code) | 1 | Area code for location management |

> **Tip:** To find your Docker host IP, run `hostname -I` on your host machine or check your network configuration. For Docker Desktop, this may be `127.0.0.1` or your machine's local network IP.

## Baicells Web Interface Configuration

### Step 1: Access the eNodeB Web Interface

1. Open a web browser
2. Navigate to the eNodeB's IP address (e.g., `http://192.168.1.100`)
3. Enter your login credentials (default credentials may vary by firmware version)

### Step 2: Configure MME Settings

1. Navigate to **LTE > MME Configuration**
2. In the MME IP Address field, enter your Docker host IP address
   - Example: `10.48.0.110`
3. In the SCTP Port field, enter `36412`
4. Click **Save** and **Apply** to apply the changes

!!! tip
    The eNodeB will need to establish a network connection to the MME IP address. Ensure that:
    - The eNodeB and Docker host are on the same network or have routing configured
    - Firewall rules allow traffic on port 36412 (SCTP)
    - The Docker host's firewall is configured to accept S1AP connections

### Step 3: Configure PLMN Settings

1. Navigate to **LTE > PLMN Configuration**
2. Set the following parameters:
   - **MCC (Mobile Country Code):** `315`
   - **MNC (Mobile Network Code):** `010`
3. Enable the PLMN by checking the enable checkbox or toggling the status
4. Click **Save** and **Apply**

!!! warning
    Ensure the PLMN is enabled after configuration. The eNodeB will not register if the PLMN is disabled.

### Step 4: Configure TAC (if required)

Some eNodeB configurations may require explicit TAC setting:

1. Navigate to **LTE > Cell Configuration** or similar location (varies by firmware)
2. Set the **TAC (Tracking Area Code)** to `1`
3. Click **Save** and **Apply**

## Verification

### Check eNodeB Connection Status

1. In the eNodeB web interface, look for the status indicator
2. The eNodeB should display a **"Connected"** or **"Registered"** status
3. The MME connection should show as active

### Check MME Logs for S1Setup

From your Docker host, examine the MME logs for S1Setup messages:

```bash
docker compose -f docker-compose.prod.yml logs mme | grep S1Setup
```

You should see output similar to:

```
mme_1  | [S1AP] S1-Setup-Request received from eNodeB
mme_1  | [S1AP] S1-Setup-Response sent to eNodeB
```

The presence of **"S1-Setup-Response"** indicates successful registration of the eNodeB.

### Additional Verification Commands

View all MME logs:
```bash
docker compose -f docker-compose.prod.yml logs mme
```

Check eNodeB connectivity:
```bash
docker compose -f docker-compose.prod.yml logs mme | grep -E "(eNodeB|connected|registered)"
```

## Troubleshooting

### eNodeB Shows "Disconnected" Status

1. Verify the MME IP address is correct and reachable from the eNodeB
2. Check firewall rules on the Docker host to allow port 36412 (SCTP)
3. Review the MME logs for error messages: `docker compose logs mme`

### S1Setup Failures

1. Confirm the PLMN configuration (MCC=315, MNC=010) matches the eNodeB's PLMN settings
2. Verify the eNodeB firmware is compatible with Open5G2GO
3. Check that the MME service is running: `docker compose -f docker-compose.prod.yml ps`

### Network Connectivity Issues

1. Test connectivity from the eNodeB to the Docker host:
   ```bash
   ping <docker_host_ip>
   ```
2. Verify the eNodeB can resolve the MME hostname (if using a hostname instead of IP)
3. Check routing tables on both the eNodeB and Docker host

!!! note
    For additional support, check the MME logs for specific error codes and consult the eNodeB manufacturer's documentation for your specific firmware version.

## Next Steps

Once the eNodeB is successfully connected:

1. Configure UE (User Equipment) devices to connect to the network
2. Set up HSS (Home Subscriber Server) subscriber entries for test users
3. Configure SGW (Serving Gateway) and PGW (Packet Data Network Gateway) settings as needed
4. Begin testing with UE devices and monitor performance through the Open5G2GO dashboard
