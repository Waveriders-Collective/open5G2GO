"""Test SIM setup choices and persistence without generating real credentials."""

import fcntl
import os
import pty
import shutil
import stat
import subprocess
import tempfile
import termios
import unittest
from pathlib import Path

WIZARD = Path(__file__).resolve().parents[1] / "scripts" / "setup-wizard.sh"
# Public 3GPP TS 35.208 test vector; no test generates real credentials.
TEST_KI = "465b5ce8b199b49faa5f0a2ee238a6bc"
TEST_OPC = "cd63cb71954a9f4e48a5994e37a02baf"
TEST_OP = "cdc202d5123e20f62b6d676ac72cb318"

MOCK_COMMANDS = r"""
mock_log() { printf '%s\n' "$*" >> "$MOCK_LOG"; }
function [ {
    if [[ "$*" == '-r /etc/os-release ]' ]]; then return 0; fi
    builtin [ "$@"
}
function . {
    if [ "$1" = /etc/os-release ]; then ID=ubuntu; else builtin . "$@"; fi
}
command() {
    if [ "$1" = -v ] && [ "$2" = /usr/bin/python3 ]; then return 1; fi
    builtin command "$@"
}
python3() {
    if [ "$1 $2" = '-B -c' ]; then
        [ "$MOCK_CRYPTO" = yes ] || [ -f "$MOCK_STATE/crypto-installed" ]
    elif [ "$1" = -B ]; then
        shift
        /bin/bash "$@"
    else
        return 1
    fi
}
sudo() { mock_log "sudo $*"; "$@"; }
env() { while [[ "$1" == *=* ]]; do shift; done; "$@"; }
apt-get() {
    mock_log "apt-get $*"
    if [ "$1" = install ]; then : > "$MOCK_STATE/crypto-installed"; fi
}
ip() { return 1; }
hostname() { printf '192.0.2.10\n'; }
getent() { printf 'docker:x:994:\n'; }
date() { printf '2026-01-01T00:00:00+00:00\n'; }
openssl() { mock_log "unexpected openssl invocation"; return 1; }
"""

MOCK_GENERATOR = r"""#!/bin/bash
# Stub the secret-producing helper: only its confirmation/status contract is tested.
printf 'generator invoked\n' >> "$MOCK_LOG"
if [ "$1 $2" != '--credentials-fd 3' ]; then exit 2; fi
read -r confirmation || exit 1
if [ "$confirmation" != COPIED ]; then exit 1; fi
if [ "$MOCK_GENERATOR_STATUS" != 0 ]; then exit "$MOCK_GENERATOR_STATUS"; fi
printf '%s\n' "$MOCK_GENERATOR_PAYLOAD" >&3
"""


