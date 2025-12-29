# Open5G2GO Distribution - Session Starters

Copy-paste these prompts to start each implementation session.

---

## Phase 1: CI/CD Infrastructure

```
Continue Open5G2GO distribution work.

**Milestone:** plans/2025-12-29-distribution-implementation-milestone.md
**Phase:** 1 - CI/CD Infrastructure

**Context files to read:**
- docker-compose.yml
- Dockerfile.backend
- Dockerfile.frontend
- open5gs/Dockerfile

**Tasks:**
1. [Lead/Opus] Create .github/workflows/docker-build.yml
   - Build 3 images on push to main
   - Push to ghcr.io/waveriders-collective/open5g2go-*
   - Tag with :latest and :sha-XXXXXX

2. [Junior/Haiku - parallel] Create docker-compose.prod.yml
   - Copy docker-compose.yml
   - Replace all build: blocks with image: ghcr.io references

**Exit criteria:** Workflow runs successfully, images visible in GitHub Packages
```

---

## Phase 2: Install Scripts

```
Continue Open5G2GO distribution work.

**Milestone:** plans/2025-12-29-distribution-implementation-milestone.md
**Phase:** 2 - Install Scripts

**Context files to read:**
- env.example
- docker-compose.prod.yml
- README.md

**Tasks (spawn Haiku agents in parallel for 2.1, 2.3):**
1. [Junior/Haiku] scripts/preflight-check.sh - system validation
2. [Lead/Opus] scripts/setup-wizard.sh - interactive .env generator
3. [Junior/Haiku] scripts/pull-and-run.sh - pull images, start stack

**Then sequentially:**
4. [Junior/Haiku] scripts/update.sh - update helper
5. [Lead/Opus] install.sh - main entry point orchestrating above

**Exit criteria:** Can run `./install.sh` on fresh system successfully
```

---

## Phase 3: Configuration Updates

```
Continue Open5G2GO distribution work.

**Milestone:** plans/2025-12-29-distribution-implementation-milestone.md
**Phase:** 3 - Configuration Updates

**Context files to read:**
- env.example
- README.md
- install.sh

**Tasks (Haiku agents in parallel):**
1. [Junior/Haiku] Update env.example with SIM key section
2. [Junior/Haiku] Update README.md with one-liner install flow

**Exit criteria:** README shows new quick start, env.example has SIM options
```

---

## Phase 4: Documentation Site

```
Continue Open5G2GO distribution work.

**Milestone:** plans/2025-12-29-distribution-implementation-milestone.md
**Phase:** 4 - Documentation Site

**Context files to read:**
- README.md
- plans/2025-12-27-open5g2go-implementation-plan.md
- docs/LESSONS_LEARNED.md

**Tasks:**
1. [Junior/Haiku] Create docs/mkdocs.yml and docs/requirements.txt

**Then parallel Haiku agents:**
2. [Junior/Haiku] docs/docs/index.md + quickstart.md
3. [Junior/Haiku] docs/docs/enodeb-setup.md
4. [Junior/Haiku] docs/docs/troubleshooting.md

**Then:**
5. [Lead/Opus] Create docs/CLOUDFLARE_PAGES_SETUP.md with manual steps

**Exit criteria:** `mkdocs build` succeeds, all pages render correctly
```

---

## Phase 5: Testing & Launch

```
Continue Open5G2GO distribution work.

**Milestone:** plans/2025-12-29-distribution-implementation-milestone.md
**Phase:** 5 - Testing & Launch

**Tasks:**
1. [Lead/Opus] E2E test on fresh Ubuntu 22.04 VM
   - Install Docker from scratch
   - Run curl one-liner
   - Verify Web UI at :8080
   - Document any issues

2. [Junior/Haiku - parallel] Create docs/BETA_INVITE_TEMPLATE.md

3. [Lead/Opus] Create GitHub Release v0.2.0-beta
   - git tag -a v0.2.0-beta
   - Write release notes

**Exit criteria:** Fresh VM deploys successfully, release tagged
```

---

## Quick Reference: Agent Distribution

| Task Type | Model | When to Use |
|-----------|-------|-------------|
| Architecture decisions | Opus | GitHub Actions workflow design, install.sh orchestration |
| Complex integrations | Opus | Setup wizard (auth, validation), Cloudflare setup |
| Boilerplate scripts | Haiku | preflight-check.sh, pull-and-run.sh, update.sh |
| Documentation | Haiku | All markdown files |
| Code review | Opus | Before merging any phase |

---

## Parallelization Map

```
Phase 1:
  ┌─ Issue 1.1 (Opus) ─────────────┐
  │                                 │
  └─ Issue 1.2 (Haiku) ─ parallel ─┘

Phase 2:
  ┌─ Issue 2.1 (Haiku) ─┐
  ├─ Issue 2.2 (Opus)  ─┼─ parallel ─┬─ Issue 2.4 (Haiku) ─┬─ Issue 2.5 (Opus)
  └─ Issue 2.3 (Haiku) ─┘            │                     │
                                     └─── sequential ──────┘

Phase 3:
  ┌─ Issue 3.1 (Haiku) ─┐
  │                     ├─ parallel
  └─ Issue 3.2 (Haiku) ─┘

Phase 4:
  Issue 4.1 (Haiku) ─┬─ Issue 4.2 (Haiku) ─┐
                     ├─ Issue 4.3 (Haiku) ─┼─ parallel ─┬─ Issue 4.5 (Opus)
                     └─ Issue 4.4 (Haiku) ─┘            │
                                                        └─── sequential

Phase 5:
  ┌─ Issue 5.1 (Opus) ────────────────────────┬─ Issue 5.3 (Opus)
  │                                            │
  └─ Issue 5.2 (Haiku) ─── parallel ──────────┘
```
