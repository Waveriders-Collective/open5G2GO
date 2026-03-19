# 5G SA Core Integration Testing Report

**Date**: 2026-03-17
**Engineer**: Jeremy Rollinson
**Branch**: `feature/5g-sa-core-support`
**Core Version**: Open5GS 2.7.6
**Docker Image**: `ghcr.io/waveriders-collective/open5g2go-open5gs:feature-5g-sa-core-support`

---

## Test Environment

| Component | Details |
|-----------|---------|
| Core Host | Proxmox VM 100 ("wavedock"), Debian 13 Trixie, 12GB RAM, 50GB disk |
| Proxmox Host | `root@192.168.8.10` (ssh -i ~/.ssh/github_waverider) |
| Core VM | `waveriders@192.168.8.5` (ssh -i ~/.ssh/github_waverider) |
| gNB | Askey, management IP 192.168.8.50 |
| PLMN | 999-70 (MCC: 999, MNC: 70, 2-digit) |
| SIM Cards | Sysmocom sysmoISIM-SJA5 (programmed via SurfSIM/grsimwrite), Seneca pre-programmed SIMs |
| UE IP Pool | 10.48.99.0/24, gateway 10.48.99.1, DNN "internet" |
| SurfSIM | v0.2.0b1, running on core host port 8808 |

---

## 1. PLMN Configuration

### What We Did
Changed PLMN from the wizard-configured 999-01 to 999-70 to match the pre-configured SIMs and radio.

### Files Modified (on host, not in repo)
- `open5gs/config/amf.yaml` — 3 places: guami, tai, plmn_support
- `open5gs/config/nrf.yaml` — 1 place: serving

### What We Learned
- The setup wizard writes PLMN to AMF and NRF configs only (5G SA mode)
- MME config has separate PLMN (4G only, irrelevant for SA)
- Changes require container restart but NOT a full stack rebuild
- MongoDB subscriber data is independent of PLMN config

---

## 2. Subscriber Provisioning

### Seneca Pre-Programmed SIMs (from CSV)
Added 4 subscribers from `seneca-sims-08082025.csv`:

| IMSI | Ki | OPc | MSISDN |
|------|----|----|--------|
| 999700000009480 | E481A8684ED8473A931FC83B052ED123 | EDABB937F91996AEA689FD8ED3D6D4F4 | 447369029369 |
| 999700000009481 | 3CB61DE48F7E415CADCFD4D07F75FC42 | 09E320D7A1B5F65A239CDC675BB232EA | 447369029370 |
| 999700000009482 | 238FCE5300624398A37780B53BF7D2F3 | E788E3C872F8478A8F971D030A0E23A2 | 447369029371 |
| 999700000009483 | 4F1984F0032F4E34AD0F13DBB0E42E20 | DE256845255655477E7E9A9E7CDAED31 | 447369029372 |

**STATUS: AUTH FAILING** — All 4 Seneca SIMs get MAC failure during 5G-AKA authentication. SUCI decryption works (key ID 30 resolved correctly, IMSI visible in UDM debug logs), but the Ki/OPc values from the CSV produce incorrect auth vectors. We tried both `op_type: 2` (OPc) and `op_type: 0` (OP) — neither works. The `amf` (Authentication Management Field) is set to `8000` but the supplier may use a different value. **Needs verification with Seneca.**

### SurfSIM-Programmed SIM
- IMSI: 999700308170001
- Ki: programmed via SurfSIM
- OPc: programmed via SurfSIM

**STATUS: AUTH WORKING** — Successfully registered, authenticated via 5G-AKA, PDU session established.

### MongoDB Subscriber Schema
```javascript
{
  schema_version: 1,
  imsi: "999700000009481",
  msisdn: ["447369029370"],
  security: {
    k: "3CB61DE48F7E415CADCFD4D07F75FC42",
    amf: "8000",
    op_type: 2,        // 2 = OPc, 0 = OP
    op_value: "09E320D7A1B5F65A239CDC675BB232EA",
    op: null
  },
  ambr: {
    downlink: {value: 1, unit: 3},
    uplink: {value: 1, unit: 3}
  },
  slice: [{
    sst: 1,
    default_indicator: true,
    session: [{
      name: "internet",
      type: 3,
      ambr: {downlink: {value: 1, unit: 3}, uplink: {value: 1, unit: 3}},
      qos: {
        index: 9,
        arp: {priority_level: 8, pre_emption_capability: 1, pre_emption_vulnerability: 1}
      }
    }]
  }]
}
```