class TestSetupWizardSimKeys(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="open5g2go-wizard-test-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        scripts = self.directory / "scripts"
        scripts.mkdir()
        self.wizard = scripts / "setup-wizard.sh"
        shutil.copyfile(WIZARD, self.wizard)
        (scripts / "generate-sim-keys.py").write_text(MOCK_GENERATOR)
        (self.directory / "config").mkdir()
        certificates = self.directory / "open5gs" / "config" / "freeDiameter"
        certificates.mkdir(parents=True)
        (certificates / "ca.cert.pem").write_text("Existing certificate fixture\n")
        self.config = self.directory / ".env"
        self.backup = self.directory / ".env.backup"
        self.log = self.directory / "commands.log"
        self.mock_file = self.directory / "mock-commands.sh"
        self.mock_file.write_text(MOCK_COMMANDS)

    def run_wizard(
        self, replies, *, crypto=True, generator_status=0, payload=f"{TEST_KI}:{TEST_OPC}"
    ):
        environment = os.environ.copy()
        environment.update(
            BASH_ENV=str(self.mock_file),
            MOCK_LOG=str(self.log),
            MOCK_STATE=str(self.directory),
            MOCK_CRYPTO="yes" if crypto else "no",
            MOCK_GENERATOR_STATUS=str(generator_status),
            MOCK_GENERATOR_PAYLOAD=payload,
        )
        master, slave = pty.openpty()
        attributes = termios.tcgetattr(slave)
        attributes[3] &= ~(termios.ECHO | termios.ECHONL)
        termios.tcsetattr(slave, termios.TCSANOW, attributes)

        def attach_terminal():
            os.setsid()
            fcntl.ioctl(slave, termios.TIOCSCTTY, 0)

        process = subprocess.Popen(
            ["/bin/bash", str(self.wizard)],
            cwd=self.directory,
            env=environment,
            stdin=slave,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            pass_fds=(slave,),
            preexec_fn=attach_terminal,  # noqa: PLW1509 - single-threaded PTY test
        )
        os.close(slave)
        try:
            os.write(master, ("\n".join(replies) + "\n").encode())
            output, _ = process.communicate(timeout=10)
        except BaseException:
            process.kill()
            process.communicate(timeout=3)
            raise
        finally:
            os.close(master)
        commands = self.log.read_text().splitlines() if self.log.exists() else []
        return process.returncode, output.decode(errors="replace"), commands

    @staticmethod
    def full_setup_replies(*sim_replies):
        # 4G, host IP, UE subnet/gateway, PLMN, then the SIM choices and skip RAN.
        return ["1", "192.0.2.10", "", "", "1", *sim_replies, "n"]

    def assert_saved_keys(self):
        content = self.config.read_text()
        self.assertIn(f"OPEN5GS_DEFAULT_K={TEST_KI}\n", content)
        self.assertIn(f"OPEN5GS_DEFAULT_OPC={TEST_OPC}\n", content)
        self.assertNotIn(TEST_OP, content)
        self.assertEqual(stat.S_IMODE(self.config.stat().st_mode), 0o600)

    def test_manual_keys_are_persisted_unchanged(self):
        status, output, commands = self.run_wizard(self.full_setup_replies("1", TEST_KI, TEST_OPC))
        self.assertEqual(status, 0, output)
        self.assert_saved_keys()
        self.assertEqual(commands, [])

    def test_confirmed_generation_saves_keys_and_preserves_existing_backup(self):
        original = (
            "# Existing manually entered credentials may remain in the backup\n"
            f"OPEN5GS_DEFAULT_K={TEST_KI.upper()}\nOPEN5GS_DEFAULT_OPC={TEST_OPC.upper()}\n"
        )
        self.config.write_text(original)
        status, output, commands = self.run_wizard(["1", *self.full_setup_replies("2", "COPIED")])
        self.assertEqual(status, 0, output)
        self.assert_saved_keys()
        self.assertEqual(self.backup.read_text(), original)
        self.assertEqual(stat.S_IMODE(self.backup.stat().st_mode), 0o600)
        self.assertNotIn(TEST_OP, self.backup.read_text())
        self.assertEqual(commands, ["generator invoked"])
        self.assertNotIn(TEST_KI, output)
        self.assertNotIn(TEST_OPC, output)
        self.assertNotIn(TEST_OP, output)

    def test_unconfirmed_or_failed_helper_preserves_configuration(self):
        original = "# Original settings must survive an interrupted setup\n"
        self.config.write_text(original)
        for confirmation, helper_status in (("CANCEL", 0), ("COPIED", 9)):
            with self.subTest(confirmation=confirmation, helper_status=helper_status):
                status, output, _ = self.run_wizard(
                    ["1", *self.full_setup_replies("2", confirmation)],
                    generator_status=helper_status,
                )
                self.assertNotEqual(status, 0, output)
                self.assertEqual(self.config.read_text(), original)
                self.assertFalse(self.backup.exists())
                self.assertIn("Setup stopped", output)

    def test_malformed_generator_payload_preserves_configuration(self):
        original = "# Existing configuration must survive invalid generator output\n"
        self.config.write_text(original)
        for payload in ("not-a-key-pair", f"{TEST_KI}:{TEST_OP}:{TEST_OPC}"):
            with self.subTest(payload=payload):
                status, output, _ = self.run_wizard(
                    ["1", *self.full_setup_replies("2", "COPIED")], payload=payload
                )
                self.assertNotEqual(status, 0, output)
                self.assertEqual(self.config.read_text(), original)
                self.assertFalse(self.backup.exists())
                self.assertNotIn(TEST_OP, output)

    def test_network_reconfiguration_preserves_saved_keys(self):
        original = (
            "MCC=001\nMNC=01\nDOCKER_GID=994\n"
            f"OPEN5GS_DEFAULT_K={TEST_KI}\nOPEN5GS_DEFAULT_OPC={TEST_OPC}\n"
        )
        self.config.write_text(original)
        status, output, commands = self.run_wizard(["2", "1", "192.0.2.11", "", ""])
        self.assertEqual(status, 0, output)
        self.assert_saved_keys()
        self.assertIn("DOCKER_HOST_IP=192.0.2.11\n", self.config.read_text())
        self.assertEqual(self.backup.read_text(), original)
        self.assertEqual(stat.S_IMODE(self.backup.stat().st_mode), 0o600)
        self.assertEqual(commands, [])

    def test_declining_optional_crypto_packages_stops_without_changes(self):
        status, output, commands = self.run_wizard(self.full_setup_replies("2", "n"), crypto=False)
        self.assertNotEqual(status, 0, output)
        self.assertFalse(self.config.exists())
        self.assertFalse(self.backup.exists())
        self.assertEqual(commands, [])
        self.assertIn("Optional dependency installation cancelled", output)

    def test_approved_optional_crypto_packages_allow_generation(self):
        status, output, commands = self.run_wizard(
            self.full_setup_replies("2", "yes", "COPIED"), crypto=False
        )
        self.assertEqual(status, 0, output)
        self.assert_saved_keys()
        self.assertIn("apt-get update", commands)
        install = "apt-get install -y --no-remove python3 python3-cryptography"
        self.assertIn(install, commands)
        self.assertLess(commands.index(install), commands.index("generator invoked"))


if __name__ == "__main__":
    unittest.main()
