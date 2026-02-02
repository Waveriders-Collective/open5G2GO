# Open5G2GO Setup Workflow - Public Release Plan

**Date:** 2025-02-02
**Status:** Ready for Implementation
**Milestone:** v0.1.0 Public Release

---

## Overview

This plan documents the changes required to the Open5G2GO setup workflow for public release. The goal is to make the installation process work for any user with pre-programmed SIMs, not just Waveriders customers.

### Key Changes

1. Remove hardcoded Waveriders Ki/OPc defaults
2. Add PLMN selection (4 predefined options)
3. Remove GitHub authentication (public images)
4. Change to full 15-digit IMSI entry
5. Update install paths to `open5G2GO`

---

## Phase 1: Foundation - Constants and Environment Variables

**Issue:** #51
**Branch:** `feature/constants-env-vars`

### Changes

#### opensurfcontrol/constants.py

```python
# BEFORE
MCC = "315"
MNC = "010"
PLMNID = f"{MCC}{MNC}"
IMSI_PREFIX = "31501000000"
DEFAULT_K = os.getenv("OPEN5GS_DEFAULT_K", "465B5CE8B199B49FAA5F0A2EE238A6BC")
DEFAULT_OPC = os.getenv("OPEN5GS_DEFAULT_OPC", "E8ED289DEBA952E4283B54E88E6183CA")

# AFTER
# Network Identity (PLMN) - read from environment
MCC = os.getenv("MCC", "315")
MNC = os.getenv("MNC", "010")

# Handle 2-digit MNC -> 3-digit for IMSI (3GPP compliance)
# 001-01 -> 001010, 999-99 -> 999990, 315-010 -> 315010
MNC_IMSI = MNC if len(MNC) == 3 else f"{MNC}0"
PLMNID = f"{MCC}{MNC_IMSI}"

# Authentication Keys (REQUIRED - no defaults)
DEFAULT_K = os.getenv("OPEN5GS_DEFAULT_K")
DEFAULT_OPC = os.getenv("OPEN5GS_DEFAULT_OPC")

def validate_auth_keys():
    """Validate that authentication keys are configured."""
    if not DEFAULT_K or not DEFAULT_OPC:
        raise ValueError(
            "OPEN5GS_DEFAULT_K and OPEN5GS_DEFAULT_OPC environment variables are required. "
            "These are your SIM authentication keys from your SIM vendor."
        )
```

Remove:
- `IMSI_PREFIX` constant (no longer needed)

### Acceptance Criteria

- [ ] MCC/MNC read from environment
- [ ] 2-digit MNC converted to 3-digit for PLMNID
- [ ] No default Ki/OPc values in code
- [ ] Clear error if Ki/OPc not set

---

## Phase 2: PLMN Configuration Step

**Issue:** #47
**Branch:** `feature/plmn-configuration`

### Changes

#### scripts/setup-wizard.sh

Add new step after Network Configuration:

```bash
# =============================================================================
# Step 2: PLMN Configuration (NEW)
# =============================================================================

echo ""
echo -e "${BLUE}Step 2: Network Identity (PLMN)${NC}"
echo "─────────────────────────────────"
echo ""
echo "Your PLMN (Public Land Mobile Network) ID must match your SIM cards."
echo ""
echo -e "  ${BOLD}[1]${NC} 315-010 - US CBRS Private LTE (default)"
echo -e "  ${BOLD}[2]${NC} 001-01  - Test Network (sysmocom/programmable SIMs)"
echo -e "  ${BOLD}[3]${NC} 999-99  - Test Network"
echo -e "  ${BOLD}[4]${NC} 999-01  - Test Network"
echo ""

read -p "Choice [1]: " plmn_choice
plmn_choice="${plmn_choice:-1}"

case "$plmn_choice" in
    1) MCC="315"; MNC="010" ;;
    2) MCC="001"; MNC="01" ;;
    3) MCC="999"; MNC="99" ;;
    4) MCC="999"; MNC="01" ;;
    *) MCC="315"; MNC="010" ;;
esac

echo -e "Selected PLMN: ${GREEN}${MCC}-${MNC}${NC}"
```

Update .env generation to include:

```bash
# PLMN Configuration (Network Identity)
MCC=${MCC}
MNC=${MNC}
```

Update summary to show PLMN selection.

### Acceptance Criteria

- [ ] 4 PLMN options available
- [ ] Default is option 1 (315-010)
- [ ] MCC/MNC written to .env
- [ ] Summary shows selected PLMN

---

## Phase 3: SIM Configuration - Remove Defaults

**Issue:** #48
**Branch:** `feature/sim-config-no-defaults`

### Changes

#### scripts/setup-wizard.sh

Replace SIM configuration step:

```bash
# =============================================================================
# Step 3: SIM Configuration (UPDATED)
# =============================================================================

echo ""
echo -e "${BLUE}Step 3: SIM Configuration${NC}"
echo "─────────────────────────────────"
echo ""
echo "You need pre-programmed SIM cards with Ki and OPc authentication keys."
echo ""
echo "Ki (Authentication Key) and OPc (Operator Key) are cryptographic keys"
echo "programmed into your SIM cards. Your SIM vendor provides these values."
echo ""
echo -e "  Need SIMs? Order at: ${YELLOW}https://waveriders.live/sims${NC}"
echo ""
echo "Enter your SIM authentication keys (32 hex characters each):"
echo ""

while true; do
    read -p "  Ki:  " OPEN5GS_DEFAULT_K
    if validate_hex_key "$OPEN5GS_DEFAULT_K" "Ki"; then
        break
    fi
done

while true; do
    read -p "  OPc: " OPEN5GS_DEFAULT_OPC
    if validate_hex_key "$OPEN5GS_DEFAULT_OPC" "OPc"; then
        break
    fi
done

echo ""
echo -e "SIM keys configured: ${GREEN}OK${NC}"
```