---

## 3. SCTP / NGAP — AMF Must Be Host Mode

### The Problem
Docker NAT completely breaks SCTP for NGAP. The gNB establishes a 4-way SCTP handshake, then immediately sends SHUTDOWN before the NG Setup Request. This happens because SCTP is a multi-homed protocol that validates source addresses — Docker's NAT changes the source, and the gNB rejects it.

### Debug Evidence
```
gNB-N2 accepted[192.168.8.50]
SCTP_ASSOC_CHANGE:[T:32769, F:0x0, S:0, I/O:10/30]
SCTP_COMM_UP
SCTP_SHUTDOWN_EVENT:[T:32773, F:0x0, L:12]    ← SAME MILLISECOND
AMF_EVENT_NGAP_LO_CONNREFUSED
gNB-N2[192.168.8.50] connection refused!!!
```

### The Fix
AMF runs with `network_mode: host` in docker-compose. This means:
- **Remove** `ports:` section (host ports used directly)
- **Remove** `networks:` section (incompatible with host mode)
- AMF SBI server address → `172.26.0.1` (Docker bridge gateway IP)
- NRF client URI stays → `http://172.26.0.30:7777` (host can reach bridge network)
- NGAP listens on `0.0.0.0:38412` directly on host
- Other NFs discover AMF through NRF, which advertises `172.26.0.1:7777`

### What NOT to Do
- Don't try to port-forward SCTP through Docker — it fundamentally doesn't work with SCTP's multi-homing
- Don't set AMF SBI to `0.0.0.0` — it needs a specific IP that other containers can route to

---

## 4. GTP-U — UPF Must Be Host Mode

### The Problem
With Docker port-mapped UPF (2152/udp), the GTP-U downlink packets reach the gNB with source IP `172.26.0.x` (Docker bridge) instead of `192.168.8.5` (the external IP the gNB expects). The gNB drops these packets silently.

### Debug Evidence
```
# tcpdump on ens18 showed:
IP 172.26.0.1.2152 > 192.168.8.50.2152: UDP    ← WRONG SOURCE
# Should be:
IP 192.168.8.5.2152 > 192.168.8.50.2152: UDP
```

Uplink worked fine (UE → gNB → host:2152 → Docker NAT → UPF container) because the source IP doesn't matter for uplink. But downlink replies came back from the wrong source.

