# Open5G2GO Beta Invite Template

**Subject:** You're invited to Open5G2GO Private Beta!

---

Hi [NAME],

You've been selected for the Open5G2GO private beta - a homelab toolkit for private 4G cellular networks.

## Getting Started

### 1. Generate a GitHub PAT (required for Docker images)

- Go to: https://github.com/settings/tokens/new
- Select scope: `read:packages`
- Copy the token (you'll need it during setup)

### 2. Install Open5G2GO (5-10 minutes)

```bash
curl -fsSL https://raw.githubusercontent.com/Waveriders-Collective/openSurfcontrol/main/install.sh | bash
```

### 3. Access the Web UI

Open: `http://YOUR_SERVER_IP:8080`

## Requirements

- Ubuntu 22.04+ (or similar Linux with Docker)
- Docker 24.0+ and Docker Compose v2+
- Baicells eNodeB (or compatible 4G radio)
- 5GB free disk space

## What's Included

- **Open5GS Mobile Core** - Complete 4G EPC (HSS, MME, SGW, PGW, PCRF)
- **Web UI** - Subscriber management dashboard
- **Pre-built Docker Images** - No compilation required

## Feedback

Please report issues and feedback to:

- GitHub Issues: https://github.com/Waveriders-Collective/openSurfcontrol/issues
- Slack: #open5g2go-beta

Thanks for being an early tester!

— The Waveriders Team
