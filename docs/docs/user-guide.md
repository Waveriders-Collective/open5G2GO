# User Guide

This guide covers how to use the Open5G2GO web interface to manage your private 4G network.

## Accessing the UI

Open your browser and navigate to:

```
http://YOUR_SERVER_IP:8080
```

The interface has four main sections accessible from the sidebar:

- **Dashboard** - System overview and real-time status
- **Devices** - Subscriber/device management
- **Network** - Network configuration display
- **Services** - Core network service monitoring

---

## Dashboard

The Dashboard provides a real-time overview of your network status. Data auto-refreshes every 30 seconds.

### Stats Cards

At the top, four cards show key metrics:

| Card | Description |
|------|-------------|
| **Provisioned Devices** | Total devices added to the system |
| **Registered UEs** | Devices currently registered with the network |
| **Connected Devices** | Devices with active data sessions |
| **Connected eNodeBs** | Base stations connected via S1AP |

### System Health

Shows operational status of core components:

- **Core Status** - Whether Open5GS services are running
- **eNodeB Connection** - Whether any base station is connected
- **Active Sessions** - Whether any devices have active data sessions

### eNodeB Status

Displays connected base stations with detailed metrics (if SNMP is configured):

- **Cell** - RF status, band, frequency, TX power
- **Core** - S1AP link status, TAC, Cell ID, PCI
- **Traffic** - Connected UE count, throughput (DL/UL), PRB usage
- **Health** - Alarms, CPU utilization, RRC/E-RAB success rates

### Active Connections

Table showing currently connected devices:

| Column | Description |
|--------|-------------|
| Device Name | Friendly name you assigned |
| IMSI | International Mobile Subscriber Identity |
| IP Address | Assigned IP from UE pool |
| APN | Access Point Name |
| Status | Connection state (CONNECTED, IDLE, etc.) |

---

## Devices

The Devices page lets you manage subscribers (SIM cards) provisioned on your network.

### Viewing Devices

The main table displays all provisioned devices with:

- **Device Name** - Friendly identifier
- **IMSI** - Full 15-digit subscriber identity
- **Static IP** - Assigned IP address from the UE pool
- **APN** - Access point name (default: "internet")

Use the **search box** to filter by name, IMSI, or IP address.

### Adding a Device

1. Click the **Add Device** button (top right)
2. Fill in the form:
   - **IMSI** - Full 15-digit IMSI from your SIM card (e.g., `315010000000001`)
   - **Device Name** - Friendly name (e.g., "Camera 1")
   - **IP Address** - Optional, auto-assigned if left blank
3. Click **Add Device**

The system automatically:
- Validates the 15-digit IMSI format
- Assigns a static IP from the UE pool (based on last 4 digits of IMSI)
- Uses the K/OPc authentication keys configured during setup

### Viewing Device Details

Click the **eye icon** on any device row to see:

- Full IMSI
- Assigned IP address
- Authentication keys (K, OPc)
- QoS profile settings
- APN configuration

### Editing a Device

1. Click the **pencil icon** on the device row
2. Modify the device name or APN
3. Click **Save Changes**

Note: IMSI and IP address cannot be changed after creation.

### Deleting a Device

1. Click the **trash icon** on the device row
2. Confirm deletion in the popup

**Warning:** Deleting a device removes it from the network immediately. The device will lose connectivity.

---

## Network Configuration

The Network page displays your current network settings (read-only).

### Network Identity

Core network identifiers (configured during setup wizard):

| Setting | Description | Example |
|---------|-------------|---------|
| PLMNID | Public Land Mobile Network ID | 315010, 001010, 999990 |
| MCC | Mobile Country Code | 315, 001, 999 |
| MNC | Mobile Network Code | 010, 01, 99 |
| TAC | Tracking Area Code | 1 |

**Note:** PLMN is selected during the setup wizard and must match your SIM cards.

### eNodeB Configuration

Settings to use when configuring your base station:

| Setting | Value |
|---------|-------|
| MME IP Address | Your Docker host IP |
| MME Port | 36412 |
| PLMN ID | 315010 |
| TAC | 1 |

Copy these values to your eNodeB's configuration interface.

### Access Point Names (APNs)

Lists configured APNs with bandwidth limits:

- **APN Name** - Identifier (e.g., "internet")
- **Downlink Bandwidth** - Max download speed (Kbps)
- **Uplink Bandwidth** - Max upload speed (Kbps)

---

## Services

The Services page monitors Open5GS core network components.

### Summary Cards

Quick status overview:

| Card | Description |
|------|-------------|
| Total | Number of monitored services |
| Running | Services operating normally |
| Stopped | Services not running |
| Error | Services in error state |
| Unknown | Services with unknown status |

### Service Categories

Services are grouped by function:

**4G EPC Core:**
- **HSS** - Home Subscriber Server (authentication)
- **MME** - Mobility Management Entity (signaling)
- **SGWC** - Serving Gateway Control Plane
- **SGWU** - Serving Gateway User Plane
- **SMF** - Session Management Function
- **UPF** - User Plane Function
- **PCRF** - Policy and Charging Rules

**Management:**
- **Backend** - REST API server
- **Frontend** - Web UI
- **MongoDB** - Subscriber database

### Status Indicators

Each service shows:

- **Green dot/checkmark** - Running normally
- **Red dot/X** - Stopped or error
- **Gray dot/?** - Unknown status

Click **Refresh** to update status immediately.

---

## Common Tasks

### Provision a New SIM

1. Go to **Devices**
2. Click **Add Device**
3. Enter the full 15-digit IMSI from your SIM card
4. Give it a friendly name
5. Click **Add Device**
6. Insert SIM into your device and power on

### Check if a Device is Connected

1. Go to **Dashboard**
2. Look at the **Active Connections** table
3. Your device should appear with status "CONNECTED"

### Verify eNodeB Connection

1. Go to **Dashboard**
2. Check **System Health** > **eNodeB Connection** shows "Connected"
3. Check **eNodeB Status** section shows your base station

### Troubleshoot a Device Not Connecting

1. Go to **Devices** and verify the device is provisioned
2. Go to **Dashboard** and check if eNodeB is connected
3. Go to **Services** and verify all services are running
4. Check the [Troubleshooting Guide](./troubleshooting.md) for common issues

---

## Tips

- **Auto-refresh**: Dashboard and Services pages refresh every 30 seconds
- **Manual refresh**: Click the Refresh button on any page for immediate update
- **Search**: Use the search box on Devices page to quickly find a specific device
- **IMSI format**: Always enter the full 15-digit IMSI from your SIM card
