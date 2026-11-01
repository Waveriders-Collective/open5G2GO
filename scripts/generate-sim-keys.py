#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Waveriders Collective Inc.

"""Display Milenage credentials once; hand only confirmed Ki/OPc to the wizard."""

import argparse
import os
import resource
import secrets
import stat
import sys
from typing import TextIO

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def derive_opc(ki: bytes, op: bytes) -> bytes:
    """Derive OPc as specified by 3GPP TS 35.206 section 4.1."""
    if len(ki) != 16 or len(op) != 16:
        raise ValueError("Ki and OP must each contain exactly 16 bytes")
    encryptor = Cipher(algorithms.AES(ki), modes.ECB()).encryptor()
    encrypted = encryptor.update(op) + encryptor.finalize()
    return bytes(left ^ right for left, right in zip(op, encrypted))


def generate_keys() -> tuple[bytes, bytes, bytes]:
    """Return independent random Ki/OP and their derived OPc, all 128 bits."""
    ki = secrets.token_bytes(16)
    op = secrets.token_bytes(16)
    return ki, op, derive_opc(ki, op)


def display_and_confirm(terminal_in: TextIO, terminal_out: TextIO) -> tuple[bytes, bytes] | None:
    """Write one credential block to the terminal and require explicit acknowledgement."""
    terminal_out.write(
        "\nWARNING: These credentials will be shown ONCE. Source OP will NEVER be saved.\n"
        "When used by setup, Ki and OPc are saved in .env for subscriber provisioning.\n"
        "Copy Ki, source OP, and OPc into your secure password manager now.\n"
        "Terminal scrollback or session recording may retain this display.\n"
        "Generated values require a SIM you can program; they cannot replace\n"
        "unknown keys on an existing vendor-programmed SIM.\n"
        "Program your SIM with the matching credentials before using it.\n\n"
    )
    terminal_out.flush()
    ki, op, opc = generate_keys()
    terminal_out.write(f"Ki:        {ki.hex()}\nSource OP: {op.hex()}\nOPc:       {opc.hex()}\n\n")
    terminal_out.flush()
    # Source OP never leaves this process except for its one terminal display.
    del op

    while True:
        terminal_out.write("Type COPIED after saving all three values, or CANCEL to stop: ")
        terminal_out.flush()
        response = terminal_in.readline()
        if not response or response.strip() == "CANCEL":
            terminal_out.write("\nSetup cancelled. The generated credentials were not saved.\n")
            terminal_out.flush()
            return None
        if response.strip() == "COPIED":
            terminal_out.write("\nCopy confirmed. Source OP will not be saved.\n")
            terminal_out.flush()
            return ki, opc
        terminal_out.write(
            "Confirmation required before continuing. Values will not be displayed again.\n"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--credentials-fd", type=int, help="Inherited pipe for confirmed Ki/OPc (never source OP)"
    )
    args = parser.parse_args(argv)
    try:
        # Keep a crash from creating a file containing the generated credentials.
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        if args.credentials_fd is not None and (
            args.credentials_fd < 3 or not stat.S_ISFIFO(os.fstat(args.credentials_fd).st_mode)
        ):
            raise ValueError("Credential handoff requires an inherited pipe above fd 2")
        # Never send credentials to stdout/stderr, which may have been redirected.
        with (
            open("/dev/tty", "r", encoding="utf-8") as terminal_in,
            open("/dev/tty", "w", encoding="utf-8", buffering=1) as terminal_out,
        ):
            if not terminal_in.isatty() or not terminal_out.isatty():
                raise OSError("No interactive terminal")
            credentials = display_and_confirm(terminal_in, terminal_out)
        if credentials is None:
            return 1
        if args.credentials_fd is not None:
            ki, opc = credentials
            with os.fdopen(args.credentials_fd, "w", encoding="ascii", closefd=False) as handoff:
                handoff.write(f"{ki.hex()}:{opc.hex()}\n")
        return 0
    except (OSError, ValueError, KeyboardInterrupt):
        print(
            "SIM key generation did not complete. Check cryptography support and the interactive terminal.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
