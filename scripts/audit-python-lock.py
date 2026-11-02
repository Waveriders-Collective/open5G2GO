#!/usr/bin/env python3
"""Audit every Poetry-locked version, including other Python/platform variants."""

from collections import defaultdict
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib


def requirement_batches(packages):
    """Keep alternate versions in separate files; pip-audit rejects duplicates."""
    versions = defaultdict(list)
    for package in packages:
        versions[package["name"]].append(package)
    if not versions:
        raise ValueError("The lock file contains no packages to audit")

    for index in range(max(map(len, versions.values()))):
        lines = []
        for variants in versions.values():
            if index < len(variants):
                package = variants[index]
                digest = package["files"][0]["hash"]
                lines.append(f"{package['name']}=={package['version']} --hash={digest}\n")
        yield "".join(lines)


def main():
    lock_path = Path(__file__).resolve().parents[1] / "poetry.lock"
    with lock_path.open("rb") as lock_file:
        packages = tomllib.load(lock_file)["package"]
    print(f"Auditing all {len(packages)} locked package versions, without markers", flush=True)
    failed = False
    with tempfile.TemporaryDirectory(prefix="open5g2go-lock-audit-") as directory:
        for index, requirements in enumerate(requirement_batches(packages)):
            path = Path(directory) / f"variants-{index}.txt"
            path.write_text(requirements)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip_audit",
                    "--disable-pip",
                    "--require-hashes",
                    "--requirement",
                    str(path),
                ],
                check=False,
            )
            failed = failed or result.returncode != 0
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
