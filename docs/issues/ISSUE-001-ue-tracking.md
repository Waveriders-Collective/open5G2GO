# ISSUE-001: UE Registration and Connection Tracking Not Working

**Status:** Fixed (feature/ue-session-tracking branch)
**Priority:** High
**Component:** Backend / MME Log Parser
**Reported:** 2025-12-29
**Fixed:** 2025-12-29

## Problem Summary

When a UE (User Equipment) attaches to the network, SurfControl still displays:
- **0** Registered UEs
- **0** Connected Devices
- **0** Active Connections (empty table)

The provisioned device count works correctly (reads from MongoDB), but real-time UE session tracking is not implemented.

## Root Cause

The metrics are **hardcoded to 0** as placeholder values. The code comments indicate this was deferred to "Phase 2":

### 1. `web_backend/services/open5gs_service.py:338-339`
```python
"subscribers": {
    "provisioned": status.get("total_subscribers", 0),
    "registered": 0,  # Would need real-time tracking  <-- HARDCODED
    "connected": 0    # Would need real-time tracking  <-- HARDCODED
},
```

### 2. `web_backend/services/open5gs_service.py:398-403`
```python
async def get_active_connections(self) -> Dict[str, Any]:
    return {
        "timestamp": self._timestamp(),
        "total_active": 0,  # <-- HARDCODED
        "connections": [],  # <-- EMPTY
        "note": "Real-time connection tracking requires log parsing (Phase 2)"
    }
```

### 3. `opensurfcontrol/mme_client.py`
The MME log parser has a `UESession` dataclass defined (line 37-43) but **it's never used**. The parser only extracts eNodeB S1AP connections, not UE-level events.

## What Needs to Be Implemented

### Option A: Parse MME Logs for UE Events (Recommended)

Open5GS MME logs contain UE attachment events that can be parsed. Expected log patterns:

```
# UE Initial Attach
[mme] INFO: [imsi-315010000000001] Unknown UE by S_TMSI/IMSI
[mme] INFO: [imsi-315010000000001] Attach request

# Authentication
[mme] INFO: [imsi-315010000000001] Authentication response received

# Context Setup (device now registered)
[mme] INFO: [imsi-315010000000001] Initial context setup request sent
[mme] INFO: [imsi-315010000000001] UE context setup complete

# PDN Connection (session established - device connected)
[mme] INFO: [imsi-315010000000001] PDN connectivity request
[mme] INFO: [imsi-315010000000001] Session created
[mme] INFO: [imsi-315010000000001] Attached

# Detach
[mme] INFO: [imsi-315010000000001] Detach request
```

**Implementation steps:**
1. Add regex patterns to `mme_client.py` for UE events
2. Track UE state: `unknown` → `attaching` → `registered` → `connected` → `detached`
3. Maintain in-memory cache of UE sessions with timestamps
4. Update `get_active_connections()` to return real data

### Option B: Query Open5GS MongoDB Sessions Collection

Open5GS stores active sessions in MongoDB. Could query:
- `open5gs.sessions` collection for active PDN sessions
- Cross-reference with `subscribers` collection for device names

**Pros:** More reliable than log parsing
**Cons:** Need to verify schema, may not have all state info

### Option C: Use SNMP eNodeB UE Count (Partial)

The SNMP client already fetches `ue_count` from Baicells eNodeBs:
```python
# opensurfcontrol/snmp_client.py
ue_count: int  # Already implemented!
```

**Pros:** Already working
**Cons:** Only gives total count per eNodeB, not per-UE details (IMSI, IP, etc.)

## Recommended Solution

Combine approaches:
1. **SNMP UE count** for quick "connected devices" metric (already implemented, just needs wiring)
2. **MME log parsing** for detailed session list with IMSI/IP/state

## Files to Modify

| File | Changes Needed |
|------|----------------|
| `opensurfcontrol/mme_client.py` | Add UE event patterns, track sessions |
| `web_backend/services/open5gs_service.py` | Wire up real counts, remove hardcoded 0s |
| `web_backend/api/routes.py` | Possibly add new endpoint for session details |

## Testing Plan

1. Provision a subscriber in SurfControl
2. Attach UE to network (e.g., via srsUE or real device)
3. Verify dashboard shows:
   - Registered UEs: 1
   - Connected Devices: 1
   - Active Connections table shows IMSI, IP, APN

## References

- Open5GS log formats: https://open5gs.org/open5gs/docs/troubleshoot/01-simple-issues/
- MME log location: `/var/log/open5gs/mme.log` (Docker)

---

## Fix Implementation

Implemented **Option A: MME Log Parsing** in branch `feature/ue-session-tracking`.

### Changes Made

#### 1. `opensurfcontrol/mme_client.py`
- Added UE session tracking patterns based on actual MME log analysis:
  - `ENB_UE_COUNT_PATTERN` - tracks `[Added/Removed] Number of eNB-UEs is now N`
  - `MME_SESSION_COUNT_PATTERN` - tracks `[Added/Removed] Number of MME-Sessions is now N`
  - `ATTACH_EVENT_PATTERN` - captures `[IMSI] Attach request/complete`
  - `DETACH_EVENT_PATTERN` - captures `[IMSI] Detach request`
  - `UE_CONTEXT_PATTERN` - captures `ENB_UE_S1AP_ID[N] MME_UE_S1AP_ID[N]`
  - `SESSION_REMOVED_PATTERN` - captures `Removed Session: UE IMSI:[...] APN:[...]`
- Enhanced `UESession` dataclass with `apn`, `enb_ue_s1ap_id`, `mme_ue_s1ap_id`, `state`
- Added `parse_ue_sessions()` method with state machine tracking
- Added `get_ue_sessions()`, `get_ue_count()`, `get_session_count()` methods

#### 2. `web_backend/services/open5gs_service.py`
- Updated `get_system_status()` to use real counts from MME parser:
  - `registered` → `mme_parser.get_ue_count()` (eNB-UE count)
  - `connected` → `mme_parser.get_session_count()` (MME-Sessions count)
- Updated `get_active_connections()` to return real session data:
  - Parses MME logs for attached UE sessions
  - Enriches with device name and IP from MongoDB subscriber records
  - Returns IMSI, device_name, ip_address, apn, state, attached_at

### Log Patterns Used (from real MME log analysis)

```
12/29 09:13:03.229: [mme] INFO: [Added] Number of eNB-UEs is now 1
12/29 09:13:03.229: [mme] INFO: [Added] Number of MME-Sessions is now 1
12/29 09:13:03.229: [emm] INFO: [315010000000010] Attach request
12/29 09:13:03.537: [emm] INFO: [315010000000010] Attach complete
12/29 09:17:37.839: [emm] INFO: [315010000000010] Detach request
12/29 09:17:37.840: [mme] INFO: Removed Session: UE IMSI:[315010000000010] APN:[internet]
12/29 09:17:37.840: [mme] INFO: [Removed] Number of MME-Sessions is now 0
```
