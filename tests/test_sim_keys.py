"""Verify Milenage derivation, one-time OP display, and confirmed Ki/OPc handoff."""

import contextlib
import fcntl
import importlib.util
import io
import os
import pty
import re
import selectors
import subprocess
import sys
import tempfile
import termios
import time
import unittest
from pathlib import Path
from unittest import mock

GENERATOR_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate-sim-keys.py"
SPEC = importlib.util.spec_from_file_location("generate_sim_keys", GENERATOR_PATH)
GENERATOR = importlib.util.module_from_spec(SPEC)
CRYPTO_AVAILABLE = importlib.util.find_spec("cryptography") is not None
if CRYPTO_AVAILABLE:
    with mock.patch.object(sys, "dont_write_bytecode", True):
        SPEC.loader.exec_module(GENERATOR)

# Public 3GPP Milenage test set 1, not operational subscriber credentials.
KI = bytes.fromhex("465b5ce8b199b49faa5f0a2ee238a6bc")
OP = bytes.fromhex("cdc202d5123e20f62b6d676ac72cb318")
OPC = bytes.fromhex("cd63cb71954a9f4e48a5994e37a02baf")


class TerminalBuffer(io.StringIO):
    def isatty(self):
        return True

    def __exit__(self, *args):
        # Retain captured output after the production context manager exits.
        return False


@unittest.skipUnless(CRYPTO_AVAILABLE, "Install optional cryptography to run SIM key tests")
class TestSimKeyDerivation(unittest.TestCase):
    def test_matches_official_milenage_vector(self):
        self.assertEqual(GENERATOR.derive_opc(KI, OP), OPC)

    def test_requires_128_bit_ki_and_op(self):
        for length in (0, 15, 17, 24, 32):
            for ki, op in ((bytes(length), OP), (KI, bytes(length))):
                with (
                    self.subTest(ki_length=len(ki), op_length=len(op)),
                    self.assertRaises(ValueError),
                ):
                    GENERATOR.derive_opc(ki, op)

    def test_generation_uses_independent_random_128_bit_values(self):
        with mock.patch.object(GENERATOR.secrets, "token_bytes", side_effect=(KI, OP)) as random:
            self.assertEqual(GENERATOR.generate_keys(), (KI, OP, OPC))
        self.assertEqual(random.call_args_list, [mock.call(16), mock.call(16)])


