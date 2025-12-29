# Open5G2GO Distribution Implementation Milestone

**Created:** 2025-12-29
**Status:** Ready for Execution
**Milestone:** v0.2.0-beta-distribution

---

## Session Execution Strategy

### Agent Roles
| Role | Model | Responsibilities |
|------|-------|------------------|
| **Lead Dev** | Opus | Architecture decisions, complex integrations, code review, session handoffs |
| **Junior Dev** | Haiku | Boilerplate generation, documentation writing, file scaffolding, parallel tasks |

### Context Preservation
Each phase includes:
- **Entry Context**: What to read/understand before starting
- **Exit Artifacts**: Files created that serve as context for next phase
- **Handoff Notes**: Key decisions and gotchas for next session

### Parallelization Strategy
- Tasks marked `[PARALLEL]` can run as concurrent Haiku agents
- Tasks marked `[SEQUENTIAL]` require previous task completion
- Each phase should complete before moving to next

---

## Phase 1: CI/CD Infrastructure

**Session Goal:** GitHub Actions workflow that builds and pushes 3 Docker images to ghcr.io

### Entry Context
```bash
# Read these files to understand current Docker setup
cat docker-compose.yml
cat Dockerfile.backend
cat Dockerfile.frontend
cat open5gs/Dockerfile
```

### Issues

#### Issue 1.1: Create GitHub Actions Docker Build Workflow
**Agent:** Opus (Lead)
**Type:** `[SEQUENTIAL]` - Foundation for all other work
**Labels:** `ci-cd`, `infrastructure`, `priority-high`

**Description:**
Create `.github/workflows/docker-build.yml` that:
- Triggers on push to `main` branch
- Builds 3 images: open5gs, backend, frontend
- Pushes to ghcr.io with `:latest` and `:sha-XXXXXXX` tags
- Uses `GITHUB_TOKEN` for authentication (no secrets needed)

**Acceptance Criteria:**
- [ ] Workflow file created at `.github/workflows/docker-build.yml`
- [ ] Builds all 3 images successfully
- [ ] Images appear in GitHub Packages
- [ ] Tags include both `:latest` and git SHA

**Files to Create:**
```
.github/
└── workflows/
    └── docker-build.yml
```

**Reference Implementation:**
```yaml
name: Build and Push Docker Images

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_PREFIX: ${{ github.repository_owner }}/open5g2go

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    strategy:
      matrix:
        include:
          - context: ./open5gs
            dockerfile: ./open5gs/Dockerfile
            image: open5gs
          - context: .
            dockerfile: ./Dockerfile.backend
            image: backend
          - context: .
            dockerfile: ./Dockerfile.frontend
            image: frontend

    steps:
      - uses: actions/checkout@v4

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_PREFIX }}-${{ matrix.image }}
          tags: |
            type=raw,value=latest
            type=sha,prefix=

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: ${{ matrix.context }}
          file: ${{ matrix.dockerfile }}
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

---

#### Issue 1.2: Create Production Docker Compose
**Agent:** Haiku (Junior)
**Type:** `[PARALLEL]` with 1.1
**Labels:** `docker`, `configuration`

**Description:**
Create `docker-compose.prod.yml` that uses pre-built ghcr.io images instead of local builds.

**Acceptance Criteria:**
- [ ] File created at `docker-compose.prod.yml`
- [ ] All `build:` blocks replaced with `image:` references
- [ ] Uses ghcr.io/waveriders-collective/open5g2go-* images
- [ ] All other configuration identical to docker-compose.yml

**Implementation Notes:**
- Copy `docker-compose.yml` as starting point
- Replace these patterns:
  ```yaml
  # FROM (in docker-compose.yml):
  build:
    context: ./open5gs
    dockerfile: Dockerfile

  # TO (in docker-compose.prod.yml):
  image: ghcr.io/waveriders-collective/open5g2go-open5gs:latest
  ```

**Services to Update:**
| Service | Image Name |
|---------|------------|
| hss, mme, sgwc, sgwu, smf, upf, pcrf | `ghcr.io/waveriders-collective/open5g2go-open5gs:latest` |
| backend | `ghcr.io/waveriders-collective/open5g2go-backend:latest` |
| frontend | `ghcr.io/waveriders-collective/open5g2go-frontend:latest` |

---

### Exit Artifacts (Phase 1)
```
.github/workflows/docker-build.yml  # CI/CD workflow
docker-compose.prod.yml              # Production compose file
```

### Handoff Notes for Phase 2
- Verify workflow runs successfully before proceeding
- Note the exact image names for use in install scripts
- If workflow fails, check Dockerfile compatibility with GitHub Actions runners

---

## Phase 2: Install Scripts

**Session Goal:** Interactive install experience with preflight checks and setup wizard

### Entry Context
```bash
# Understand environment configuration
cat env.example
cat docker-compose.prod.yml

