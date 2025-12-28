# Open5G2GO Docker Compose Design - Executive Summary

**Date:** 2025-12-27
**Version:** 1.0
**Status:** Design Ready for Implementation

---

## Overview

This design document package specifies a **production-ready docker-compose architecture** for Open5G2GO - a complete 4G LTE private network system combining Open5GS core, openSurfControl management UI, and MongoDB persistence.

**Key Innovation:** DHCP-agnostic NUC deployment that works in any lab network (192.168.x.x, 10.x.x.x, etc.) with zero static IP configuration required on the host.

---

## Design Deliverables

### 1. Main Architecture Document
**File:** `2025-12-27-open5g2go-docker-compose-design.md`

**Contains:**
- Complete network topology with DHCP support
- 5 service definitions (MongoDB, Open5GS, FastAPI, Frontend, implicit daemon)
- Network configuration strategy (two networks: lab DHCP + Docker internal)
- Volume mount strategy for persistence
- Environment variable management (.env file)
- Port mapping and firewall rules
- Health check implementation
- Configuration generation workflow
- Complete `docker-compose.yml` template
- Deployment instructions (prerequisites, 8 steps)
- eNodeB configuration guide
- Troubleshooting matrix
- Security roadmap (MVP vs Phase 2+)
- Scaling considerations

**Length:** ~800 lines, highly detailed with examples

---

### 2. Architecture Diagrams Document
**File:** `2025-12-27-docker-compose-architecture-diagrams.md`

**Contains:**
- High-level network topology (eNodeB → NUC → Docker services)
- Service communication diagram (internal Docker DNS)
- Port mapping and eNodeB connectivity model
- Data flow diagrams:
  - Subscriber provisioning flow
  - eNodeB S1AP registration
- Startup sequence (cold start vs warm restart timing)
- Configuration file structure (what gets generated where)
- IP address assignment lifecycle (device attachment to IP provisioning)
- MongoDB schema overview
- Environment variable resolution flow
- Firewall rules diagram
- Error recovery scenarios
- Docker command reference
- Kubernetes migration preview (Phase 4)
- Quick reference: location of all components

**Visual Style:** ASCII diagrams with call-outs and annotations

---

### 3. Deployment Runbook
**File:** `2025-12-27-docker-compose-deployment-runbook.md`

**Contains:**
- Pre-flight checklist (what to verify before starting)
- Quick start (5 minutes for impatient users)
- 8 detailed setup steps:
  1. Prepare NUC (DHCP verification, SCTP, firewall)
  2. Clone repository
  3. Create .env configuration
  4. Build Docker images
  5. Start services
  6. Wait for startup with log monitoring
  7. Verify health status
  8. Record NUC IP for future use
- eNodeB configuration (4 steps)
- 5 verification tests (health, UI access, API, device provisioning, eNodeB attachment)
- Comprehensive troubleshooting guide (8 common issues)
- Cleanup and teardown procedures
- Monitoring and operations guide
- Support resources

**Time to Deploy:** 10-15 minutes (end-to-end)

---

## Key Design Decisions

### 1. DHCP-First Architecture
**Decision:** Assume NUC has DHCP-assigned IP on lab network

**Rationale:**
- Most lab networks use DHCP (Windows, Cisco, Unifi)
- Static IPs add deployment friction
- Admin can easily discover IP via `hostname -I`
- eNodeB can be configured with discovered IP

**Trade-off:** Must document eNodeB configuration step clearly ✓

---

### 2. Internal Docker Network (172.26.0.0/16)
**Decision:** Separate internal Docker bridge from host network

**Rationale:**
- Avoids IP conflicts with common lab networks (192.168, 10.x)
- Keeps Open5GS internal IPs stable/predictable
- Services communicate via hostnames (Docker DNS)
- Simple to remember (172.26 = distinct, not used elsewhere)

**Benefits:**
- Works regardless of host's DHCP assignment
- eNodeB doesn't need to know about internal IPs
- Simplifies network debugging (fewer overlapping subnets)

---

