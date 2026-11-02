"""Keep lockfile audits independent of the interpreter running the scanner."""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "audit_python_lock", Path(__file__).resolve().parents[1] / "scripts/audit-python-lock.py"
)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def test_audits_alternate_versions_without_environment_markers():
    packages = [
        {
            "name": "example",
            "version": "1.0",
            "markers": "python_version < '3.12'",
            "files": [{"hash": "sha256:old"}],
        },
        {
            "name": "example",
            "version": "2.0",
            "markers": "python_version >= '3.12'",
            "files": [{"hash": "sha256:new"}],
        },
        {
            "name": "windows-only",
            "version": "3.0",
            "markers": "sys_platform == 'win32'",
            "files": [{"hash": "sha256:windows"}],
        },
    ]
    batches = list(AUDIT.requirement_batches(packages))
    assert len(batches) == 2
    assert "example==1.0 --hash=sha256:old\n" in batches[0]
    assert "example==2.0 --hash=sha256:new\n" in batches[1]
    assert "windows-only==3.0 --hash=sha256:windows\n" in batches[0]
    assert all(";" not in batch and "markers" not in batch for batch in batches)
    assert all(batch.count("example==") == 1 for batch in batches)


def test_rejects_an_empty_lock_instead_of_reporting_a_clean_audit():
    with pytest.raises(ValueError, match="no packages"):
        list(AUDIT.requirement_batches([]))