# Understand existing docs for deployment requirements
cat README.md
cat plans/2025-12-27-open5g2go-implementation-plan.md | head -100
```

### Issues

#### Issue 2.1: Create Preflight Check Script
**Agent:** Haiku (Junior)
**Type:** `[PARALLEL]` - Can run with 2.2, 2.3
**Labels:** `scripts`, `validation`

**Description:**
Create `scripts/preflight-check.sh` that validates system requirements before installation.

**Acceptance Criteria:**
- [ ] Checks Docker installed and running
- [ ] Checks Docker Compose v2+ installed
- [ ] Checks SCTP kernel module available
- [ ] Checks ports 36412, 2152, 8080 available
- [ ] Checks user has Docker permissions
- [ ] Checks disk space (minimum 5GB free)
- [ ] Clear pass/fail output with actionable error messages
- [ ] Exit code 0 on success, non-zero on failure

**Implementation:**
```bash
#!/bin/bash
# scripts/preflight-check.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "  Open5G2GO Preflight Checks"
echo "========================================"
echo ""

ERRORS=0

# Check Docker
check_docker() {
    echo -n "Checking Docker... "
    if command -v docker &> /dev/null && docker info &> /dev/null; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAILED${NC}"
        echo "  -> Install Docker: https://docs.docker.com/get-docker/"
        ((ERRORS++))
    fi
}

# Check Docker Compose
check_compose() {
    echo -n "Checking Docker Compose... "
    if docker compose version &> /dev/null; then
        VERSION=$(docker compose version --short)
        echo -e "${GREEN}OK${NC} (v$VERSION)"
    else
        echo -e "${RED}FAILED${NC}"
        echo "  -> Docker Compose v2 required"
        ((ERRORS++))
    fi
}

# Check SCTP
check_sctp() {
    echo -n "Checking SCTP kernel module... "
    if lsmod | grep -q sctp || modprobe -n sctp 2>/dev/null; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${YELLOW}WARNING${NC}"
        echo "  -> Run: sudo modprobe sctp"
        echo "  -> Add 'sctp' to /etc/modules for persistence"
    fi
}

# Check ports
check_ports() {
    echo -n "Checking port availability... "
    PORTS_IN_USE=""
    for PORT in 36412 2152 8080; do
        if ss -tuln | grep -q ":$PORT "; then
            PORTS_IN_USE="$PORTS_IN_USE $PORT"
        fi
    done
    if [ -z "$PORTS_IN_USE" ]; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAILED${NC}"
        echo "  -> Ports in use:$PORTS_IN_USE"
        ((ERRORS++))
    fi
}

# Check disk space
check_disk() {
    echo -n "Checking disk space... "
    AVAILABLE=$(df -BG . | awk 'NR==2 {print $4}' | tr -d 'G')
    if [ "$AVAILABLE" -ge 5 ]; then
        echo -e "${GREEN}OK${NC} (${AVAILABLE}GB available)"
    else
        echo -e "${RED}FAILED${NC}"
        echo "  -> Need at least 5GB, have ${AVAILABLE}GB"
        ((ERRORS++))
    fi
}

# Run all checks
check_docker
check_compose
check_sctp
check_ports
check_disk

echo ""
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}All preflight checks passed!${NC}"
    exit 0
else
    echo -e "${RED}$ERRORS check(s) failed. Please fix before continuing.${NC}"
    exit 1