### 3. Port Exposure (Host → Container)
**Decision:** Expose S1AP, GTP-C, GTP-U to 0.0.0.0 (all interfaces)

**Rationale:**
- eNodeB connects via host eth0 (DHCP IP)
- Docker automatically forwards traffic: `eth0:36412 → container:36412`
- No manual iptables rules needed
- Firewall (ufw) is sufficient

**Security:** Limited in MVP; Phase 2 adds TLS and auth

---

### 4. Volume Persistence Strategy
**Decision:** Named volumes for data, bind mounts for code

**Rationale:**
- `mongodb_data`: Named volume (survives container restart, easy backup)
- `./configs/`: Bind mount (FastAPI generates, Open5GS reads)
- `./api/`, `./frontend/`, `./daemon/`: Bind mount ro (live code editing)

**Trade-off:** Requires volume driver support (standard Docker ✓)

---

### 5. Configuration Generation at Startup
**Decision:** FastAPI generates Open5GS YAML configs from WaveridersConfig schema

**Rationale:**
- Dynamic: env vars → WaveridersConfig → YAML
- Syncs with UI changes (Phase 2 feature)
- No hard-coded configs
- Open5GS reads generated configs at startup

**Workflow:**
```
.env (PLMN, device pool) → FastAPI startup
                        ↓
                  WaveridersConfig object
                        ↓
                  ConfigGenerator.generate_mme_config()
                        ↓
                  ./configs/mme.yaml (+ hss, sgwc, sgwu)
                        ↓
                  open5gs-mme reads YAML
                        ↓
                  MME/HSS/SGW-C/SGW-U operational
```

---

### 6. QCI 9 (Best-Effort) as Default
**Decision:** Hardcode QCI 9 (best-effort, lowest priority)

**Rationale:**
- Matches Baicells PoC network
- Sufficient for MVP testing
- Simplifies initial setup (no QoS policy selection)
- Phase 2/3 adds configurable QoS

**Parameters:**
- Priority: 9 (lowest)
- Guaranteed BW: No
- Default: 1 Mbps up/down (configurable per device later)

---

### 7. PLMN 315-010 Phased Flexibility
**Decision:** Hardcode PLMN in MVP, make env-configurable in Phase 2

**Rationale:**
- MVP: Single PLMN (315-010 = Indonesia, Waveriders region)
- Phase 2: Allow via .env (3+ different networks)
- Phase 3: UI-configurable without restart

**Implementation:**
```yaml
# MVP (docker-compose.yml)
environment:
  - PLMN_MCC=${PLMN_MCC:-315}    ← Defaults to 315, .env can override
  - PLMN_MNC=${PLMN_MNC:-010}    ← Defaults to 010, .env can override
```

---

### 8. Single Monolithic Open5GS Container
**Decision:** One container for MME, HSS, SGW-C, SGW-U

**Rationale:**
- Matches docker_open5gs project structure
- Simpler for MVP (fewer services, less orchestration)
- Phase 3: Can split into separate containers for scaling

**Assumption:**
- docker_open5gs provides single image with all components
- If not, expand docker-compose.yml with separate services

---

### 9. Health Check Sequencing
**Decision:** Dependency chain: MongoDB → Open5GS → FastAPI → Frontend

**Rationale:**
- MongoDB must be ready before any core service
- Open5GS can start once MongoDB healthy
- FastAPI depends on MongoDB (config generation)
- Frontend depends on FastAPI (implicit, via depends_on)

**Startup Times:**
- Cold: ~60-90 seconds (all services starting)
- Warm: ~10 seconds (containers paused, volumes cached)

---

### 10. No TLS or Auth in MVP
**Decision:** Skip authentication for Phase 1

**Rationale:**
- Lab environment (isolated network)
- Simplifies deployment (no cert generation)
- Reduces attack surface during PoC
- Phase 2 roadmap: MongoDB auth, FastAPI JWT, TLS certs

**Acceptable Risk:** Lab-only deployment; not for production

---

## Architecture Layers