Remove:
- [W]/[B] menu choice
- Hardcoded Waveriders keys (lines 140-141)

### Acceptance Criteria

- [ ] No default Ki/OPc in setup-wizard.sh
- [ ] Always prompts for Ki/OPc
- [ ] Brief explanation of Ki/OPc displayed
- [ ] Link to waveriders.live/sims displayed
- [ ] Hex validation retained

---

## Phase 4: Remove GitHub Authentication

**Issue:** #49
**Branch:** `feature/remove-github-auth`

### Changes

#### scripts/setup-wizard.sh

Delete entire GitHub Authentication step (lines 145-193):

```bash
# DELETE THIS ENTIRE SECTION:
# =============================================================================
# Step 3: GitHub Authentication
# =============================================================================
# ... (lines 145-193)
```

Renumber subsequent steps:
- Step 4 (Docker Config) → Step 4 (unchanged number)
- Step 5 (Generate Config) → Step 5
- Step 6 (FreeDiameter) → Step 6
- Step 7 (SGWU) → Step 7

Update summary - remove "GitHub Auth: OK" line.

#### scripts/pull-and-run.sh

Remove any authentication checks (if present).

### Acceptance Criteria

- [ ] No GitHub authentication step in wizard
- [ ] docker compose pull works without login
- [ ] Summary doesn't mention GitHub auth

---

## Phase 5: Full 15-Digit IMSI Entry

**Issue:** #50
**Branch:** `feature/full-imsi-entry`

### Changes

#### opensurfcontrol/mongodb_client.py

```python
# REMOVE or UPDATE build_imsi() method
# BEFORE:
def build_imsi(self, device_number: str) -> str:
    padded = device_number.zfill(4)
    return f"{IMSI_PREFIX}{padded}"

# AFTER: Remove entirely or change to validation-only
def validate_imsi(self, imsi: str) -> str:
    """Validate IMSI format."""
    if not imsi.isdigit() or len(imsi) != 15:
        raise ValidationError("IMSI must be exactly 15 digits")
    return imsi
```

Update add_subscriber() to accept full IMSI directly.

#### web_frontend/src/components/subscribers/AddSubscriberModal.tsx

```tsx
// BEFORE:
<label>Device Number (last 4 digits)</label>
<input maxLength={4} pattern="[0-9]{4}" />

// AFTER:
<label>IMSI (15 digits)</label>
<input maxLength={15} pattern="[0-9]{15}" placeholder="315010000000001" />
```

#### web_backend/api/models.py

Update validation:
```python
# BEFORE:
device_number: str = Field(..., min_length=1, max_length=4)

# AFTER:
imsi: str = Field(..., min_length=15, max_length=15, pattern="^[0-9]{15}$")
```

#### web_backend/api/routes.py

Update add_subscriber endpoint to use full IMSI.

### Acceptance Criteria

- [ ] Frontend accepts 15-digit IMSI
- [ ] Backend validates 15 digits
- [ ] No automatic prefix prepending
- [ ] Works with any PLMN

---

## Phase 6: Install Script Updates

**Issue:** #46
**Branch:** `feature/installer-public-release`

### Changes

#### install.sh

```bash
# BEFORE:
REPO_URL="https://github.com/Waveriders-Collective/openSurfcontrol.git"
INSTALL_DIR="${OPEN5G2GO_DIR:-$HOME/openSurfcontrol}"

# AFTER:
REPO_URL="https://github.com/Waveriders-Collective/open5G2GO.git"
INSTALL_DIR="${OPEN5G2GO_DIR:-$HOME/open5G2GO}"
```

Update all references to installation directory.

### Acceptance Criteria

- [ ] Clones to ~/open5G2GO
- [ ] All paths use new directory name
- [ ] Installer completes on fresh Ubuntu 22.04

---

## Implementation Order

```
Phase 1: constants.py env vars (#51)
    ↓
Phase 2: PLMN configuration (#47)  ←──┐
    ↓                                 │ Can be parallel
Phase 3: SIM config no defaults (#48) ┘
    ↓
Phase 4: Remove GitHub auth (#49)
    ↓
Phase 5: Full IMSI entry (#50)
    ↓
Phase 6: Install script (#46)
    ↓
Phase 5 (original): Public repo setup (#41)
```

---

## Testing Checklist

After all phases complete:

- [ ] Fresh install on Ubuntu 22.04 with Docker
- [ ] Setup wizard completes with each PLMN option
- [ ] Custom Ki/OPc values work
- [ ] Add subscriber with full 15-digit IMSI
- [ ] All 4 PLMN options function correctly
- [ ] No hardcoded Waveriders values remain
- [ ] Docker images pull without authentication

---

## Files Modified Summary

| File | Changes |
|------|---------|
| `install.sh` | Repo URL, install directory |
| `scripts/setup-wizard.sh` | PLMN step, SIM step, remove GitHub auth |
| `opensurfcontrol/constants.py` | Env vars for MCC/MNC/Ki/OPc, remove IMSI_PREFIX |
| `opensurfcontrol/mongodb_client.py` | Remove build_imsi(), accept full IMSI |
| `web_backend/api/models.py` | IMSI validation (15 digits) |
| `web_backend/api/routes.py` | Full IMSI in add_subscriber |
| `web_frontend/.../AddSubscriberModal.tsx` | Full IMSI input field |

---

## Document History

| Date | Author | Changes |
|------|--------|---------|
| 2025-02-02 | Waveriders Collective Inc. | Initial plan |