fi
```

---

#### Issue 2.2: Create Setup Wizard Script
**Agent:** Opus (Lead)
**Type:** `[PARALLEL]` - Can run with 2.1, 2.3
**Labels:** `scripts`, `configuration`, `priority-high`

**Description:**
Create `scripts/setup-wizard.sh` that interactively generates `.env` file.

**Acceptance Criteria:**
- [ ] Auto-detects Docker host IP
- [ ] Prompts for UE IP pool (with default)
- [ ] Asks if using Waveriders SIMs or BYO
- [ ] For BYO: prompts for K and OPc keys
- [ ] Prompts for GitHub username and PAT
- [ ] Runs `docker login ghcr.io`
- [ ] Generates `.env` file from `env.example` template
- [ ] Validates all inputs before writing

**Key Implementation Details:**

```bash
#!/bin/bash
# scripts/setup-wizard.sh

# Auto-detect host IP (prefer non-loopback, non-docker interface)
detect_host_ip() {
    # Try to get the default route interface IP
    ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K[\d.]+' || \
    hostname -I | awk '{print $1}' || \
    echo "10.48.0.110"
}

# Prompt with default value
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"

    read -p "$prompt [$default]: " value
    value="${value:-$default}"
    eval "$var_name='$value'"
}

# GitHub authentication
setup_github_auth() {
    echo ""
    echo "GitHub Authentication (required for private images)"
    echo "─────────────────────────────────────────────────────"
    echo "Create a PAT at: https://github.com/settings/tokens"
    echo "Required scope: read:packages"
    echo ""

    read -p "GitHub username: " GITHUB_USER
    read -s -p "GitHub PAT: " GITHUB_PAT
    echo ""

    echo "$GITHUB_PAT" | docker login ghcr.io -u "$GITHUB_USER" --password-stdin
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Successfully authenticated with ghcr.io${NC}"
    else
        echo -e "${RED}Authentication failed${NC}"
        exit 1
    fi
}

# SIM configuration
setup_sim_config() {
    echo ""
    echo "SIM Configuration"
    echo "─────────────────"
    echo "[W] Waveriders-provided SIMs (default K/OPc)"
    echo "[B] Bring Your Own SIMs (enter K/OPc)"
    echo ""

    read -p "Choice [W/B]: " sim_choice
    sim_choice="${sim_choice:-W}"

    if [[ "${sim_choice^^}" == "B" ]]; then
        read -p "Default K (32 hex chars): " OPEN5GS_DEFAULT_K
        read -p "Default OPc (32 hex chars): " OPEN5GS_DEFAULT_OPC
    else
        # Waveriders defaults
        OPEN5GS_DEFAULT_K="465B5CE8B199B49FAA5F0A2EE238A6BC"
        OPEN5GS_DEFAULT_OPC="E8ED289DEBA952E4283B54E88E6183CA"
    fi
}
```

---

#### Issue 2.3: Create Pull and Run Script
**Agent:** Haiku (Junior)
**Type:** `[PARALLEL]` - Can run with 2.1, 2.2
**Labels:** `scripts`, `deployment`

**Description:**
Create `scripts/pull-and-run.sh` that pulls images and starts the stack.

**Acceptance Criteria:**
- [ ] Pulls all images from ghcr.io
- [ ] Starts stack with docker compose
- [ ] Waits for health checks to pass
- [ ] Prints success message with Web UI URL

**Implementation:**
```bash
#!/bin/bash
# scripts/pull-and-run.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Pulling Docker images from ghcr.io..."
docker compose -f docker-compose.prod.yml pull

echo "Starting Open5G2GO stack..."
docker compose -f docker-compose.prod.yml up -d

echo "Waiting for services to become healthy..."
sleep 10

# Wait for backend health check
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        break
    fi
    ((ATTEMPT++))
    echo "  Waiting for backend... ($ATTEMPT/$MAX_ATTEMPTS)"
    sleep 3
done

HOST_IP=$(grep DOCKER_HOST_IP .env 2>/dev/null | cut -d= -f2 || echo "localhost")

echo ""
echo "========================================"
echo "  Open5G2GO is running!"
echo "========================================"
echo ""
echo "  Web UI: http://${HOST_IP}:8080"
echo "  API:    http://${HOST_IP}:8080/api/v1"
echo ""
echo "  View logs: docker compose -f docker-compose.prod.yml logs -f"
echo "  Stop:      docker compose -f docker-compose.prod.yml down"
echo ""
```

---

#### Issue 2.4: Create Update Script
**Agent:** Haiku (Junior)
**Type:** `[SEQUENTIAL]` after 2.3
**Labels:** `scripts`, `maintenance`

**Description:**
Create `scripts/update.sh` for easy updates.

**Implementation:**
```bash
#!/bin/bash
# scripts/update.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Updating Open5G2GO..."