### Layer 1: Host Network (Lab DHCP)
- **IP Range:** 192.168.x.x or 10.x.x.x (admin assigned)
- **Interfaces:** eth0 (NUC)
- **Participants:** eNodeB, admin laptops, NUC
- **Discovery:** Manual configuration on eNodeB (S1AP target = NUC DHCP IP)

### Layer 2: Docker Host
- **Kernel:** Linux with SCTP module
- **Firewall:** ufw rules for S1AP, GTP, web ports
- **Port Forwarding:** Automatic (Docker engine)

### Layer 3: Docker Network (Internal)
- **IP Range:** 172.26.0.0/16
- **Services:** MongoDB, Open5GS, FastAPI, Frontend
- **Communication:** Hostname DNS resolution (mongodb, open5gs-mme, etc.)
- **Isolation:** Not directly reachable from lab network

### Layer 4: Applications
- **Open5GS:** MME, HSS, SGW-C, SGW-U (single container)
- **FastAPI:** Management daemon + REST API
- **React:** Web UI (Vite bundled)
- **MongoDB:** Subscriber database

---

## MVP Constraints & Assumptions

| Constraint | Value | Notes |
|-----------|-------|-------|
| Max Devices | 10 | Device pool: 172.26.99.0/24 (~250 IPs) |
| Network Type | 4G LTE only | No 5G SA; Phase 2 feature |
| QoS | QCI 9 (best-effort) | One policy; Phase 2 adds templates |
| eNodeB | Baicells | Tested; others untested |
| NUC Spec | 4+ GB RAM, 20+ GB disk | Ubuntu 22.04+ |
| TLS | None | Lab-only; Phase 2 adds self-signed certs |
| Authentication | Hardcoded token | CLI only; Phase 2 adds JWT |
| Monitoring | Log parsing | Phase 2 adds Prometheus metrics |
| HA/DR | None | Single node; Phase 3 adds replica set |
| Scaling | Vertical only | Phase 4 adds Kubernetes |

---

## Deliverables Summary

| Document | Purpose | Audience | Lines |
|----------|---------|----------|-------|
| Main Design | Architecture + implementation details | Architects, leads | ~800 |
| Diagrams | Visual reference (networks, flows, timing) | All levels | ~400 |
| Runbook | Step-by-step deployment guide | Field teams, DevOps | ~500 |
| Summary | This document | Decision makers | ~400 |

**Total:** ~2,100 lines of specification + diagrams

---

## Implementation Roadmap

### Immediate (Phase 1 - MVP)
- [ ] Implement docker-compose.yml from template
- [ ] Create Dockerfile for FastAPI (api/Dockerfile)
- [ ] Create Dockerfile for React frontend (frontend/Dockerfile)
- [ ] Implement FastAPI endpoints:
  - GET /api/health
  - GET /api/devices
  - POST /api/devices
  - PUT /api/devices/{imsi}
  - DELETE /api/devices/{imsi}
- [ ] Test locally with docker-compose
- [ ] Deploy to NUC with Baicells eNodeB
- [ ] Document issues and workarounds

### Phase 2 (Production Readiness)
- [ ] MongoDB authentication (username/password)
- [ ] FastAPI JWT tokens
- [ ] TLS for FastAPI ↔ Frontend (self-signed)
- [ ] Configurable QoS policies
- [ ] CSV bulk device import
- [ ] Multi-PLMN support (via UI)
- [ ] Prometheus metrics integration

### Phase 3 (High Availability)
- [ ] MongoDB replica set
- [ ] Multiple Open5GS MME instances (load balanced)
- [ ] Automatic failover
- [ ] Backup/restore procedures
- [ ] Network policies (Kubernetes-ready)

### Phase 4 (Cloud Native)
- [ ] Kubernetes deployment (Helm chart)
- [ ] Multi-region federation
- [ ] Cloud provider integrations (AWS, GCP, Azure)
- [ ] Terraform IaC

---

## Files Provided

### Design Documents (in `/plans/` directory)

1. **2025-12-27-open5g2go-docker-compose-design.md**
   - Complete specification (800 lines)
   - Includes template docker-compose.yml

