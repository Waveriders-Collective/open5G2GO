"""Exercise installer consent and ordering without installing host packages."""

import fcntl
import os
from pathlib import Path
import pty
import subprocess
import tempfile
import termios
import unittest


INSTALLER = Path(__file__).resolve().parents[1] / "install.sh"
CLONE_REACHED = 73

# Every command that could install packages, use the network, or change the host
# is a shell function. The real installer still controls all decisions and reads.
MOCK_COMMANDS = r"""
mock_log() { printf '%s\n' "$*" >> "$MOCK_LOG"; }
mock_probe() { printf '%s\n' "$*" >> "$MOCK_PROBES"; }
mock_installed() {
    if [ "$1" != "$MOCK_UNAVAILABLE" ]; then : > "$MOCK_STATE/installed-$1"; fi
}
function [ {
    if [[ "$*" == '-r /etc/os-release ]' ]]; then return 0; fi
    builtin [ "$@"
}
command() {
    if [ "$1" = -v ]; then
        case " $MOCK_MISSING " in
            *" $2 "*) [ -f "$MOCK_STATE/installed-$2" ] || return 1 ;;
        esac
    fi
    builtin command "$@"
}
function . {
    if [ "$1" = /etc/os-release ]; then
        ID="$MOCK_DISTRO"
        VERSION_ID=22.04
        VERSION_CODENAME=jammy
        UBUNTU_CODENAME=jammy
    else
        builtin . "$@"
    fi
}
uname() { printf 'Linux\n'; }
git() {
    mock_log "git $*"
    if [ "$1" = clone ]; then exit 73; fi
}
docker() {
    if [ "$1 $2" = 'compose version' ]; then
        [ "$MOCK_COMPOSE" = yes ] || [ -f "$MOCK_STATE/installed-compose" ]
    elif [ "$1" = info ]; then
        mock_probe "docker info"
        if [ "$MOCK_DAEMON" = yes ]; then return 0; fi
        if [ -f "$MOCK_STATE/docker-started" ]; then
            if [ "$MOCK_START_PERMISSION_ERROR" = yes ]; then
                echo 'permission denied while trying to connect to the Docker daemon socket' >&2
                return 1
            fi
            local attempts=0
            if [ -f "$MOCK_STATE/startup-attempts" ]; then
                read -r attempts < "$MOCK_STATE/startup-attempts"
            fi
            attempts=$((attempts + 1))
            printf '%s\n' "$attempts" > "$MOCK_STATE/startup-attempts"
            if [ "$attempts" -gt "$MOCK_STARTUP_DELAY" ]; then return 0; fi
        elif [ "$MOCK_PERMISSION_ERROR" = yes ]; then
            echo 'permission denied while trying to connect to the Docker daemon socket' >&2
            return 1
        fi
        echo 'Cannot connect to the Docker daemon at unix:///var/run/docker.sock.' >&2
        return 1
    elif [ "$1 $2" = 'context inspect' ]; then
        mock_probe "docker $*"
        printf '%s\n' "$MOCK_ENDPOINT"
    else
        mock_log "docker $*"
    fi
}
sudo() {
    mock_log "sudo $*"
    if [ "$1" = -v ]; then return 0; fi
    "$@"
}
env() {
    while [[ "$1" == *=* ]]; do shift; done
    "$@"
}
apt-get() {
    mock_log "apt-get $*"
    if [ "$1" = "$MOCK_APT_FAILURE" ]; then return 42; fi
    case " $* " in
        *' install '*)
            for package in "$@"; do
                case "$package" in
                    git|curl|openssl|iptables) mock_installed "$package" ;;
                    iproute2) mock_installed ip; mock_installed ss ;;
                    kmod) mock_installed lsmod; mock_installed modprobe ;;
                    procps) mock_installed sysctl ;;
                    docker-ce|docker-ce-cli|docker.io) mock_installed docker ;;
                    docker-compose-plugin|docker-compose-v2) mock_installed compose ;;
                esac
            done
            ;;
    esac
}
apt-cache() {
    if [ "$MOCK_CANDIDATES" = yes ]; then
        printf '  Installed: (none)\n  Candidate: 1.0\n'
    else
        printf '  Installed: (none)\n  Candidate: (none)\n'
    fi
}
dpkg() {
    if [ "$1" = --print-architecture ]; then printf 'amd64\n'; else return 1; fi
}
dpkg-query() { return 1; }
curl() { mock_log "curl $*"; }
openssl() { mock_log "openssl $*"; }
ip() { mock_log "ip $*"; }
ss() { mock_log "ss $*"; }
lsmod() { mock_log "lsmod $*"; }
modprobe() { mock_log "modprobe $*"; }
iptables() { mock_log "iptables $*"; }
sysctl() { mock_log "sysctl $*"; }
systemctl() {
    case "$1" in
        show)
            mock_probe "systemctl $*"
            printf '%s\n' "$MOCK_LOAD_STATE"
            ;;
        is-active)
            mock_probe "systemctl $*"
            if [ -f "$MOCK_STATE/docker-started" ]; then
                printf 'active\n'
                return 0
            fi
            printf '%s\n' "$MOCK_SERVICE_STATE"
            [ "$MOCK_SERVICE_STATE" = active ]
            ;;
        start)
            mock_log "systemctl $*"
            if [ "$MOCK_START_FAILURE" = yes ]; then return 1; fi
            : > "$MOCK_STATE/docker-started"
            ;;
        *) mock_log "systemctl $*" ;;
    esac
}
sleep() { mock_probe "sleep $*"; }
service() { mock_log "service $*"; }
usermod() { mock_log "usermod $*"; }
install() { mock_log "install $*"; }
tee() { mock_log "tee $*"; cat > /dev/null; }
gpg() { mock_log "gpg $*"; }
chmod() { mock_log "chmod $*"; }
rm() { mock_log "rm $*"; }
"""