echo "1. Pulling latest code..."
git pull

echo "2. Pulling latest images..."
docker compose -f docker-compose.prod.yml pull

echo "3. Restarting services..."
docker compose -f docker-compose.prod.yml up -d

echo ""
echo "Update complete!"
```

---

#### Issue 2.5: Create Main Install Script
**Agent:** Opus (Lead)
**Type:** `[SEQUENTIAL]` after 2.1-2.4
**Labels:** `scripts`, `priority-high`

**Description:**
Create `install.sh` entry point that orchestrates all scripts.

**Acceptance Criteria:**
- [ ] Can be run via `curl | bash` one-liner
- [ ] Clones repo if not present
- [ ] Runs preflight checks
- [ ] Runs setup wizard
- [ ] Runs pull-and-run
- [ ] Handles errors gracefully

**Implementation:**
```bash
#!/bin/bash
# install.sh - Open5G2GO Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/Waveriders-Collective/open5g2go/main/install.sh | bash

set -e

REPO_URL="https://github.com/Waveriders-Collective/open5g2go.git"
INSTALL_DIR="${OPEN5G2GO_DIR:-$HOME/open5g2go}"

echo "========================================"
echo "  Open5G2GO Installer"
echo "========================================"
echo ""

# Check if already installed
if [ -d "$INSTALL_DIR" ]; then
    echo "Found existing installation at $INSTALL_DIR"
    read -p "Update existing installation? [Y/n]: " update_choice
    if [[ "${update_choice:-Y}" =~ ^[Yy] ]]; then
        cd "$INSTALL_DIR"
        exec ./scripts/update.sh
    fi
fi

# Clone repository
echo "Cloning Open5G2GO to $INSTALL_DIR..."
git clone "$REPO_URL" "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Run installation steps
echo ""
./scripts/preflight-check.sh

echo ""
./scripts/setup-wizard.sh

echo ""
./scripts/pull-and-run.sh
```

---

### Exit Artifacts (Phase 2)
```
scripts/
├── preflight-check.sh
├── setup-wizard.sh
├── pull-and-run.sh
└── update.sh
install.sh
```

### Handoff Notes for Phase 3
- All scripts should be tested on fresh Ubuntu 22.04 VM
- Ensure scripts are executable (`chmod +x`)
- GitHub PAT flow is critical - test with real PAT

---

## Phase 3: Configuration Updates

**Session Goal:** Update env.example and README for new install flow

### Entry Context
```bash
cat env.example
cat README.md
cat install.sh
```

### Issues

#### Issue 3.1: Update env.example with SIM Options
**Agent:** Haiku (Junior)
**Type:** `[PARALLEL]` with 3.2
**Labels:** `configuration`, `documentation`

**Description:**
Enhance `env.example` with SIM key configuration options.

**Changes:**
```bash
# Add to env.example:

# =============================================================================
# SIM Authentication Keys
# =============================================================================

# Default authentication keys for subscriber provisioning
# For Waveriders-provided SIMs, use the defaults below
# For BYO SIMs, replace with your programmed K/OPc values

# Ki (128-bit key, 32 hex characters)
OPEN5GS_DEFAULT_K=465B5CE8B199B49FAA5F0A2EE238A6BC

# OPc (128-bit derived operator key, 32 hex characters)
OPEN5GS_DEFAULT_OPC=E8ED289DEBA952E4283B54E88E6183CA

# =============================================================================
# Docker Configuration
# =============================================================================

# Docker group ID (for service monitoring)
# Find with: getent group docker | cut -d: -f3
DOCKER_GID=994
```

---

#### Issue 3.2: Update README with New Install Flow
**Agent:** Haiku (Junior)
**Type:** `[PARALLEL]` with 3.1
**Labels:** `documentation`

**Description:**
Update README.md with one-liner install and new quick start.

**New Quick Start Section:**
```markdown
## Quick Start

