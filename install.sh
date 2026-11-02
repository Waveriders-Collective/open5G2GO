#!/bin/bash
# install.sh - Open5G2GO Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/Waveriders-Collective/open5G2GO/main/install.sh | bash

set -e

# Configuration
REPO_URL="https://github.com/Waveriders-Collective/open5G2GO.git"
INSTALL_DIR="${OPEN5G2GO_DIR:-$HOME/open5G2GO}"
case "$INSTALL_DIR" in
    /*) ;;
    *) INSTALL_DIR="$PWD/$INSTALL_DIR" ;;
esac

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Read prompts from the terminal without consuming a piped installer script.
read_prompt() {
    if [ -t 0 ]; then
        read -r -p "$1" "$2"
    elif { true < /dev/tty; } 2>/dev/null; then
        read -r -p "$1" "$2" < /dev/tty
    else
        echo "An interactive terminal is required. Run the installer from a terminal." >&2
        return 1
    fi
}

run_as_root() {
    if [ "$EUID" -eq 0 ]; then
        "$@"
    else
        sudo "$@"
    fi
}

package_available() {
    LC_ALL=C apt-cache policy "$1" | awk '
        $1 == "Candidate:" && $2 != "(none)" { found = 1 }
        END { exit !found }
    '
}

# Called only after approval. Keep package commands away from the script's stdin.
install_missing_dependencies() (
    set -E
    trap 'echo "Dependency installation failed. Resolve the package-manager error above and rerun the installer." >&2' ERR
    local package docker_codename needs_docker_repo=false
    local ID="" VERSION_CODENAME="" UBUNTU_CODENAME=""
    . /etc/os-release
    docker_codename="$VERSION_CODENAME"
    if [ "$ID" = ubuntu ]; then
        docker_codename="${UBUNTU_CODENAME:-$VERSION_CODENAME}"
    fi

    run_as_root apt-get update
    for package in "$@"; do
        case "$package" in
            docker-*|containerd.io)
                if ! package_available "$package"; then
                    needs_docker_repo=true
                fi
                ;;
        esac
    done

    if [ "$needs_docker_repo" = true ]; then
        if [ -z "$docker_codename" ]; then
            echo "Cannot determine the distribution codename for Docker's repository." >&2
            exit 1
        fi
        # https://docs.docker.com/engine/install/ubuntu/#install-using-the-apt-repository
        # https://docs.docker.com/engine/install/debian/#install-using-the-apt-repository
        run_as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-remove ca-certificates curl
        run_as_root install -m 0755 -d /etc/apt/keyrings
        run_as_root curl -fsSL "https://download.docker.com/linux/$ID/gpg" -o /etc/apt/keyrings/docker.asc
        run_as_root chmod a+r /etc/apt/keyrings/docker.asc
        run_as_root tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/$ID
Suites: $docker_codename
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
        run_as_root apt-get update
    fi

    # Refuse package removals, including conflicts with an existing Docker install.
    run_as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-remove "$@"
)

ensure_docker_running() {
    local docker_error endpoint load_state service_state approval="" attempt

    if docker_error=$(docker info < /dev/null 2>&1); then
        return 0
    fi

    # Starting the system service cannot repair a remote or rootless Docker host.
    # Docker gives DOCKER_CONTEXT precedence over DOCKER_HOST.
    if [ -n "${DOCKER_CONTEXT:-}" ]; then
        endpoint=$(docker context inspect "$DOCKER_CONTEXT" --format '{{.Endpoints.docker.Host}}' < /dev/null 2>/dev/null) || endpoint=""
    elif [ -n "${DOCKER_HOST:-}" ]; then
        endpoint="$DOCKER_HOST"
    else
        endpoint=$(docker context inspect --format '{{.Endpoints.docker.Host}}' < /dev/null 2>/dev/null) || endpoint=""
    fi
    case "$endpoint" in
        unix:///var/run/docker.sock|unix:///run/docker.sock) ;;
        *)
            echo -e "${RED}Cannot connect to the selected Docker host: ${endpoint:-unknown}${NC}"
            printf '%s\n' "$docker_error" >&2
            echo "Check your Docker context or DOCKER_HOST setting and start that daemon, then rerun the installer."
            return 1
            ;;
    esac

    # A systemctl binary alone does not mean systemd or a Docker unit is available.
    if command -v systemctl > /dev/null 2>&1; then
        load_state=$(systemctl show --property=LoadState --value docker.service < /dev/null 2>/dev/null) || load_state=""
    fi
    if [ "$load_state" != loaded ]; then
        echo -e "${RED}Cannot manage Docker automatically: its systemd service is unavailable.${NC}"
        printf '%s\n' "$docker_error" >&2
        echo "Start Docker using your system's service manager, then rerun the installer."
        echo "Instructions: https://docs.docker.com/engine/daemon/start/"
        return 1
    fi

    service_state=$(systemctl is-active docker < /dev/null 2>/dev/null) || true
    case "$service_state" in
        inactive|failed)
            echo -e "${YELLOW}Docker is installed, but its daemon is not running.${NC}"
            if [ "$EUID" -ne 0 ] && ! command -v sudo > /dev/null 2>&1; then
                echo "sudo is required to start Docker. Ask an administrator to start the service."
                return 1
            fi
            echo "The installer can run: sudo systemctl start docker (directly when root)."
            echo "Declining exits the installer."
            if ! read_prompt "Start Docker now and continue? [y/N]: " approval; then
                echo "Installation cancelled."
                return 1
            fi
            case "$approval" in
                [yY]|[yY][eE][sS]) ;;
                *) echo "Installation cancelled."; return 1 ;;
            esac
            if ! run_as_root systemctl start docker < /dev/null; then
                echo -e "${RED}Docker failed to start.${NC}"
                echo "Check the service logs: sudo journalctl -u docker --no-pager -n 50"
                return 1
            fi
            ;;
        active)
            # Already running: preserve the diagnostic instead of offering a restart.
            ;;
        activating)
            echo "Docker is starting. Waiting for it to become available..."
            ;;
        *)
            echo -e "${RED}Cannot start Docker while its service state is: ${service_state:-unknown}${NC}"
            echo "Check the service: sudo systemctl status docker"
            printf '%s\n' "$docker_error" >&2
            return 1
            ;;
    esac

    # The service can take a moment to accept requests after starting.
    for ((attempt = 0; attempt < 10; attempt++)); do
        if docker_error=$(docker info < /dev/null 2>&1); then
            return 0
        fi
        case "$docker_error" in
            *"permission denied"*) break ;;
        esac
        if [ "$attempt" -lt 9 ]; then
            sleep 1
        fi
    done

    if systemctl is-active --quiet docker < /dev/null 2>/dev/null; then
        echo -e "${RED}Docker's service is running, but Docker is not accessible to this session.${NC}"
    else
        echo -e "${RED}Docker is still unavailable after starting.${NC}"
        echo "Check the service logs: sudo journalctl -u docker --no-pager -n 50"
    fi
    printf '%s\n' "$docker_error" >&2
    if [ "$EUID" -ne 0 ] && [[ "$docker_error" == *"permission denied"* ]]; then
        echo 'To grant your user Docker access: sudo usermod -aG docker "$USER"'
        echo "Docker group membership grants root-level access. Log out and back in after this change."
        echo "Details: https://docs.docker.com/engine/install/linux-postinstall/"
    fi
    echo "Once Docker is accessible, rerun this installer."
    return 1
}

check_prerequisites() {
    local spec package tool missing_docker=false
    local packages=() missing_tools=()
    local ID="" PRETTY_NAME=""
    local approval=""

    echo -e "${BLUE}Checking prerequisites...${NC}"
    echo ""

    if [ "$(uname -s)" != Linux ]; then
        echo -e "${RED}Open5G2GO requires a Linux host (Ubuntu 22.04+ recommended).${NC}"
        exit 1
    fi

    # Utilities used by the setup wizard, preflight checks, and stack launcher.
    for spec in git:git curl:curl openssl:openssl iproute2:ip iproute2:ss \
                kmod:lsmod kmod:modprobe iptables:iptables procps:sysctl; do
        package="${spec%%:*}"
        tool="${spec#*:}"
        if ! command -v "$tool" > /dev/null 2>&1; then
            missing_tools+=("$tool")
            case " ${packages[*]} " in
                *" $package "*) ;;
                *) packages+=("$package") ;;
            esac
        fi
    done

    if ! command -v docker > /dev/null 2>&1; then
        missing_docker=true
        echo "Docker Engine is not installed."
        missing_tools+=(docker)
        packages+=(docker-ce docker-ce-cli containerd.io docker-buildx-plugin)
    fi
    if [ "$missing_docker" = true ] || ! docker compose version > /dev/null 2>&1; then
        packages+=(docker-compose-plugin)
    fi

    if [ "${#packages[@]}" -gt 0 ]; then
        echo -e "${YELLOW}Missing required packages:${NC}"
        printf '  - %s\n' "${packages[@]}"
        echo ""

        if [ -r /etc/os-release ]; then
            . /etc/os-release
        fi
        case "$ID" in
            ubuntu|debian) ;;
            *)
                echo "Automatic dependency installation is supported on Ubuntu and Debian."
                echo "Install the equivalent packages for ${PRETTY_NAME:-your Linux distribution}, then rerun this installer."
                exit 1
                ;;
        esac
        if ! command -v apt-get > /dev/null 2>&1 || ! command -v apt-cache > /dev/null 2>&1; then
            echo "apt-get and apt-cache are required for automatic dependency installation."
            exit 1
        fi
        if [ "$EUID" -ne 0 ] && ! command -v sudo > /dev/null 2>&1; then
            echo "sudo is required to install packages. Install them as root, then rerun this installer."
            exit 1
        fi

        echo "The installer will refresh apt's package index and install these packages"
        echo "and their dependencies using root privileges (sudo when needed)."
        case " ${packages[*]} " in
            *" docker-compose-plugin "*)
                echo "Docker's official apt repository and signing key will be added if needed,"
                echo "along with ca-certificates and curl. Installing Docker may start its service."
                echo "Installation method: https://docs.docker.com/engine/install/$ID/#install-using-the-apt-repository"
                ;;
        esac
        echo ""
        if ! read_prompt "Install missing dependencies now? [y/N]: " approval; then
            echo "Dependency installation cancelled."
            exit 1
        fi
        case "$approval" in
            [yY]|[yY][eE][sS]) ;;
            *) echo "Dependency installation cancelled."; exit 1 ;;
        esac

        install_missing_dependencies "${packages[@]}" < /dev/null
        hash -r

        for tool in "${missing_tools[@]}"; do
            if ! command -v "$tool" > /dev/null 2>&1; then
                echo -e "${RED}Dependency installation did not make $tool available. Check your PATH and rerun the installer.${NC}"
                exit 1
            fi
        done
    fi

    if ! docker compose version > /dev/null 2>&1; then
        echo -e "${RED}Docker Compose v2+ is required but is still unavailable.${NC}"
        echo "Install instructions: https://docs.docker.com/compose/install/linux/"
        exit 1
    fi
    ensure_docker_running

    echo -e "  Required tools, Docker, and Docker Compose: ${GREEN}OK${NC}"
    echo ""
}

echo ""
echo -e "${BOLD}========================================"
echo "        Open5G2GO Installer"
echo "========================================"
echo ""
echo "  Private 4G LTE Network Toolkit"
echo -e "========================================${NC}"
echo ""

# Check before updating, removing an existing installation, or cloning files.
check_prerequisites

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
    if ! read_prompt "Choice [U/R/Q]: " choice; then
        echo "Installation cancelled."
        exit 1
    fi
    choice="${choice:-U}"

    case "$choice" in
        U|u)
            echo ""
            echo "Updating existing installation..."
            cd "$INSTALL_DIR"
            exec ./scripts/update.sh < /dev/null
            ;;
        R|r)
            echo ""
            echo -e "${YELLOW}Removing existing installation...${NC}"
            # Stop any running containers first
            if [ -f "$INSTALL_DIR/docker-compose.prod.yml" ]; then
                cd "$INSTALL_DIR"
                docker compose -f docker-compose.prod.yml down < /dev/null 2>/dev/null || true
            fi
            cd "$HOME"
            rm -rf "$INSTALL_DIR"
            echo -e "Removed: ${GREEN}OK${NC}"
            ;;
        *)
            echo "Installation cancelled."
            exit 0
            ;;
    esac
fi

# =============================================================================
# Clone repository
# =============================================================================

echo -e "${BLUE}Installing Open5G2GO...${NC}"
echo ""
echo "Cloning repository to: $INSTALL_DIR"
echo ""

git clone "$REPO_URL" "$INSTALL_DIR" < /dev/null
cd "$INSTALL_DIR"

echo ""
echo -e "Repository cloned: ${GREEN}OK${NC}"

# =============================================================================
# Run preflight checks
# =============================================================================

echo ""
echo -e "${BLUE}Running preflight checks...${NC}"
echo ""

if ! ./scripts/preflight-check.sh < /dev/null; then
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

if ! ./scripts/setup-wizard.sh < /dev/tty; then
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

if ! ./scripts/pull-and-run.sh < /dev/null; then
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
