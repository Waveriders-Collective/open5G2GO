#!/bin/bash
# install.sh - Open5G2GO Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/Waveriders-Collective/open5g2go/main/install.sh | bash

set -e

# Configuration
REPO_URL="https://github.com/Waveriders-Collective/open5g2go.git"
INSTALL_DIR="${OPEN5G2GO_DIR:-$HOME/open5g2go}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${BOLD}========================================"
echo "        Open5G2GO Installer"
echo "========================================"
echo ""
echo "  Private 4G LTE Network Toolkit"
echo -e "========================================${NC}"
echo ""

# =============================================================================
# Check for existing installation
# =============================================================================

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Found existing installation at:${NC} $INSTALL_DIR"
    echo ""
    echo "Options:"
    echo "  [U] Update existing installation"
    echo "  [R] Remove and reinstall"
    echo "  [Q] Quit"
    echo ""
    read -p "Choice [U/R/Q]: " choice
    choice="${choice:-U}"

    case "${choice^^}" in
        U)
            echo ""
            echo "Updating existing installation..."
            cd "$INSTALL_DIR"
            exec ./scripts/update.sh
            ;;
        R)
            echo ""
            echo -e "${YELLOW}Removing existing installation...${NC}"
            # Stop any running containers first
            if [ -f "$INSTALL_DIR/docker-compose.prod.yml" ]; then
                cd "$INSTALL_DIR"
                docker compose -f docker-compose.prod.yml down 2>/dev/null || true
            fi
            rm -rf "$INSTALL_DIR"
            echo -e "Removed: ${GREEN}OK${NC}"
            ;;
        Q|*)
            echo "Installation cancelled."
            exit 0
            ;;
    esac
fi

# =============================================================================
# Check prerequisites
# =============================================================================

echo -e "${BLUE}Checking prerequisites...${NC}"
echo ""

# Check for git
if ! command -v git &> /dev/null; then
    echo -e "${RED}Error: git is not installed${NC}"
    echo "Install with: sudo apt install git"
    exit 1
fi
echo -e "  git: ${GREEN}OK${NC}"

# Check for docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: docker is not installed${NC}"
    echo "Install with: curl -fsSL https://get.docker.com | bash"
    exit 1
fi
echo -e "  docker: ${GREEN}OK${NC}"

# Check docker daemon
if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker daemon is not running or you don't have permission${NC}"
    echo ""
    echo "Try:"
    echo "  sudo systemctl start docker"
    echo "  sudo usermod -aG docker \$USER && newgrp docker"
    exit 1
fi
echo -e "  docker daemon: ${GREEN}OK${NC}"

# Check docker compose
if ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose v2 is not installed${NC}"
    echo "Docker Compose v2 is included with Docker Desktop,"
    echo "or install with: sudo apt install docker-compose-plugin"
    exit 1
fi
echo -e "  docker compose: ${GREEN}OK${NC}"

echo ""

# =============================================================================
# Clone repository
# =============================================================================

echo -e "${BLUE}Installing Open5G2GO...${NC}"
echo ""
echo "Cloning repository to: $INSTALL_DIR"
echo ""

git clone "$REPO_URL" "$INSTALL_DIR"
cd "$INSTALL_DIR"

echo ""
echo -e "Repository cloned: ${GREEN}OK${NC}"

# =============================================================================
# Run preflight checks
# =============================================================================

echo ""
echo -e "${BLUE}Running preflight checks...${NC}"
echo ""

if ! ./scripts/preflight-check.sh; then
    echo ""
    echo -e "${RED}Preflight checks failed!${NC}"
    echo "Please fix the issues above and run the installer again."
    echo ""
    echo "You can also run the installation steps manually:"
    echo "  cd $INSTALL_DIR"
    echo "  ./scripts/preflight-check.sh"
    echo "  ./scripts/setup-wizard.sh"
    echo "  ./scripts/pull-and-run.sh"
    exit 1
fi

# =============================================================================
# Run setup wizard
# =============================================================================

echo ""
echo -e "${BLUE}Running setup wizard...${NC}"

if ! ./scripts/setup-wizard.sh; then
    echo ""
    echo -e "${RED}Setup wizard failed or was cancelled${NC}"
    echo ""
    echo "You can run it again with:"
    echo "  cd $INSTALL_DIR"
    echo "  ./scripts/setup-wizard.sh"
    exit 1
fi

# =============================================================================
# Pull images and start stack
# =============================================================================

echo ""
echo -e "${BLUE}Starting Open5G2GO...${NC}"

if ! ./scripts/pull-and-run.sh; then
    echo ""
    echo -e "${RED}Failed to start Open5G2GO${NC}"
    echo ""
    echo "Check the logs with:"
    echo "  cd $INSTALL_DIR"
    echo "  docker compose -f docker-compose.prod.yml logs"
    exit 1
fi

# =============================================================================
# Installation complete
# =============================================================================

HOST_IP=$(grep DOCKER_HOST_IP .env 2>/dev/null | cut -d= -f2 || echo "localhost")

echo ""
echo -e "${BOLD}========================================"
echo "  Installation Complete!"
echo -e "========================================${NC}"
echo ""
echo "Open5G2GO is now running!"
echo ""
echo "  Web UI:   http://${HOST_IP}:8080"
echo "  API:      http://${HOST_IP}:8080/api/v1"
echo ""
echo "Useful commands:"
echo "  cd $INSTALL_DIR"
echo "  ./scripts/update.sh          # Update to latest version"
echo "  docker compose -f docker-compose.prod.yml logs -f   # View logs"
echo "  docker compose -f docker-compose.prod.yml down      # Stop"
echo ""
echo "Documentation: https://open.5g2go.net/docs"
echo ""