### The Fix
UPF runs with `network_mode: host`:
- **Remove** `ports:` section
- **Remove** `networks:` section
- **Remove** `sysctls:` section (can't set sysctls in host network namespace, host already has `ip_forward=1`)
- GTP-U server address → `192.168.8.5` (host's external IP, or could use `0.0.0.0`)
- PFCP server address → `172.26.0.1` (bridge gateway, so SMF can reach it)
- **Remove** `advertise:` field from gtpu config (not needed in host mode)
- **Update SMF** PFCP client address to `172.26.0.1` (was `172.26.0.15`)

### UPF Config After Fix
```yaml
upf:
  pfcp:
    server:
      - address: 172.26.0.1
    client:
      smf:
        - address: 172.26.0.14
  gtpu:
    server:
      - address: 192.168.8.5
  session:
    - subnet: 10.48.99.0/24
      gateway: 10.48.99.1
      dnn: internet
      dev: ogstun
```

---

## 5. iptables / Forwarding Rules

### The Problem
Docker sets the FORWARD chain policy to DROP. Even with UPF in host mode, traffic from ogstun (UE subnet) to ens18 (external) is blocked. Also, the UPF container's built-in MASQUERADE rule (`! -o ogstun`) doesn't reliably NAT traffic going out ens18 in host mode.

### Required Rules
```bash
# Allow forwarding between ogstun and external interface
iptables -I FORWARD 1 -i ogstun -o ens18 -j ACCEPT
iptables -I FORWARD 2 -i ens18 -o ogstun -m state --state RELATED,ESTABLISHED -j ACCEPT

# NAT UE traffic going to external network
iptables -t nat -A POSTROUTING -s 10.48.99.0/24 -o ens18 -j MASQUERADE
```

### Action Required for Codebase
These rules need to be applied automatically. Options:
1. Add to UPF container entrypoint script (preferred — keeps it with the service)
2. Add to host startup script
3. Add a systemd service on the host

**Note**: The host does NOT have `iptables` binary — it uses `nft` backend accessed through Docker's iptables compatibility layer. The `sudo iptables` commands work because Docker installs iptables-nft.

---

## 6. SUCI / SUPI Concealment

### Background
5G SA requires SUCI (Subscription Concealed Identifier). The SIM encrypts the IMSI using a Home Network Public Key before sending over the air. The UDM needs the corresponding private key to decrypt.

### SUCI Scheme Mapping (3GPP → Open5GS)

| SIM sends scheme ID | Open5GS `scheme` value | Algorithm | PEM format |
|---|---|---|---|
| 30 | 1 | ECIES Profile A (X25519) | `BEGIN PRIVATE KEY` (PKCS8) |
| 48 | 2 | ECIES Profile B (P256/secp256r1) | `BEGIN EC PRIVATE KEY` (Traditional) |
| 0 | N/A | Null scheme (plaintext IMSI) | No key needed |

### CRITICAL: Key ID Must Match SIM
The `id` field in the UDM hnet config must match the key index on the SIM. The supplier told us to use `id: 30` for their X25519 key. This is NOT the same as scheme ID — it's the SIM's key_index field in `EF.SUCI_Calc_Info`.

### UDM Configuration
```yaml
udm:
  hnet:
    - id: 30          # Seneca supplier key (matches SIM key_index)
      scheme: 1       # X25519
      key: /etc/open5gs/hnet_key2.pem
    - id: 1           # Our generated key for SurfSIM-programmed cards
      scheme: 1       # X25519
      key: /etc/open5gs/hnet_key1.pem
```

Each key file must be volume-mounted into the UDM container:
```yaml
volumes:
  - ./open5gs/config/udm.yaml:/etc/open5gs/udm.yaml:ro
  - ./open5gs/config/hnet_key1.pem:/etc/open5gs/hnet_key1.pem:ro
  - ./open5gs/config/hnet_key2.pem:/etc/open5gs/hnet_key2.pem:ro
```

### Key Generation

**X25519 (Profile A):**
```python
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption

key = X25519PrivateKey.generate()
# Private → PEM file for UDM
pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
# Public → hex string for SIM programming via SurfSIM
pub_hex = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
```

**P256 (Profile B):**
```python
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption

key = ec.generate_private_key(ec.SECP256R1())
pem = key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
```

### Open5GS PEM Format Gotchas
- Scheme 1 (X25519): Expects `-----BEGIN PRIVATE KEY-----` (PKCS8 format)
- Scheme 2 (P256): Expects `-----BEGIN EC PRIVATE KEY-----` (Traditional OpenSSL format)
- If wrong format: `ogs_pem_decode_curve25519_key failed` or `ogs_pem_decode_secp256r1_key failed`
- If inline hex instead of file path: `Cannot find file [hexstring]`
- If key fails to load, `nudm-ueau` service doesn't register → all auth fails with 404

### Current Test Keys on Host

**Key 1** (our generated key for SurfSIM cards):
- Public: `b999ba50da01ce3d572e54dbf4cd508bab0aeed381101f1c04721096afdec269`
- File: `open5gs/config/hnet_key1.pem`

**Key 2** (Seneca supplier key):
- File: `open5gs/config/hnet_key2.pem` (copied from `~/Downloads/private_key_a_30.pem`)

---

## 7. SurfSIM SUCI Bug (GitHub Issue #17)

### The Bug
When SUCI is toggled OFF in SurfSIM, `program_all()` skips SUCI programming entirely (`if suci_enabled and card_cfg["suci_capable"]`). It does NOT actively disable SUCI on the SIM. The factory-default SUCI config (ECIES Profile A, scheme 30) remains intact in `EF.SUCI_Calc_Info`.

### Impact
SIMs programmed with "SUCI disabled" still send encrypted IMSI (scheme 30) to the core. The core rejects with `Cannot find SUCI [404]` and `HNET PKI Value Not Available` unless the HNET private key is configured.

### Evidence
```
SurfSIM API reads: "suci_enabled": false, "suci_schemes": [], "suci_keys": []
But UE sends: suci-0-999-70-0-1-30-<encrypted_imsi>
```

### Workaround
Configure HNET keys in UDM so the core can decrypt SUCI regardless of whether we intended to disable it.

### Proper Fix Required
When `suci_enabled=False` and card is `suci_capable`:
1. Write null-only protection scheme (identifier=0) to `EF.SUCI_Calc_Info` (ADF.USIM/DF.5GS/4F07)
2. Disable UST service 124 (clear bit 123 in EF.UST)
3. Need a new `disable_suci_service()` method (inverse of `enable_suci_service()`)

Filed as: https://github.com/Waveriders-Collective/SurfSIM/issues/17

---

## 8. SIM Programming Pitfalls

### MNC Length (EF_AD byte 4)
For 2-digit MNC (e.g., "70"), EF_AD byte 4 must be `02`. If set to `03`, the UE reads 3 digits for MNC from the IMSI.

**Example failure**: IMSI `999700308170001` with MNC length=3 → UE sends PLMN 999-700 instead of 999-70 → AMF rejects with `Cannot receive SBI message` and `Registration reject [90]`.

grsimwrite users: ensure the MNC length field is set correctly. SurfSIM handles this automatically based on the MNC value provided.

### ADM Keys
**NEVER guess or programmatically use ADM keys.** Each sysmocom SIM has a unique ADM key printed on the card holder. Wrong attempts permanently lock the card. Only enter ADM manually through SurfSIM UI.

### OP vs OPc
- `op_type: 0` = OP (raw operator key; Open5GS derives OPc from OP + Ki)
- `op_type: 2` = OPc (pre-computed; used directly)
- If supplier provides "OPC" in CSV, assume it's OPc (`op_type: 2`)
- MAC failure during auth = Ki/OPc mismatch between SIM and database

### Authentication Management Field (AMF — not the NF)
The `amf` field in the subscriber security config (default `"8000"`) is the 16-bit Authentication Management Field used in MILENAGE. Some SIM vendors use different values (e.g., `"9001"`, `"C000"`). If Ki and OPc are verified correct but auth still fails, check this value with the supplier.

---

## 9. Askey gNB Specifics

### Connection Parameters
| Parameter | Value |
|-----------|-------|
| AMF Address | 192.168.8.5:38412 (SCTP) |
| N2 Local IP | 192.168.8.50 (gNB's own IP) |
| N3 Local IP | 192.168.8.50 (same as N2, confirmed OK) |
| PLMN | 999-70 |
| TAC | 1 |
| SST | 1, SD: 0xffffff |

### SCTP Behavior
- Negotiates I/O streams: 2/2 (differs from typical 10/30)
- Source port matches destination: 38412 ↔ 38412
- NG Setup succeeds with these stream counts

### Known Issues
1. **Dashboard shows stale "connected" state** — After AMF restart, gNB dashboard may still show connected even though SCTP is down. Full gNB reboot required to force fresh SCTP INIT.
2. **Duplicate gNB entry after reconnect** — If stale SCTP state exists in AMF, reconnecting gNB creates "Number of gNBs is now 2" then immediately refuses. Fix: restart AMF to clear state.
3. **N2/N3 IP conflict** — Setting gNB N2/N3 local IP to the core's IP (192.168.8.5) causes ARP conflict. The gNB claims the IP, core VM loses network. gNB N2/N3 must be its own interface IP.
4. **Downlink data delivery failure** — Uplink (UE → internet) works. Downlink packets reach ogstun, get encapsulated in GTP-U, sent to gNB, but gNB does not deliver to UE. Under investigation — may be firmware issue, DRB setup issue, or MTU problem. gNB crashed during debugging.

---

## 10. VM / Infrastructure Issues

### DHCP vs Static IP
The VM originally used DHCP with a router reservation for 192.168.8.5. After gNB-induced crashes/reboots, the VM would get a different DHCP lease (192.168.8.206), breaking all connectivity.

**Fix**: Static IP in `/etc/network/interfaces`, dhcpcd disabled:
```
auto ens18
iface ens18 inet static
    address 192.168.8.5/24
    gateway 192.168.8.1
    dns-nameservers 8.8.8.8 8.8.4.4
```

### Proxmox Guest Agent Access
When the VM is unreachable via SSH, Proxmox guest agent (`qm guest exec`) can still execute commands:
```bash
ssh root@192.168.8.10 'qm guest exec 100 -- bash -c "command here"'
```
This was essential for debugging network issues and setting static IP when SSH was down.

---

## 11. Docker Compose Changes Summary

### Services Requiring Host Mode
| Service | Reason | Config Changes |
|---------|--------|----------------|
| AMF | SCTP multi-homing breaks through Docker NAT | SBI addr → 172.26.0.1, remove ports/networks |
| UPF | GTP-U source address must be external IP | GTP-U addr → 192.168.8.5, PFCP addr → 172.26.0.1, remove ports/networks/sysctls |

### Services Remaining on Bridge Network
NRF, SMF, UDM, AUSF, PCF, NSSF, UDR, MongoDB, Backend, Frontend — all stay on `172.26.0.0/16` bridge.

### SMF Config Change Required
PFCP client UPF address: `172.26.0.15` → `172.26.0.1` (UPF is now on host, reachable via bridge gateway)

### Host Mode Service Pattern
```yaml
service:
  network_mode: host
  # NO ports: (host ports used directly)
  # NO networks: (incompatible with host mode)
  # NO sysctls: for ip_forward (not allowed in host namespace)
  # SBI/PFCP address: 172.26.0.1 (bridge gateway)
  # External-facing address: 192.168.8.5 (or 0.0.0.0)
```

### docker-compose.5g.prod.yml Corruption Warning
Multiple `sed` edits to the compose file during testing caused structural corruption (e.g., ports line moved into depends_on). The file on the host is a working-but-fragile state. **The canonical version should be rebuilt cleanly in the repo based on these findings.**

---

## 12. End-of-Session Status

| Component | Status | Notes |
|-----------|--------|-------|
| PLMN 999-70 config | WORKING | AMF + NRF configured |
| gNB NG Setup | WORKING | Host-mode AMF, SCTP direct |
| SUCI Decryption | WORKING | HNET keys configured (id:30 X25519, id:1 X25519) |
| SurfSIM-programmed SIM auth | WORKING | 5G-AKA success, registration complete |
| Seneca SIM auth | FAILING | MAC failure — Ki/OPc or AMF value mismatch, needs supplier clarification |
| PDU Session (internet) | WORKING | 10.48.99.0/24 pool, DNN "internet" |
| Uplink data | WORKING | DNS resolves, TCP SYN exits, ICMP works on ogstun |
| Downlink data | NOT WORKING | Packets reach gNB via GTP-U but not delivered to UE. gNB crashed during investigation |
| SurfControl UI | WORKING | Shows gNB and UE status |
| Static IP | WORKING | /etc/network/interfaces, dhcpcd disabled |

---

## 13. Open Action Items

### Blocking
1. **Downlink data delivery** — Root cause unknown. Need to investigate after gNB reboot. Possible causes: GTP-U TEID mismatch in initial session (stale from pre-host-mode config), MTU issue, Askey firmware bug, or DRB setup failure.
2. **Seneca SIM auth** — Contact supplier to verify: (a) Are CSV values OP or OPc? (b) What AMF (auth management field) value do the SIMs use? (c) Are the Ki values correct for these specific ICCIDs?

### Codebase Changes Needed
3. **AMF host mode in docker-compose** — Implement cleanly in repo (not sed hacks on host)
4. **UPF host mode in docker-compose** — Same
5. **SMF PFCP address update** — Point to bridge gateway for UPF
6. **iptables rules automation** — FORWARD and MASQUERADE rules for ogstun ↔ ens18
7. **HNET key management** — Setup wizard should generate keys and configure UDM
8. **UDM volume mounts** — PEM key files need to be mounted
9. **SurfSIM SUCI fix** — Issue #17, null scheme write when disabled

### Nice to Have
10. **gNB monitoring in SurfControl** — Currently no way to see gNB details from the UI
11. **Debug logging toggle** — Easy way to switch AMF/UDM between info and debug levels
12. **Static IP configuration** — Setup wizard should configure or warn about DHCP vs static