@unittest.skipUnless(CRYPTO_AVAILABLE, "Install optional cryptography to run SIM key tests")
class TestSimKeyDisplay(unittest.TestCase):
    def display(self, response):
        terminal_in = TerminalBuffer(response)
        terminal_out = TerminalBuffer()
        stdout = io.StringIO()
        stderr = io.StringIO()

        def generate_after_warning():
            self.assertIn("WARNING", terminal_out.getvalue())
            return KI, OP, OPC

        with (
            mock.patch.object(
                GENERATOR, "generate_keys", side_effect=generate_after_warning
            ) as keys,
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            result = GENERATOR.display_and_confirm(terminal_in, terminal_out)
        keys.assert_called_once_with()
        self.assertEqual(len(stdout.getvalue()), 0)
        self.assertEqual(len(stderr.getvalue()), 0)
        output = terminal_out.getvalue()
        for value in (KI, OP, OPC):
            self.assertEqual(output.count(value.hex()), 1)
        return result, output

    def test_warns_before_display_and_accepts_copied(self):
        result, output = self.display("COPIED\n")
        self.assertEqual(result, (KI, OPC))
        self.assertLess(output.index("WARNING"), output.index("Ki:"))
        self.assertEqual(output.count("Type COPIED"), 1)

    def test_invalid_confirmation_only_repeats_prompt(self):
        result, output = self.display("\ncopied\nyes\nCOPIED extra\nCOPIED\n")
        self.assertEqual(result, (KI, OPC))
        self.assertEqual(output.count("Type COPIED"), 5)
        self.assertEqual(output.count("WARNING"), 1)

    def test_cancel_stops_without_redisplaying_values(self):
        result, output = self.display("CANCEL\n")
        self.assertIsNone(result)
        self.assertEqual(output.count("Type COPIED"), 1)

    def test_eof_stops_without_redisplaying_values(self):
        result, output = self.display("")
        self.assertIsNone(result)
        self.assertEqual(output.count("Type COPIED"), 1)

    def test_main_refuses_missing_terminal_before_generating_keys(self):
        stderr = io.StringIO()
        with (
            mock.patch("builtins.open", side_effect=OSError("No controlling terminal")),
            mock.patch.object(GENERATOR.resource, "setrlimit"),
            mock.patch.object(GENERATOR, "generate_keys") as keys,
            contextlib.redirect_stderr(stderr),
        ):
            self.assertEqual(GENERATOR.main([]), 1)
        keys.assert_not_called()
        self.assertIn("interactive terminal", stderr.getvalue())

    def test_main_refuses_nonterminal_stream_before_generating_keys(self):
        terminal_in = TerminalBuffer()
        terminal_out = TerminalBuffer()
        with (
            mock.patch("builtins.open", side_effect=(terminal_in, terminal_out)),
            mock.patch.object(terminal_in, "isatty", return_value=False),
            mock.patch.object(GENERATOR.resource, "setrlimit"),
            mock.patch.object(GENERATOR, "generate_keys") as keys,
            contextlib.redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(GENERATOR.main([]), 1)
        keys.assert_not_called()
        self.assertEqual(len(terminal_out.getvalue()), 0)

    def test_main_uses_terminal_and_disables_core_dumps(self):
        terminal_in = TerminalBuffer("COPIED\n")
        terminal_out = TerminalBuffer()
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            mock.patch("builtins.open", side_effect=(terminal_in, terminal_out)) as open_terminal,
            mock.patch.object(GENERATOR.resource, "setrlimit") as setrlimit,
            mock.patch.object(GENERATOR, "generate_keys", return_value=(KI, OP, OPC)),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            self.assertEqual(GENERATOR.main([]), 0)
        setrlimit.assert_called_once_with(GENERATOR.resource.RLIMIT_CORE, (0, 0))
        self.assertEqual(open_terminal.call_count, 2)
        for call in open_terminal.call_args_list:
            self.assertEqual(call.args[0], "/dev/tty")
        self.assertEqual(len(stdout.getvalue()), 0)
        self.assertEqual(len(stderr.getvalue()), 0)

    def run_main_with_credentials_pipe(self, response):
        reader, writer = os.pipe()
        os.set_blocking(reader, False)
        terminal_in = TerminalBuffer(response)
        terminal_out = TerminalBuffer()
        stdout = io.StringIO()
        stderr = io.StringIO()
        original_readline = terminal_in.readline

        def confirm_without_early_payload():
            try:
                early_payload = os.read(reader, 4096)
            except BlockingIOError:
                early_payload = b""
            self.assertEqual(len(early_payload), 0)
            return original_readline()

        try:
            with (
                mock.patch("builtins.open", side_effect=(terminal_in, terminal_out)),
                mock.patch.object(
                    terminal_in, "readline", side_effect=confirm_without_early_payload
                ),
                mock.patch.object(GENERATOR.resource, "setrlimit"),
                mock.patch.object(GENERATOR, "generate_keys", return_value=(KI, OP, OPC)),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                status = GENERATOR.main(["--credentials-fd", str(writer)])
            with contextlib.suppress(OSError):
                os.close(writer)
            payload = os.read(reader, 4096)
        finally:
            os.close(reader)
            with contextlib.suppress(OSError):
                os.close(writer)
        self.assertEqual(len(stdout.getvalue()), 0)
        self.assertEqual(len(stderr.getvalue()), 0)
        return status, payload

    def test_confirmed_pipe_handoff_contains_only_ki_and_opc(self):
        status, payload = self.run_main_with_credentials_pipe("\ncopied\nCOPIED\n")
        self.assertEqual(status, 0)
        self.assertTrue(payload == f"{KI.hex()}:{OPC.hex()}\n".encode())
        self.assertFalse(OP.hex().encode() in payload)

    def test_cancel_and_eof_do_not_export_credentials(self):
        for response in ("CANCEL\n", ""):
            with self.subTest(response=response):
                status, payload = self.run_main_with_credentials_pipe(response)
                self.assertEqual(status, 1)
                self.assertEqual(len(payload), 0)

    def test_standard_streams_cannot_be_used_as_credentials_destination(self):
        for descriptor in (-1, 0, 1, 2):
            with self.subTest(descriptor=descriptor):
                with (
                    mock.patch(
                        "builtins.open",
                        side_effect=(TerminalBuffer("COPIED\n"), TerminalBuffer()),
                    ),
                    mock.patch.object(GENERATOR.resource, "setrlimit"),
                    mock.patch.object(
                        GENERATOR,
                        "generate_keys",
                        side_effect=AssertionError("Unsafe descriptor reached key generation"),
                    ) as keys,
                    contextlib.redirect_stdout(io.StringIO()),
                    contextlib.redirect_stderr(io.StringIO()),
                ):
                    try:
                        status = GENERATOR.main(["--credentials-fd", str(descriptor)])
                    except SystemExit as error:
                        status = error.code
                self.assertNotEqual(status, 0)
                keys.assert_not_called()


@unittest.skipUnless(CRYPTO_AVAILABLE, "Install optional cryptography to run SIM key tests")
class TestSimKeyTerminalIntegration(unittest.TestCase):
    def run_on_terminal(self, reply, *, credentials_pipe=False):
        master, slave = pty.openpty()
        attributes = termios.tcgetattr(slave)
        attributes[3] &= ~(termios.ECHO | termios.ECHONL)
        termios.tcsetattr(slave, termios.TCSANOW, attributes)

        def attach_terminal():
            os.setsid()
            fcntl.ioctl(slave, termios.TIOCSCTTY, 0)

        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        output = {
            "terminal": bytearray(),
            "stdout": bytearray(),
            "stderr": bytearray(),
            "credentials": bytearray(),
        }
        command = [sys.executable, str(GENERATOR_PATH)]
        inherited_fds = (slave,)
        credentials_reader = credentials_writer = None
        if credentials_pipe:
            credentials_reader, credentials_writer = os.pipe()
            os.set_blocking(credentials_reader, False)
            command.extend(("--credentials-fd", str(credentials_writer)))
            inherited_fds += (credentials_writer,)
        with tempfile.TemporaryDirectory(prefix="open5g2go-sim-test-") as directory:
            process = subprocess.Popen(
                command,
                cwd=directory,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=attach_terminal,  # noqa: PLW1509 - single-threaded PTY test
                pass_fds=inherited_fds,
            )
            os.close(slave)
            if credentials_writer is not None:
                os.close(credentials_writer)
            try:
                reply_sent = False
                deadline = time.monotonic() + 10
                with selectors.DefaultSelector() as selector:
                    selector.register(master, selectors.EVENT_READ, "terminal")
                    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
                    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
                    if credentials_reader is not None:
                        selector.register(credentials_reader, selectors.EVENT_READ, "credentials")
                    while selector.get_map():
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            self.fail("Generator did not finish after terminal confirmation")
                        for key, _ in selector.select(remaining):
                            try:
                                data = os.read(key.fd, 4096)
                            except OSError:
                                data = b""
                            if data:
                                if key.data == "credentials":
                                    self.assertTrue(reply_sent)
                                output[key.data].extend(data)
                            else:
                                selector.unregister(key.fileobj)
                            if not reply_sent and b"Type COPIED" in output["terminal"]:
                                if credentials_reader is not None:
                                    try:
                                        early_payload = os.read(credentials_reader, 4096)
                                    except BlockingIOError:
                                        early_payload = b""
                                    self.assertEqual(len(early_payload), 0)
                                os.write(master, reply)
                                reply_sent = True
                status = process.wait(timeout=3)
                self.assertEqual(list(Path(directory).iterdir()), [])
            finally:
                os.close(master)
                if credentials_reader is not None:
                    os.close(credentials_reader)
                if process.poll() is None:
                    process.kill()
                process.communicate(timeout=3)
        return status, output

    def assert_single_terminal_display(self, output):
        # Never include generated values in assertion failure messages.
        self.assertEqual(len(output["stdout"]), 0)
        self.assertEqual(len(output["stderr"]), 0)
        terminal = output["terminal"].decode()
        values = re.findall(r"^(?:Ki|Source OP|OPc):\s+([0-9a-f]{32})\r?$", terminal, re.MULTILINE)
        self.assertEqual(len(values), 3)
        for value in values:
            self.assertEqual(terminal.count(value), 1)
        self.assertEqual(terminal.count("WARNING"), 1)
        return terminal

    def test_real_terminal_display_never_uses_redirected_output(self):
        status, output = self.run_on_terminal(b"COPIED\n")
        self.assertEqual(status, 0)
        self.assert_single_terminal_display(output)

    def test_real_terminal_reprompts_without_revealing_values_again(self):
        status, output = self.run_on_terminal(b"\ncopied\nCOPIED\n")
        self.assertEqual(status, 0)
        terminal = self.assert_single_terminal_display(output)
        self.assertEqual(terminal.count("Type COPIED"), 3)

    def test_real_terminal_cancel_returns_failure(self):
        status, output = self.run_on_terminal(b"CANCEL\n")
        self.assertEqual(status, 1)
        self.assert_single_terminal_display(output)

    def test_real_terminal_pipe_handoff_excludes_source_op(self):
        status, output = self.run_on_terminal(b"COPIED\n", credentials_pipe=True)
        self.assertEqual(status, 0)
        terminal = self.assert_single_terminal_display(output)
        displayed = dict(
            re.findall(r"^(Ki|Source OP|OPc):\s+([0-9a-f]{32})\r?$", terminal, re.MULTILINE)
        )
        expected = f"{displayed['Ki']}:{displayed['OPc']}\n".encode()
        self.assertTrue(output["credentials"] == expected)
        self.assertFalse(displayed["Source OP"].encode() in output["credentials"])

    def test_real_terminal_cancel_leaves_credentials_pipe_empty(self):
        status, output = self.run_on_terminal(b"CANCEL\n", credentials_pipe=True)
        self.assertEqual(status, 1)
        self.assert_single_terminal_display(output)
        self.assertEqual(len(output["credentials"]), 0)

    def test_cli_without_terminal_returns_failure_without_output_files(self):
        with tempfile.TemporaryDirectory(prefix="open5g2go-sim-test-") as directory:
            result = subprocess.run(
                [sys.executable, str(GENERATOR_PATH)],
                check=False,
                cwd=directory,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                start_new_session=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(len(result.stdout), 0)
            self.assertEqual(len(re.findall(rb"[0-9a-f]{32}", result.stderr)), 0)
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