### One-Line Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/Waveriders-Collective/open5g2go/main/install.sh | bash
```

This will:
1. Check system prerequisites
2. Clone the repository
3. Run interactive setup wizard
4. Pull pre-built Docker images
5. Start the stack

### Manual Install

```bash
# Clone repository
git clone https://github.com/Waveriders-Collective/open5g2go.git
cd open5g2go

# Run setup
./scripts/preflight-check.sh
./scripts/setup-wizard.sh
./scripts/pull-and-run.sh
```

### Requirements

- Ubuntu 22.04+ (or similar Linux)
- Docker 24.0+
- Docker Compose v2+
- 5GB free disk space
- Ports: 36412/sctp, 2152/udp, 8080/tcp

### Updates

```bash
cd ~/open5g2go
./scripts/update.sh
```
```

---

### Exit Artifacts (Phase 3)
```
env.example   # Updated with SIM keys
README.md     # Updated with new install flow
```

---

## Phase 4: Documentation Site

**Session Goal:** MkDocs site for Cloudflare Pages at open.5g2go.net/docs

### Entry Context
```bash
# Review existing docs
cat README.md
cat plans/2025-12-27-open5g2go-implementation-plan.md
cat docs/LESSONS_LEARNED.md
```

### Issues

#### Issue 4.1: Create MkDocs Configuration
**Agent:** Haiku (Junior)
**Type:** `[SEQUENTIAL]` - Foundation for docs
**Labels:** `documentation`, `infrastructure`

**Description:**
Create MkDocs configuration with Material theme.

**Files to Create:**
```
docs/
├── mkdocs.yml
├── requirements.txt
└── docs/
    └── (content files in subsequent issues)
```

**mkdocs.yml:**
```yaml
site_name: Open5G2GO Documentation
site_url: https://open.5g2go.net/docs
site_description: Homelab toolkit for private 4G cellular networks

theme:
  name: material
  palette:
    primary: indigo
    accent: amber
  features:
    - navigation.tabs
    - navigation.sections
    - toc.integrate
    - search.suggest

nav:
  - Home: index.md
  - Quick Start: quickstart.md
  - eNodeB Setup: enodeb-setup.md
  - Troubleshooting: troubleshooting.md
  - API Reference: api.md

markdown_extensions:
  - admonition
  - codehilite
  - toc:
      permalink: true

extra:
  social:
    - icon: fontawesome/brands/github
      link: https://github.com/Waveriders-Collective/open5g2go
```

**requirements.txt:**
```
mkdocs>=1.5
mkdocs-material>=9.0
```

---

#### Issue 4.2: Write Quick Start Guide
**Agent:** Haiku (Junior)
**Type:** `[PARALLEL]` with 4.3, 4.4
**Labels:** `documentation`

**Description:**
Create `docs/docs/index.md` and `docs/docs/quickstart.md`.

**index.md content:**
- Project overview
- What's included (Open5GS, Web UI, MCP tools)
- MVP scope (4G LTE, 10 devices, single eNodeB)
- Link to Quick Start

**quickstart.md content:**
- Prerequisites list
- One-liner install command
- Manual install steps
- First device provisioning walkthrough
- Verification steps

---

#### Issue 4.3: Write eNodeB Setup Guide
**Agent:** Haiku (Junior)
**Type:** `[PARALLEL]` with 4.2, 4.4
**Labels:** `documentation`

**Description:**
Create `docs/docs/enodeb-setup.md` with Baicells configuration.

**Content:**
- S1AP configuration (IP, port 36412)
- GTP-U configuration (IP, port 2152)
- PLMN settings (315-010)
- TAC configuration
- Screenshots of Baicells web interface
- Verification: checking MME logs for S1Setup

---

#### Issue 4.4: Write Troubleshooting Guide
**Agent:** Haiku (Junior)
**Type:** `[PARALLEL]` with 4.2, 4.3
**Labels:** `documentation`

**Description:**
Create `docs/docs/troubleshooting.md`.

**Content from LESSONS_LEARNED.md:**
- eNodeB S1AP rejection issues
- SCTP module not loaded
- Port conflicts
- Docker permission errors
- Subscriber not getting IP
- Log viewing commands
- Full reset procedure

---

