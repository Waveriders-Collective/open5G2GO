# ISSUE-002: Network Config Page Shows Hardcoded Data, Lacks eNodeB Configuration Help

**Status:** Open
**Priority:** Medium
**Component:** Frontend / Backend API
**Reported:** 2025-12-29

## Problem Summary

The Network Configuration page displays **hardcoded values** from `constants.py` rather than reading from the actual Open5GS configuration files. More importantly, it lacks critical information that users need to configure their eNodeBs.

In a lab environment, SurfControl can be deployed on any private subnet. Users need to know the actual IP addresses to configure their eNodeB's S1AP and GTP settings.

## Current State

### What's Shown (Hardcoded from `constants.py`)
- PLMNID: 315010
- MCC: 315, MNC: 010
- Network Name: Open5G2GO
- TAC: 1
- Default APN: internet
- Bandwidth: 50/100 Mbps
- UE IP Pool: 10.48.99.0/24

### What's NOT Shown (But Critical for eNodeB Setup)
| Setting | Where It's Configured | What eNodeB Needs |
|---------|----------------------|-------------------|
| **MME S1AP IP** | mme.yaml binds to `0.0.0.0:36412` | Docker host IP (e.g., `10.48.0.110`) |
| **MME S1AP Port** | mme.yaml `port: 36412` | 36412 (standard) |

### The Problem
When a user deploys SurfControl on a different subnet (e.g., `192.168.1.0/24`), they need to:
1. Update the `advertise` IPs in sgwu.yaml and upf.yaml
2. Know what IP to configure in their eNodeB's MME settings

Currently, there's no way to see or configure this from the UI.

## Current Code Analysis

### `web_backend/services/open5gs_service.py:360-390`
```python
async def get_network_config(self) -> Dict[str, Any]:
    return {
        "network_identity": {
            "plmnid": PLMNID,      # From constants.py - HARDCODED
            "mcc": MCC,            # From constants.py - HARDCODED
            "mnc": MNC,            # From constants.py - HARDCODED
            ...
        },
        ...
    }
```

### Actual Open5GS Config Files
```yaml
# open5gs/config/mme.yaml
mme:
  s1ap:
    server:
      - address: 0.0.0.0  # Binds to all interfaces
        port: 36412

# open5gs/config/sgwu.yaml
sgwu:
  gtpu:
    server:
      - address: 172.26.0.13           # Internal Docker IP
        advertise: 10.48.0.110         # <-- THIS is what eNodeB uses!
```

## Proposed Solution

### 1. Add "eNodeB Configuration" Section to Network Config Page

Display the critical settings eNodeB operators need:

```
┌─────────────────────────────────────────────────────────────┐
│ eNodeB Configuration                                         │
│ Use these settings when configuring your eNodeB             │
├─────────────────────────────────────────────────────────────┤
│ MME IP Address      │ 10.48.0.110                           │
│ MME Port            │ 36412                                  │
│ PLMN ID             │ 315-010                                │
│ TAC                 │ 1                                      │
└─────────────────────────────────────────────────────────────┘
```

### 2. Read from Actual Config Files (Not Hardcoded)

Parse the YAML config files to get real values:
- `/etc/open5gs/mme.yaml` → S1AP port, PLMN, TAC, security algorithms
- `/etc/open5gs/sgwu.yaml` → GTP-U advertise IP
- `/etc/open5gs/upf.yaml` → UE subnet, gateway

### 3. Host IP Detection/Configuration

Options for determining the host IP:
1. **Environment Variable**: `HOST_IP=10.48.0.110` in docker-compose
2. **Parse from config**: Read `advertise` field from sgwu.yaml
3. **Auto-detect**: Query network interfaces (less reliable in Docker)

**Recommended**: Use environment variable `HOST_IP` with fallback to parsing config.

## Implementation Plan

### Backend Changes (`open5gs_service.py`)

```python
async def get_network_config(self) -> Dict[str, Any]:
    # Parse actual config files
    mme_config = self._parse_yaml("/etc/open5gs/mme.yaml")

    # Get host IP from env or config
    host_ip = os.getenv("HOST_IP", "10.48.0.110")

    return {
        "network_identity": {...},  # From mme.yaml
        "enodeb_config": {
            "mme_ip": host_ip,
            "mme_port": 36412,
            "plmn_id": "315-010",
            "tac": 1,
        },
        "apns": {...},
        "ip_pool": {...},
    }
```

### Frontend Changes (`NetworkConfig.tsx`)

Add new Card component:
```tsx
<Card title="eNodeB Configuration" subtitle="Use these settings for your eNodeB">
  <Table
    data={[
      { setting: "MME IP Address", value: data.enodeb_config.mme_ip },
      { setting: "MME Port", value: data.enodeb_config.mme_port },
      { setting: "PLMN ID", value: data.enodeb_config.plmn_id },
      { setting: "TAC", value: data.enodeb_config.tac },
    ]}
    columns={[
      { key: 'setting', header: 'Setting' },
      { key: 'value', header: 'Value' },
    ]}
  />
</Card>
```

### Docker Compose Changes

```yaml
services:
  backend:
    environment:
      - HOST_IP=${HOST_IP:-10.48.0.110}
```

## Files to Modify

| File | Changes |
|------|---------|
| `web_backend/services/open5gs_service.py` | Parse YAML configs, add enodeb_config |
| `web_frontend/src/pages/NetworkConfig.tsx` | Add eNodeB Configuration section |
| `web_frontend/src/types/open5gs.ts` | Add EnodebConfig type |
| `docker-compose.yml` | Add HOST_IP environment variable |
| `.env.example` | Document HOST_IP variable |

## Benefits

1. **Self-documenting**: Users see exactly what to configure in their eNodeB
2. **Environment-aware**: Works on any subnet, not just 10.48.0.x
3. **Reduces support burden**: No need to explain "what IP do I use for MME?"
4. **Professional**: Shows actual config, not hardcoded demo values

## Testing Plan

1. Deploy on test server with known HOST_IP
2. Verify Network Config page shows correct MME address
3. Configure eNodeB using displayed settings
4. Verify S1AP connection succeeds
5. Test on different subnet to confirm environment variable works

## References

- Open5GS configuration: https://open5gs.org/open5gs/docs/guide/02-building-open5gs-from-sources/
- Baicells eNodeB S1 configuration guide
- Current config files: `open5gs/config/*.yaml`