class TestInstallerDependencies(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="open5g2go-installer-test-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.install_dir = self.directory / "installation"
        self.log = self.directory / "commands.log"
        self.probes = self.directory / "probes.log"
        self.mock_file = self.directory / "mock-commands.sh"
        self.mock_file.write_text(MOCK_COMMANDS)

    def run_installer(
        self,
        reply="",
        *,
        missing=(),
        terminal=True,
        streamed=False,
        compose=True,
        daemon=True,
        apt_failure="",
        candidates=True,
        distro="ubuntu",
        unavailable="",
        service_state="inactive",
        load_state="loaded",
        start_failure=False,
        startup_delay=0,
        permission_error=False,
        start_permission_error=False,
        endpoint="unix:///var/run/docker.sock",
        docker_host="",
        docker_context="",
    ):
        environment = os.environ.copy()
        environment.update(
            BASH_ENV=str(self.mock_file),
            OPEN5G2GO_DIR=str(self.install_dir),
            MOCK_LOG=str(self.log),
            MOCK_PROBES=str(self.probes),
            MOCK_STATE=str(self.directory),
            MOCK_MISSING=" ".join(missing),
            MOCK_COMPOSE="yes" if compose else "no",
            MOCK_DAEMON="yes" if daemon else "no",
            MOCK_APT_FAILURE=apt_failure,
            MOCK_CANDIDATES="yes" if candidates else "no",
            MOCK_DISTRO=distro,
            MOCK_UNAVAILABLE=unavailable,
            MOCK_SERVICE_STATE=service_state,
            MOCK_LOAD_STATE=load_state,
            MOCK_START_FAILURE="yes" if start_failure else "no",
            MOCK_STARTUP_DELAY=str(startup_delay),
            MOCK_PERMISSION_ERROR="yes" if permission_error else "no",
            MOCK_START_PERMISSION_ERROR="yes" if start_permission_error else "no",
            MOCK_ENDPOINT=endpoint,
            DOCKER_HOST=docker_host,
            DOCKER_CONTEXT=docker_context,
        )
        args = ["/bin/bash"] if streamed else ["/bin/bash", str(INSTALLER)]
        master = slave = None
        options = {}
        if terminal:
            master, slave = pty.openpty()
            # There is no human draining terminal echo; disable it so terminal
            # cleanup cannot block when the streamed shell exits on macOS.
            attributes = termios.tcgetattr(slave)
            attributes[3] &= ~(termios.ECHO | termios.ECHONL)
            termios.tcsetattr(slave, termios.TCSANOW, attributes)

            def attach_terminal():
                os.setsid()
                fcntl.ioctl(slave, termios.TIOCSCTTY, 0)

            options.update(preexec_fn=attach_terminal, pass_fds=(slave,))
        else:
            options["start_new_session"] = True
        process = subprocess.Popen(
            args,
            cwd=self.directory,
            env=environment,
            stdin=subprocess.PIPE if streamed or not terminal else slave,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            **options,
        )
        try:
            if terminal:
                os.close(slave)
                slave = None
                if reply:
                    os.write(master, reply.encode())
            if streamed:
                data = INSTALLER.read_bytes()
            else:
                data = reply.encode() if not terminal else None
            output, _ = process.communicate(input=data, timeout=15)
        except BaseException:
            if master is not None:
                os.close(master)
                master = None
            process.kill()
            process.communicate(timeout=3)
            raise
        finally:
            if master is not None:
                os.close(master)
            if slave is not None:
                os.close(slave)
        commands = self.log.read_text().splitlines() if self.log.exists() else []
        return process.returncode, output.decode(errors="replace"), commands

    def assert_stopped_before_install(self, result):
        status, output, commands = result
        self.assertNotEqual(status, CLONE_REACHED, output)
        self.assertNotEqual(status, 0, output)
        self.assertFalse(any(line.startswith("git clone ") for line in commands), commands)
        self.assertFalse(any(line.startswith("rm ") for line in commands), commands)

    def test_ready_host_reaches_clone_without_package_changes(self):
        status, output, commands = self.run_installer(terminal=False)
        self.assertEqual(status, CLONE_REACHED, output)
        self.assertEqual(len(commands), 1, commands)
        self.assertTrue(commands[0].startswith("git clone "), commands)

    def test_declined_missing_dependency_does_not_mutate_host(self):
        result = self.run_installer("n\n", missing=("git",))
        self.assert_stopped_before_install(result)
        self.assertEqual(result[2], [])

    def test_empty_response_defaults_to_decline(self):
        result = self.run_installer("\n", missing=("git",))
        self.assert_stopped_before_install(result)
        self.assertEqual(result[2], [])

    def test_eof_does_not_authorize_installation(self):
        result = self.run_installer("\x04", missing=("git",))
        self.assert_stopped_before_install(result)
        self.assertEqual(result[2], [])

    def test_missing_terminal_does_not_authorize_installation(self):
        result = self.run_installer("yes\n", missing=("git",), terminal=False)
        self.assert_stopped_before_install(result)
        self.assertEqual(result[2], [])

    def test_approved_git_is_installed_before_clone(self):
        status, output, commands = self.run_installer("yes\n", missing=("git",))
        self.assertEqual(status, CLONE_REACHED, output)
        package_installs = [line for line in commands if line.startswith("apt-get install ")]
        self.assertTrue(package_installs, commands)
        self.assertIn("git", package_installs[0].split())
        self.assertTrue(commands[-1].startswith("git clone "), commands)

    def test_streamed_installer_reads_approval_from_terminal(self):
        status, output, commands = self.run_installer(
            "y\n", missing=("git",), streamed=True
        )
        self.assertEqual(status, CLONE_REACHED, output)
        self.assertTrue(commands[-1].startswith("git clone "), commands)

    def test_missing_docker_and_compose_are_installed(self):
        status, output, commands = self.run_installer(
            "y\n", missing=("docker",), compose=False
        )
        self.assertEqual(status, CLONE_REACHED, output)
        package_installs = " ".join(
            line for line in commands if line.startswith("apt-get install ")
        )
        self.assertIn("docker-ce", package_installs)
        self.assertIn("docker-compose-plugin", package_installs)

    def test_missing_compose_preserves_existing_docker(self):
        status, output, commands = self.run_installer("y\n", compose=False)
        self.assertEqual(status, CLONE_REACHED, output)
        package_installs = " ".join(
            line for line in commands if line.startswith("apt-get install ")
        ).split()
        self.assertIn("docker-compose-plugin", package_installs)
        self.assertNotIn("docker-ce", package_installs)

    def test_docker_repository_is_added_when_packages_are_unavailable(self):
        status, output, commands = self.run_installer(
            "y\n", missing=("docker",), compose=False, candidates=False
        )
        self.assertEqual(status, CLONE_REACHED, output)
        self.assertTrue(any("download.docker.com/linux/ubuntu/gpg" in line for line in commands))
        self.assertIn("tee /etc/apt/sources.list.d/docker.sources", commands)
        self.assertEqual(commands.count("apt-get update"), 2, commands)

    def test_setup_utilities_are_installed_once_per_package(self):
        status, output, commands = self.run_installer(
            "y\n",
            missing=(
                "git",
                "curl",
                "openssl",
                "ip",
                "ss",
                "lsmod",
                "modprobe",
                "iptables",
                "sysctl",
            ),
        )
        self.assertEqual(status, CLONE_REACHED, output)
        package_installs = " ".join(
            line for line in commands if line.startswith("apt-get install ")
        ).split()
        for package in ("git", "curl", "openssl", "iproute2", "kmod", "iptables", "procps"):
            self.assertEqual(package_installs.count(package), 1, commands)

    def test_package_failure_preserves_existing_installation(self):
        self.install_dir.mkdir()
        marker = self.install_dir / "keep-me"
        marker.write_text("existing installation")
        result = self.run_installer(
            "y\nR\n", missing=("git",), apt_failure="install"
        )
        self.assert_stopped_before_install(result)
        self.assertEqual(marker.read_text(), "existing installation")

    def test_inaccessible_docker_prevents_clone_without_service_changes(self):
        result = self.run_installer(
            daemon=False, terminal=False, service_state="active", permission_error=True
        )
        self.assert_stopped_before_install(result)
        self.assertEqual(result[2], [])
        self.assertIn("permission denied", result[1])
        self.assertNotIn("sleep ", self.probes.read_text())

    def test_approved_docker_start_runs_before_clone(self):
        status, output, commands = self.run_installer("yes\n", daemon=False)
        self.assertEqual(status, CLONE_REACHED, output)
        self.assertEqual(commands.count("systemctl start docker"), 1, commands)
        self.assertTrue(commands[-1].startswith("git clone "), commands)
        self.assertEqual(self.probes.read_text().splitlines().count("docker info"), 2)

    def test_decline_blank_and_eof_do_not_start_docker(self):
        for reply in ("n\n", "\n", "\x04"):
            with self.subTest(reply=repr(reply)):
                result = self.run_installer(reply, daemon=False)
                self.assert_stopped_before_install(result)
                self.assertEqual(result[2], [])
                self.assertIn("cancelled", result[1])

    def test_missing_terminal_does_not_authorize_docker_start(self):
        result = self.run_installer("yes\n", daemon=False, terminal=False)
        self.assert_stopped_before_install(result)
        self.assertEqual(result[2], [])
        self.assertIn("interactive terminal is required", result[1])

    def test_failed_service_can_be_started_with_approval(self):
        status, output, commands = self.run_installer(
            "y\n", daemon=False, service_state="failed", endpoint="unix:///run/docker.sock"
        )
        self.assertEqual(status, CLONE_REACHED, output)
        self.assertIn("systemctl start docker", commands)

    def test_docker_start_failure_preserves_existing_installation(self):
        self.install_dir.mkdir()
        marker = self.install_dir / "keep-me"
        marker.write_text("existing installation")
        result = self.run_installer("y\nR\n", daemon=False, start_failure=True)
        self.assert_stopped_before_install(result)
        self.assertEqual(result[2].count("systemctl start docker"), 1)
        self.assertEqual(marker.read_text(), "existing installation")
        self.assertIn("Docker failed to start", result[1])

    def test_docker_start_waits_for_daemon_readiness(self):
        status, output, commands = self.run_installer("y\n", daemon=False, startup_delay=2)
        self.assertEqual(status, CLONE_REACHED, output)
        self.assertEqual(commands.count("systemctl start docker"), 1)
        probes = self.probes.read_text().splitlines()
        self.assertEqual(probes.count("docker info"), 4)
        self.assertEqual(probes.count("sleep 1"), 2)

    def test_docker_start_timeout_is_bounded(self):
        result = self.run_installer("y\n", daemon=False, startup_delay=100)
        self.assert_stopped_before_install(result)
        probes = self.probes.read_text().splitlines()
        self.assertEqual(probes.count("docker info"), 11)
        self.assertEqual(probes.count("sleep 1"), 9)

    def test_permission_error_after_start_stops_without_changing_groups(self):
        result = self.run_installer("y\n", daemon=False, start_permission_error=True)
        self.assert_stopped_before_install(result)
        self.assertIn("permission denied", result[1])
        commands = [line for line in result[2] if not line.startswith("sudo ")]
        self.assertEqual(commands, ["systemctl start docker"])
        probes = self.probes.read_text().splitlines()
        self.assertEqual(probes.count("docker info"), 2)
        self.assertNotIn("sleep 1", probes)

    def test_remote_and_rootless_contexts_do_not_start_system_service(self):
        for endpoint in ("ssh://example.test", "unix:///run/user/1000/docker.sock"):
            with self.subTest(endpoint=endpoint):
                result = self.run_installer("y\n", daemon=False, endpoint=endpoint)
                self.assert_stopped_before_install(result)
                self.assertEqual(result[2], [])
                self.assertNotIn("systemctl ", self.probes.read_text())

    def test_remote_docker_host_does_not_start_system_service(self):
        result = self.run_installer(
            "y\n", daemon=False, docker_host="tcp://example.test:2376"
        )
        self.assert_stopped_before_install(result)
        self.assertEqual(result[2], [])
        probes = self.probes.read_text()
        self.assertNotIn("docker context inspect", probes)
        self.assertNotIn("systemctl ", probes)

    def test_remote_context_overrides_local_docker_host(self):
        result = self.run_installer(
            "y\n",
            daemon=False,
            docker_context="remote",
            docker_host="unix:///var/run/docker.sock",
            endpoint="ssh://example.test",
        )
        self.assert_stopped_before_install(result)
        self.assertEqual(result[2], [])
        self.assertIn("docker context inspect remote ", self.probes.read_text())

    def test_local_context_overrides_remote_docker_host(self):
        status, output, commands = self.run_installer(
            "y\n",
            daemon=False,
            docker_context="local",
            docker_host="ssh://example.test",
        )
        self.assertEqual(status, CLONE_REACHED, output)
        self.assertIn("systemctl start docker", commands)
        self.assertIn("docker context inspect local ", self.probes.read_text())

    def test_streamed_installer_reads_docker_start_approval_from_terminal(self):
        status, output, commands = self.run_installer("y\n", daemon=False, streamed=True)
        self.assertEqual(status, CLONE_REACHED, output)
        self.assertIn("systemctl start docker", commands)

    def test_missing_docker_installation_and_start_require_separate_approvals(self):
        status, output, commands = self.run_installer(
            "yes\nyes\n",
            missing=("docker",),
            compose=False,
            daemon=False,
            candidates=False,
        )
        self.assertEqual(status, CLONE_REACHED, output)
        self.assertIn("tee /etc/apt/sources.list.d/docker.sources", commands)
        self.assertIn("systemctl start docker", commands)
        self.assertLess(
            commands.index("tee /etc/apt/sources.list.d/docker.sources"),
            commands.index("systemctl start docker"),
        )

    def test_dependency_approval_does_not_authorize_docker_start(self):
        result = self.run_installer(
            "yes\nno\n", missing=("docker",), compose=False, daemon=False
        )
        self.assert_stopped_before_install(result)
        self.assertTrue(any(line.startswith("apt-get install ") for line in result[2]))
        self.assertNotIn("systemctl start docker", result[2])

    def test_missing_service_manager_does_not_attempt_start(self):
        result = self.run_installer("y\n", missing=("systemctl",), daemon=False)
        self.assert_stopped_before_install(result)
        self.assertEqual(result[2], [])
        self.assertIn("systemd service is unavailable", result[1])

    def test_unavailable_docker_service_does_not_attempt_start(self):
        for load_state in ("not-found", ""):
            with self.subTest(load_state=load_state):
                result = self.run_installer("y\n", daemon=False, load_state=load_state)
                self.assert_stopped_before_install(result)
                self.assertEqual(result[2], [])
                self.assertIn("systemd service is unavailable", result[1])

    def test_package_index_failure_prevents_package_installation(self):
        result = self.run_installer("y\n", missing=("git",), apt_failure="update")
        self.assert_stopped_before_install(result)
        self.assertFalse(any(line.startswith("apt-get install ") for line in result[2]))

    def test_packages_are_rechecked_after_installation(self):
        result = self.run_installer("y\n", missing=("git",), unavailable="git")
        self.assert_stopped_before_install(result)
        self.assertIn("did not make git available", result[1])

    def test_unsupported_distribution_does_not_install_packages(self):
        result = self.run_installer("y\n", missing=("git",), distro="fedora")
        self.assert_stopped_before_install(result)
        self.assertEqual(result[2], [])


if __name__ == "__main__":
    unittest.main()