#### Issue 4.5: Configure Cloudflare Pages
**Agent:** Opus (Lead)
**Type:** `[SEQUENTIAL]` after 4.1-4.4
**Labels:** `infrastructure`, `deployment`

**Description:**
Manual steps to configure Cloudflare Pages (documented for user execution).

**Steps:**
1. Go to Cloudflare Dashboard → Pages
2. Create new project → Connect to Git
3. Select Waveriders-Collective/open5g2go repo
4. Configure build:
   - Build command: `pip install -r docs/requirements.txt && mkdocs build -f docs/mkdocs.yml`
   - Build output directory: `docs/site`
   - Root directory: `/`
5. Add custom domain: `open.5g2go.net`
6. Configure DNS: CNAME to `<project>.pages.dev`

**Output:** Step-by-step guide in `docs/CLOUDFLARE_PAGES_SETUP.md`

---

### Exit Artifacts (Phase 4)
```
docs/
├── mkdocs.yml
├── requirements.txt
├── CLOUDFLARE_PAGES_SETUP.md
└── docs/
    ├── index.md
    ├── quickstart.md
    ├── enodeb-setup.md
    ├── troubleshooting.md
    └── api.md
```

---

## Phase 5: Testing & Launch

**Session Goal:** End-to-end validation and beta launch preparation

### Issues

#### Issue 5.1: End-to-End Test on Fresh VM
**Agent:** Opus (Lead)
**Type:** `[SEQUENTIAL]`
**Labels:** `testing`, `priority-high`

**Description:**
Test complete install flow on fresh Ubuntu 22.04 VM.

**Test Script:**
```bash
# Fresh Ubuntu 22.04 VM
# Run as non-root user with sudo

# Install Docker (if needed)
curl -fsSL https://get.docker.com | bash
sudo usermod -aG docker $USER
newgrp docker

# Run Open5G2GO installer
curl -fsSL https://raw.githubusercontent.com/Waveriders-Collective/open5g2go/main/install.sh | bash

# Verify
curl http://localhost:8080  # Should return frontend
curl http://localhost:8080/api/v1/health  # Should return OK
docker compose -f docker-compose.prod.yml ps  # All healthy
```

**Document any issues in `docs/issues/ISSUE-XXX-*.md`**

---

#### Issue 5.2: Create Beta Invite Email Template
**Agent:** Haiku (Junior)
**Type:** `[PARALLEL]` with 5.1
**Labels:** `documentation`, `launch`

**Description:**
Create invite email template at `docs/BETA_INVITE_TEMPLATE.md`.

**Content:**
```markdown
Subject: You're invited to Open5G2GO Private Beta!

Hi [NAME],

You've been selected for the Open5G2GO private beta - a homelab toolkit
for private 4G cellular networks.

## Getting Started

1. **Generate a GitHub PAT** (required for Docker images)
   - Go to: https://github.com/settings/tokens/new
   - Select scope: `read:packages`
   - Copy the token (you'll need it during setup)

2. **Install Open5G2GO** (5-10 minutes)
   ```bash
   curl -fsSL https://raw.githubusercontent.com/Waveriders-Collective/open5g2go/main/install.sh | bash
   ```

3. **Access the Web UI**
   - Open: http://YOUR_SERVER_IP:8080

## Requirements
- Ubuntu 22.04+ (or similar Linux with Docker)
- Docker 24.0+ and Docker Compose v2+
- Baicells eNodeB (or compatible 4G radio)

## Documentation
- Quick Start: https://open.5g2go.net/docs
- Troubleshooting: https://open.5g2go.net/docs/troubleshooting

## Feedback
Please report issues and feedback to:
- GitHub Issues: [link to private repo issues]
- Slack: #open5g2go-beta

Thanks for being an early tester!

- The Waveriders Team
```

---

#### Issue 5.3: Create GitHub Release v0.2.0-beta
**Agent:** Opus (Lead)
**Type:** `[SEQUENTIAL]` after 5.1
**Labels:** `release`

**Description:**
Tag and create GitHub release.

**Steps:**
```bash
git tag -a v0.2.0-beta -m "Distribution beta release"
git push origin v0.2.0-beta
```

**Release Notes:**
- One-liner install support
- Pre-built Docker images on ghcr.io
- Interactive setup wizard
- Documentation site
- Support for Waveriders and BYO SIMs