2. **2025-12-27-docker-compose-architecture-diagrams.md**
   - Visual reference (400 lines, ASCII diagrams)
   - Network topology, flows, timing

3. **2025-12-27-docker-compose-deployment-runbook.md**
   - Step-by-step deployment guide (500 lines)
   - Troubleshooting + operations

4. **2025-12-27-docker-compose-design-summary.md**
   - This document (400 lines)
   - Executive summary + roadmap

---

## Next Steps for Implementation

### Week 1: Setup & Build
1. Create `docker-compose.yml` from template
2. Create Dockerfiles (api/, frontend/)
3. Implement FastAPI health endpoints
4. Test locally: `docker-compose up -d`

### Week 2: Integration
1. Implement config generation (WaveridersConfig → YAML)
2. Implement subscriber CRUD (MongoDB operations)
3. Deploy to NUC lab environment
4. Test with mock eNodeB simulation

### Week 3: Validation
1. Test with real Baicells eNodeB
2. Verify S1AP handshake
3. Test device provisioning and attachment
4. Document issues and fixes

### Week 4: Hardening & Docs
1. Implement security (Phase 2 items)
2. Finalize runbook with field feedback
3. Create troubleshooting guide updates
4. Prepare for production deployment

---

## Success Criteria

**MVP Phase 1 Complete when:**
- [ ] docker-compose up -d on fresh NUC → all services healthy in <90s
- [ ] eNodeB S1AP connects and registers with MME
- [ ] Device provisioning via Web UI works end-to-end
- [ ] Device gets IP from pool after eNodeB attachment
- [ ] API health checks pass
- [ ] Runbook deployment takes <15 minutes
- [ ] Zero code on host machine (only Docker)
- [ ] Survives container restart with data intact
- [ ] Logs show clear error messages for troubleshooting

---

## References

### Related Documents
- **Design:** `plans/2025-10-31-opensurfcontrol-design.md` (original architecture)
- **MVP Plan:** `plans/2025-10-31-opensurfcontrol-mvp-phase1.md` (high-level roadmap)
- **Schema:** `daemon/models/schema.py` (WaveridersConfig pydantic models)

### External Resources
- Open5GS: https://open5gs.org/open5gs/docs/
- Docker Compose: https://docs.docker.com/compose/compose-file/compose-file-v3/
- Baicells: https://www.baicells.com/
- SCTP on Linux: https://wiki.linuxfoundation.org/networking/sctp

---

## Questions & Clarifications

### Q: Why not use docker-compose file version 2.1?
**A:** Version 3.9+ provides better support for health checks and dependencies. V2.1 is deprecated.

### Q: Can we use Kubernetes instead of docker-compose?
**A:** Yes, in Phase 4. MVP prioritizes simplicity; Helm chart planned for later.

### Q: What if NUC loses DHCP lease (power cycling)?
**A:** IP will change, but eNodeB can be configured to re-discover via DNS or DHCP reservation. Phase 2 adds static IP mode.

### Q: Can we scale to 100+ devices?
**A:** MVP device pool supports 250+. Performance depends on NUC specs and MME load. Phase 3 adds distributed MME.

### Q: What about 5G SA?
**A:** Designed for 4G LTE (MVP). 5G SA logic already exists in codebase (`config_generator.generate_amf_config()`). Phase 2 enables via UI.

---

## Conclusion

This design provides a **production-ready, DHCP-friendly docker-compose architecture** for Open5G2GO that:

1. **Works in any lab network** (no static IP required on host)
2. **Deploys in 10-15 minutes** (repeatable, documented)
3. **Scales to 10 devices** with room for 250+ (MVP sufficient)
4. **Integrates with existing openSurfControl codebase** (reuses schema, daemon patterns)
5. **Provides clear path to production** (Phase 2/3/4 roadmap)

The three accompanying documents provide detailed specifications, visual references, and step-by-step deployment guidance ready for immediate implementation.

---

**Design Status:** Ready for Implementation Sprint
**Last Updated:** 2025-12-27
**Next Review:** After Phase 1 implementation complete