---

### Exit Artifacts (Phase 5)
```
docs/BETA_INVITE_TEMPLATE.md
GitHub Release v0.2.0-beta
```

---

## Summary: Issue Tracker View

### Milestone: v0.2.0-beta-distribution

| # | Issue | Agent | Type | Phase | Labels |
|---|-------|-------|------|-------|--------|
| 1.1 | Create GitHub Actions Docker Build Workflow | Opus | Sequential | 1 | ci-cd, infrastructure |
| 1.2 | Create Production Docker Compose | Haiku | Parallel | 1 | docker, configuration |
| 2.1 | Create Preflight Check Script | Haiku | Parallel | 2 | scripts, validation |
| 2.2 | Create Setup Wizard Script | Opus | Parallel | 2 | scripts, configuration |
| 2.3 | Create Pull and Run Script | Haiku | Parallel | 2 | scripts, deployment |
| 2.4 | Create Update Script | Haiku | Sequential | 2 | scripts, maintenance |
| 2.5 | Create Main Install Script | Opus | Sequential | 2 | scripts |
| 3.1 | Update env.example with SIM Options | Haiku | Parallel | 3 | configuration |
| 3.2 | Update README with New Install Flow | Haiku | Parallel | 3 | documentation |
| 4.1 | Create MkDocs Configuration | Haiku | Sequential | 4 | documentation |
| 4.2 | Write Quick Start Guide | Haiku | Parallel | 4 | documentation |
| 4.3 | Write eNodeB Setup Guide | Haiku | Parallel | 4 | documentation |
| 4.4 | Write Troubleshooting Guide | Haiku | Parallel | 4 | documentation |
| 4.5 | Configure Cloudflare Pages | Opus | Sequential | 4 | infrastructure |
| 5.1 | End-to-End Test on Fresh VM | Opus | Sequential | 5 | testing |
| 5.2 | Create Beta Invite Email Template | Haiku | Parallel | 5 | documentation |
| 5.3 | Create GitHub Release v0.2.0-beta | Opus | Sequential | 5 | release |

---

## Session Execution Guide

### How to Start a New Session

**Phase 1 Session:**
```
You are continuing work on Open5G2GO distribution.

Read the milestone plan: plans/2025-12-29-distribution-implementation-milestone.md

Current phase: Phase 1 - CI/CD Infrastructure
Entry context: docker-compose.yml, Dockerfile.backend, Dockerfile.frontend, open5gs/Dockerfile

Tasks:
- Issue 1.1: Create GitHub Actions workflow (Lead - do this yourself)
- Issue 1.2: Create docker-compose.prod.yml (spawn Haiku agent in parallel)

When complete, verify workflow runs and images push to ghcr.io.
```

**Phase 2 Session:**
```
You are continuing work on Open5G2GO distribution.

Read the milestone plan: plans/2025-12-29-distribution-implementation-milestone.md

Current phase: Phase 2 - Install Scripts
Entry context: env.example, docker-compose.prod.yml

Tasks (can parallelize 2.1, 2.2, 2.3):
- Issue 2.1: preflight-check.sh (Haiku)
- Issue 2.2: setup-wizard.sh (Lead - complex logic)
- Issue 2.3: pull-and-run.sh (Haiku)
Then sequentially:
- Issue 2.4: update.sh (Haiku)
- Issue 2.5: install.sh (Lead - orchestration)

Test all scripts before completing phase.
```

---

## Appendix: File Checklist

```
[ ] .github/workflows/docker-build.yml
[ ] docker-compose.prod.yml
[ ] install.sh
[ ] scripts/preflight-check.sh
[ ] scripts/setup-wizard.sh
[ ] scripts/pull-and-run.sh
[ ] scripts/update.sh
[ ] env.example (updated)
[ ] README.md (updated)
[ ] docs/mkdocs.yml
[ ] docs/requirements.txt
[ ] docs/docs/index.md
[ ] docs/docs/quickstart.md
[ ] docs/docs/enodeb-setup.md
[ ] docs/docs/troubleshooting.md
[ ] docs/docs/api.md
[ ] docs/CLOUDFLARE_PAGES_SETUP.md
[ ] docs/BETA_INVITE_TEMPLATE.md
```
