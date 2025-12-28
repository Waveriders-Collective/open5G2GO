# openSurfControl MVP Phase 1 - Tasks 16-60 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Date:** 2025-10-31
**Phase:** Complete MVP Implementation - Daemon API, FastAPI Backend, React Frontend
**Tasks:** 16-60 of Phase 1

---

## Overview

This plan completes the openSurfControl MVP implementation:
- **Tasks 16-20:** System integration, service management, validation
- **Tasks 21-30:** Core Management Daemon API server
- **Tasks 31-40:** FastAPI Backend (REST API, auth, daemon client)
- **Tasks 41-50:** React Frontend (UI components, pages, API integration)
- **Tasks 51-60:** Configuration templates, wizards, end-to-end testing

**Current State:**
- ✅ Tasks 1-15 completed (~65 passing tests, ~4,300 LOC)
- ✅ Complete Open5GSAdapter with monitoring
- ✅ Schema models, config generation, subscriber management
- ✅ Log parsing, device/radio detection, health monitoring

**Goal:** Complete web-based management platform with wizard-driven setup, device management, and real-time monitoring.

---

## Phase 2: System Integration (Tasks 16-20)

### Task 16: Service Management and Restart Orchestration

**Goal:** Implement safe service restart with proper ordering and validation

**Context:** When applying network config, Open5GS services must restart in correct order (HSS → MME → SGW → PGW for 4G). This task implements orchestrated restarts with health checks.

**Files:**
- Create: `opensurfcontrol/daemon/services/service_manager.py`
- Create: `tests/daemon/services/test_service_manager.py`

#### Step 1: Write test for service restart ordering

Create `tests/daemon/services/test_service_manager.py`:

```python
import pytest
from unittest.mock import Mock, patch, call
from daemon.services.service_manager import ServiceManager, ServiceRestartError


def test_restart_4g_services_in_correct_order():
    """Test 4G services restart in dependency order"""
    manager = ServiceManager()

    restart_order = []

    def track_restart(service):
        restart_order.append(service)
        return Mock(returncode=0)

    with patch("subprocess.run", side_effect=lambda cmd, **kwargs: track_restart(cmd[2])):
        manager.restart_4g_services()

    # Verify order: HSS → MME → SGWC → SGWU → SMFD → UPFD
    assert restart_order.index("open5gs-hssd") < restart_order.index("open5gs-mmed")
    assert restart_order.index("open5gs-mmed") < restart_order.index("open5gs-sgwcd")
    assert restart_order.index("open5gs-sgwcd") < restart_order.index("open5gs-sgwud")


def test_restart_5g_services_in_correct_order():
    """Test 5G services restart in dependency order"""
    manager = ServiceManager()

    restart_order = []

    def track_restart(service):
        restart_order.append(service)
        return Mock(returncode=0)

    with patch("subprocess.run", side_effect=lambda cmd, **kwargs: track_restart(cmd[2])):
        manager.restart_5g_services()

    # Verify order: UDM → AUSF → NRF → AMF → SMF → UPF
    assert restart_order.index("open5gs-udmd") < restart_order.index("open5gs-ausfd")
    assert restart_order.index("open5gs-nrfd") < restart_order.index("open5gs-amfd")


def test_wait_for_service_ready():
    """Test waiting for service to become active"""
    manager = ServiceManager()

    # Mock service becoming active after 2 checks
    call_count = 0
    def mock_check(cmd, **kwargs):
        nonlocal call_count
        call_count += 1
        result = Mock()
        result.stdout = "active" if call_count >= 2 else "activating"
        result.returncode = 0 if call_count >= 2 else 3
        return result

    with patch("subprocess.run", side_effect=mock_check), \
         patch("time.sleep"):

        ready = manager.wait_for_service_ready("open5gs-mmed", timeout=10)

    assert ready is True
    assert call_count >= 2


def test_restart_fails_if_service_doesnt_start():
    """Test restart failure when service won't start"""
    manager = ServiceManager()

    # Mock service that never becomes active
    def mock_check(cmd, **kwargs):
        result = Mock()
        result.stdout = "failed"
        result.returncode = 1
        return result

    with patch("subprocess.run", side_effect=mock_check), \
         patch("time.sleep"):

        with pytest.raises(ServiceRestartError, match="failed to start"):
            manager.restart_service_with_validation("open5gs-mmed")


def test_rollback_on_restart_failure():
    """Test automatic rollback when restart fails"""
    manager = ServiceManager()

    services_restarted = []

    def mock_restart(cmd, **kwargs):
        service = cmd[2]
        services_restarted.append(service)

        # Fail on third service
        if len(services_restarted) == 3:
            raise Exception("Service failed to start")

        return Mock(returncode=0)

    with patch("subprocess.run", side_effect=mock_restart):
        with pytest.raises(ServiceRestartError):
            manager.restart_4g_services()

    # Should have attempted to restart first 3 services
    assert len(services_restarted) == 3
```

#### Step 2: Run tests to verify they fail

```bash
poetry run pytest tests/daemon/services/test_service_manager.py -v
```

Expected: FAIL with "No module named 'daemon.services.service_manager'"

#### Step 3: Implement service manager

Create `opensurfcontrol/daemon/services/__init__.py`:

```python
"""Service management for Open5GS"""
```

Create `opensurfcontrol/daemon/services/service_manager.py`:

```python
"""Manage Open5GS service lifecycle with proper ordering"""

import time
import subprocess
from typing import List, Literal
from dataclasses import dataclass


class ServiceRestartError(Exception):
    """Raised when service restart fails"""
    pass


@dataclass
class ServiceDefinition:
    """Service with dependencies"""
    name: str
    depends_on: List[str]
    startup_delay: float = 2.0  # Seconds to wait after starting


class ServiceManager:
    """Manage Open5GS service restarts with dependency ordering"""

    # 4G EPC service dependencies
    EPC_SERVICES = [
        ServiceDefinition("open5gs-hssd", []),
        ServiceDefinition("open5gs-pcrfd", []),
        ServiceDefinition("open5gs-mmed", ["open5gs-hssd"]),
        ServiceDefinition("open5gs-sgwcd", ["open5gs-mmed"]),
        ServiceDefinition("open5gs-sgwud", ["open5gs-sgwcd"]),
        ServiceDefinition("open5gs-smfd", ["open5gs-sgwcd"]),
        ServiceDefinition("open5gs-upfd", ["open5gs-smfd"]),
    ]

    # 5G SA service dependencies
    SA_SERVICES = [
        ServiceDefinition("open5gs-udmd", []),
        ServiceDefinition("open5gs-ausfd", ["open5gs-udmd"]),
        ServiceDefinition("open5gs-nrfd", []),
        ServiceDefinition("open5gs-pcfd", []),
        ServiceDefinition("open5gs-amfd", ["open5gs-nrfd", "open5gs-ausfd"]),
        ServiceDefinition("open5gs-smfd", ["open5gs-amfd"]),
        ServiceDefinition("open5gs-upfd", ["open5gs-smfd"]),
    ]

    def restart_4g_services(self):
        """Restart 4G EPC services in dependency order"""
        self._restart_services(self.EPC_SERVICES)

    def restart_5g_services(self):
        """Restart 5G SA services in dependency order"""
        self._restart_services(self.SA_SERVICES)

    def _restart_services(self, services: List[ServiceDefinition]):
        """Restart services with dependency ordering

        Args:
            services: List of service definitions

        Raises:
            ServiceRestartError: If any service fails to start
        """
        restarted = []

        try:
            for service in services:
                # Wait for dependencies
                for dep in service.depends_on:
                    if dep not in restarted:
                        raise ServiceRestartError(
                            f"Dependency {dep} not started for {service.name}"
                        )

                # Restart service
                self.restart_service_with_validation(service.name)

                # Wait for stability
                time.sleep(service.startup_delay)

                restarted.append(service.name)

        except Exception as e:
            # Rollback: stop all restarted services
            for service_name in reversed(restarted):
                try:
                    subprocess.run(
                        ["systemctl", "stop", service_name],
                        timeout=5
                    )
                except:
                    pass  # Best effort

            raise ServiceRestartError(
                f"Failed to restart services: {str(e)}"
            ) from e

    def restart_service_with_validation(self, service_name: str, timeout: int = 30):
        """Restart service and wait for it to become active

        Args:
            service_name: Systemd service name
            timeout: Maximum seconds to wait

        Raises:
            ServiceRestartError: If service fails to start
        """
        # Restart service
        result = subprocess.run(
            ["systemctl", "restart", service_name],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            raise ServiceRestartError(
                f"Failed to restart {service_name}: {result.stderr}"
            )

        # Wait for service to become active
        if not self.wait_for_service_ready(service_name, timeout):
            raise ServiceRestartError(
                f"Service {service_name} failed to start within {timeout}s"
            )

    def wait_for_service_ready(self, service_name: str, timeout: int = 30) -> bool:
        """Wait for service to become active

        Args:
            service_name: Systemd service name
            timeout: Maximum seconds to wait

        Returns:
            True if service became active, False otherwise
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.stdout.strip() == "active":
                return True

            time.sleep(1)

        return False
```

#### Step 4: Run tests to verify they pass

```bash
poetry run pytest tests/daemon/services/test_service_manager.py -v
```

Expected: PASS (all tests)

#### Step 5: Integrate with adapter

Modify `opensurfcontrol/daemon/core/open5gs/adapter.py`:

```python
from daemon.services.service_manager import ServiceManager

class Open5GSAdapter(CoreAdapter):
    def __init__(self, ...):
        # ... existing init ...
        self.service_mgr = ServiceManager()

    def _restart_services(self, network_type: str):
        """Restart Open5GS services with proper ordering

        Args:
            network_type: \"4G_LTE\" or \"5G_Standalone\"
        """
        if network_type == "4G_LTE":
            self.service_mgr.restart_4g_services()
        else:
            self.service_mgr.restart_5g_services()
```

#### Step 6: Commit

```bash
git add daemon/services/ tests/daemon/services/ daemon/core/open5gs/adapter.py
git commit -m "feat(daemon): add orchestrated service restart with validation

- Implement dependency-aware service restart ordering
- Validate service health after restart
- Add automatic rollback on failure
- Support both 4G EPC and 5G SA service chains
- Integrate with Open5GSAdapter"
```

---

### Task 17: Configuration Validation

**Goal:** Validate Waveriders config before applying to prevent core breakage

**Context:** Invalid configs (wrong IP formats, conflicting PLMN, etc.) can break Open5GS. This task adds comprehensive validation.

**Files:**
- Create: `opensurfcontrol/daemon/services/config_validator.py`
- Create: `tests/daemon/services/test_config_validator.py`

#### Step 1: Write validation tests

Create `tests/daemon/services/test_config_validator.py`:

```python
import pytest
from daemon.services.config_validator import ConfigValidator, ValidationError
from daemon.models.schema import (
    WaveridersConfig,
    NetworkIdentity,
    IPAddressing,
    RadioParameters,
    NetworkSlice
)


def test_validate_valid_4g_config():
    """Test validation passes for valid 4G config"""
    config = WaveridersConfig(
        network_type="4G_LTE",
        network_identity=NetworkIdentity(
            country_code="315",
            network_code="010",
            area_code=1,
            network_name="Test"
        ),
        ip_addressing=IPAddressing(
            core_address="10.48.0.5",
            device_pool="10.48.99.0/24",
            device_gateway="10.48.99.1"
        ),
        radio_parameters=RadioParameters(
            network_name="internet",
            frequency_band="CBRS_Band48"
        ),
        template_source="test"
    )

    validator = ConfigValidator()
    result = validator.validate(config)

    assert result.valid is True
    assert len(result.errors) == 0


def test_validate_5g_requires_network_slice():
    """Test 5G networks must have network slice"""
    config = WaveridersConfig(
        network_type="5G_Standalone",
        network_identity=NetworkIdentity(
            country_code="999",
            network_code="770",
            area_code=1,
            network_name="Test"
        ),
        ip_addressing=IPAddressing(
            core_address="10.48.0.5",
            device_pool="10.48.99.0/24",
            device_gateway="10.48.99.1"
        ),
        radio_parameters=RadioParameters(
            network_name="internet",
            frequency_band="3.5GHz_CBRS"
            # Missing network_slice!
        ),
        template_source="test"
    )

    validator = ConfigValidator()
    result = validator.validate(config)

    assert result.valid is False
    assert any("network_slice" in err.lower() for err in result.errors)


def test_validate_device_gateway_in_pool():
    """Test device gateway must be within device pool"""
    config = WaveridersConfig(
        network_type="4G_LTE",
        network_identity=NetworkIdentity(
            country_code="315",
            network_code="010",
            area_code=1,
            network_name="Test"
        ),
        ip_addressing=IPAddressing(
            core_address="10.48.0.5",
            device_pool="10.48.99.0/24",
            device_gateway="10.48.100.1"  # Outside pool!
        ),
        radio_parameters=RadioParameters(
            network_name="internet",
            frequency_band="CBRS_Band48"
        ),
        template_source="test"
    )

    validator = ConfigValidator()
    result = validator.validate(config)

    assert result.valid is False
    assert any("gateway" in err.lower() and "pool" in err.lower() for err in result.errors)


def test_validate_no_ip_conflicts():
    """Test core address and device pool don't overlap"""
    config = WaveridersConfig(
        network_type="4G_LTE",
        network_identity=NetworkIdentity(
            country_code="315",
            network_code="010",
            area_code=1,
            network_name="Test"
        ),
        ip_addressing=IPAddressing(
            core_address="10.48.99.5",  # Inside device pool!
            device_pool="10.48.99.0/24",
            device_gateway="10.48.99.1"
        ),
        radio_parameters=RadioParameters(
            network_name="internet",
            frequency_band="CBRS_Band48"
        ),
        template_source="test"
    )

    validator = ConfigValidator()
    result = validator.validate(config)

    assert result.valid is False
    assert any("conflict" in err.lower() or "overlap" in err.lower() for err in result.errors)


def test_validate_plmn_format():
    """Test PLMN validation (MCC + MNC)"""
    config = WaveridersConfig(
        network_type="4G_LTE",
        network_identity=NetworkIdentity(
            country_code="001",  # Valid test PLMN
            network_code="01",
            area_code=1,
            network_name="Test"
        ),
        ip_addressing=IPAddressing(
            core_address="10.48.0.5",
            device_pool="10.48.99.0/24",
            device_gateway="10.48.99.1"
        ),
        radio_parameters=RadioParameters(
            network_name="internet",
            frequency_band="CBRS_Band48"
        ),
        template_source="test"
    )

    validator = ConfigValidator()
    result = validator.validate(config)

    # Should pass - 001-01 is valid test PLMN
    assert result.valid is True
```

#### Step 2: Implement validator

Create `opensurfcontrol/daemon/services/config_validator.py`:

```python
"""Validate Waveriders configuration before deployment"""

import ipaddress
from typing import List
from dataclasses import dataclass

from daemon.models.schema import WaveridersConfig


@dataclass
class ValidationResult:
    """Configuration validation result"""
    valid: bool
    errors: List[str]
    warnings: List[str]


class ValidationError(Exception):
    """Configuration validation error"""
    pass


class ConfigValidator:
    """Validate Waveriders network configuration"""

    def validate(self, config: WaveridersConfig) -> ValidationResult:
        """Validate complete network configuration

        Args:
            config: Waveriders configuration to validate

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        # Network type specific validation
        if config.network_type == "5G_Standalone":
            if config.radio_parameters.network_slice is None:
                errors.append("5G networks require network_slice configuration")

        # IP addressing validation
        ip_errors = self._validate_ip_addressing(config.ip_addressing)
        errors.extend(ip_errors)

        # PLMN validation
        plmn_warnings = self._validate_plmn(config.network_identity)
        warnings.extend(plmn_warnings)

        # Network name validation
        if not config.radio_parameters.network_name:
            errors.append("Network name (APN/DNN) is required")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _validate_ip_addressing(self, addressing) -> List[str]:
        """Validate IP addressing configuration

        Args:
            addressing: IPAddressing object

        Returns:
            List of error messages
        """
        errors = []

        try:
            core_ip = ipaddress.ip_address(addressing.core_address)
            device_network = ipaddress.ip_network(addressing.device_pool, strict=False)
            gateway_ip = ipaddress.ip_address(addressing.device_gateway)

            # Check gateway is in device pool
            if gateway_ip not in device_network:
                errors.append(
                    f"Device gateway {addressing.device_gateway} is not in "
                    f"device pool {addressing.device_pool}"
                )

            # Check core address doesn't conflict with device pool
            if core_ip in device_network:
                errors.append(
                    f"Core address {addressing.core_address} conflicts with "
                    f"device pool {addressing.device_pool}"
                )

            # Validate DNS servers
            for dns in addressing.dns_servers:
                try:
                    ipaddress.ip_address(dns)
                except ValueError:
                    errors.append(f"Invalid DNS server IP: {dns}")

        except ValueError as e:
            errors.append(f"Invalid IP configuration: {str(e)}")

        return errors

    def _validate_plmn(self, identity) -> List[str]:
        """Validate PLMN configuration

        Args:
            identity: NetworkIdentity object

        Returns:
            List of warning messages
        """
        warnings = []

        mcc = identity.country_code
        mnc = identity.network_code

        # Warn about test PLMNs (001-01)
        if mcc == "001" and mnc == "01":
            warnings.append(
                "Using test PLMN 001-01 - acceptable for lab use only"
            )

        # Warn about common conflicts
        if mcc == "310" or mcc == "311":
            warnings.append(
                f"MCC {mcc} is allocated to commercial US carriers - "
                "ensure MNC doesn't conflict with existing networks"
            )

        return warnings
```

#### Step 3: Integrate with adapter

Modify `opensurfcontrol/daemon/core/open5gs/adapter.py`:

```python
from daemon.services.config_validator import ConfigValidator, ValidationError

class Open5GSAdapter(CoreAdapter):
    def apply_network_config(self, config: WaveridersConfig) -> Result:
        """Deploy network configuration with validation"""
        try:
            # Validate configuration first
            validator = ConfigValidator()
            validation = validator.validate(config)

            if not validation.valid:
                return Result(
                    success=False,
                    message="Configuration validation failed",
                    error="; ".join(validation.errors)
                )

            # Log warnings
            for warning in validation.warnings:
                # TODO: Add proper logging
                pass

            # Proceed with deployment...
            # (existing implementation)
```

#### Step 4: Run tests and commit

```bash
poetry run pytest tests/daemon/services/test_config_validator.py -v
git add daemon/services/config_validator.py tests/daemon/services/test_config_validator.py daemon/core/open5gs/adapter.py
git commit -m "feat(daemon): add configuration validation

- Validate IP addressing and network ranges
- Ensure gateway is within device pool
- Prevent IP conflicts between core and devices
- Validate 5G requires network slice
- Warn about test PLMNs and potential conflicts
- Integrate validation into config deployment"
```

---

### Task 18: System Health Monitoring API

**Goal:** Create structured API for monitoring that daemon will expose

**Context:** The monitor returns raw objects. This task creates a clean API layer for consumption by web backend.

**Files:**
- Modify: `opensurfcontrol/daemon/core/open5gs/adapter.py`
- Create: `tests/daemon/core/open5gs/test_monitoring_api.py`

#### Step 1: Write monitoring API tests

Create `tests/daemon/core/open5gs/test_monitoring_api.py`:

```python
import pytest
from unittest.mock import Mock, patch
from daemon.core.open5gs.adapter import Open5GSAdapter
from daemon.core.abstract import CoreStatus


def test_get_dashboard_summary():
    """Test getting dashboard summary with all stats"""
    with patch("daemon.core.open5gs.adapter.MongoClient"):
        adapter = Open5GSAdapter()

    # Mock monitoring data
    adapter.monitor.get_core_status = Mock(
        return_value=CoreStatus(overall="healthy", components={})
    )
    adapter.monitor.get_connected_radios = Mock(return_value=[
        Mock(name="Radio-1", status="connected"),
        Mock(name="Radio-2", status="connected")
    ])
    adapter.monitor.get_connected_devices = Mock(return_value=[
        Mock(imsi="315010000000001", status="connected", uplink_mbps=45.0, downlink_mbps=2.0),
        Mock(imsi="315010000000002", status="connected", uplink_mbps=42.0, downlink_mbps=3.0),
        Mock(imsi="315010000000003", status="connected", uplink_mbps=38.0, downlink_mbps=2.5)
    ])

    summary = adapter.get_dashboard_summary()

    assert summary["core_status"] == "healthy"
    assert summary["radios_connected"] == 2
    assert summary["devices_connected"] == 3
    assert summary["total_uplink_mbps"] == pytest.approx(125.0)
    assert summary["total_downlink_mbps"] == pytest.approx(7.5)


def test_get_device_groups_summary():
    """Test aggregating devices by group"""
    with patch("daemon.core.open5gs.adapter.MongoClient"):
        adapter = Open5GSAdapter()

    adapter.monitor.get_connected_devices = Mock(return_value=[
        Mock(imsi="001", group="Cameras", uplink_mbps=45.0),
        Mock(imsi="002", group="Cameras", uplink_mbps=42.0),
        Mock(imsi="003", group="Crew", uplink_mbps=5.0),
        Mock(imsi="004", group=None, uplink_mbps=1.0),  # No group
    ])

    groups = adapter.get_device_groups_summary()

    assert "Cameras" in groups
    assert groups["Cameras"]["device_count"] == 2
    assert groups["Cameras"]["total_uplink_mbps"] == pytest.approx(87.0)

    assert "Crew" in groups
    assert groups["Crew"]["device_count"] == 1

    assert "Ungrouped" in groups
    assert groups["Ungrouped"]["device_count"] == 1
```

#### Step 2: Implement monitoring API methods

Modify `opensurfcontrol/daemon/core/open5gs/adapter.py`:

```python
from typing import Dict, Any

class Open5GSAdapter(CoreAdapter):
    # ... existing methods ...

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get high-level dashboard summary

        Returns:
            Dict with overall network stats
        """
        core_status = self.get_core_status()
        radios = self.get_connected_radios()
        devices = self.get_connected_devices()

        # Aggregate throughput
        total_uplink = sum(d.uplink_mbps for d in devices)
        total_downlink = sum(d.downlink_mbps for d in devices)

        return {
            "core_status": core_status.overall,
            "radios_connected": len(radios),
            "devices_connected": len(devices),
            "total_uplink_mbps": round(total_uplink, 2),
            "total_downlink_mbps": round(total_downlink, 2),
        }

    def get_device_groups_summary(self) -> Dict[str, Dict[str, Any]]:
        """Aggregate device statistics by group

        Returns:
            Dict mapping group names to group stats
        """
        devices = self.get_connected_devices()
        groups: Dict[str, Dict[str, Any]] = {}

        for device in devices:
            group_name = device.group or "Ungrouped"

            if group_name not in groups:
                groups[group_name] = {
                    "device_count": 0,
                    "total_uplink_mbps": 0.0,
                    "total_downlink_mbps": 0.0,
                    "devices": []
                }

            groups[group_name]["device_count"] += 1
            groups[group_name]["total_uplink_mbps"] += device.uplink_mbps
            groups[group_name]["total_downlink_mbps"] += device.downlink_mbps
            groups[group_name]["devices"].append({
                "imsi": device.imsi,
                "name": device.name,
                "ip_address": device.ip_address,
                "status": device.status
            })

        return groups
```

#### Step 3: Test and commit

```bash
poetry run pytest tests/daemon/core/open5gs/test_monitoring_api.py -v
git add daemon/core/open5gs/adapter.py tests/daemon/core/open5gs/test_monitoring_api.py
git commit -m "feat(daemon): add monitoring API for dashboard

- Add dashboard summary with aggregated stats
- Implement device grouping summary
- Calculate total throughput across all devices
- Provide structured data for web UI consumption"
```

---

### Task 19: Configuration Backup and Restore

**Goal:** Enhance backup system with list, restore, and cleanup capabilities

**Context:** Currently backups are created but there's no way to list or manually restore them. This task adds management capabilities.

**Files:**
- Create: `opensurfcontrol/daemon/services/backup_manager.py`
- Create: `tests/daemon/services/test_backup_manager.py`

#### Step 1: Write backup management tests

Create `tests/daemon/services/test_backup_manager.py`:

```python
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timedelta
from daemon.services.backup_manager import BackupManager, Backup


def test_list_backups():
    """Test listing all available backups"""
    with TemporaryDirectory() as tmpdir:
        backup_dir = Path(tmpdir)
        manager = BackupManager(backup_dir)

        # Create some backup directories
        (backup_dir / "backup_20251030_120000").mkdir()
        (backup_dir / "backup_20251030_130000").mkdir()
        (backup_dir / "backup_20251031_140000").mkdir()

        backups = manager.list_backups()

        assert len(backups) == 3
        assert backups[0].id == "backup_20251031_140000"  # Newest first


def test_get_backup_info():
    """Test getting detailed backup information"""
    with TemporaryDirectory() as tmpdir:
        backup_dir = Path(tmpdir)
        manager = BackupManager(backup_dir)

        backup_path = backup_dir / "backup_20251031_140000"
        backup_path.mkdir()
        (backup_path / "mme.yaml").write_text("config")

        backup = manager.get_backup_info("backup_20251031_140000")

        assert backup is not None
        assert backup.id == "backup_20251031_140000"
        assert backup.file_count >= 1
        assert backup.size_bytes > 0


def test_cleanup_old_backups():
    """Test automatic cleanup of old backups"""
    with TemporaryDirectory() as tmpdir:
        backup_dir = Path(tmpdir)
        manager = BackupManager(backup_dir, max_backups=3)

        # Create 5 backups
        for i in range(5):
            (backup_dir / f"backup_2025103{i}_120000").mkdir()

        # Cleanup should remove 2 oldest
        removed = manager.cleanup_old_backups()

        assert removed == 2
        assert len(list(backup_dir.iterdir())) == 3


def test_restore_backup():
    """Test restoring from backup"""
    with TemporaryDirectory() as tmpdir:
        backup_dir = Path(tmpdir) / "backups"
        config_dir = Path(tmpdir) / "config"
        backup_dir.mkdir()
        config_dir.mkdir()

        manager = BackupManager(backup_dir)

        # Create backup with config
        backup_path = backup_dir / "backup_20251031_140000"
        backup_path.mkdir()
        (backup_path / "mme.yaml").write_text("backup config")

        # Create current config (different)
        (config_dir / "mme.yaml").write_text("current config")

        # Restore
        success = manager.restore_backup("backup_20251031_140000", config_dir)

        assert success is True
        assert (config_dir / "mme.yaml").read_text() == "backup config"
```

#### Step 2: Implement backup manager

Create `opensurfcontrol/daemon/services/backup_manager.py`:

```python
"""Manage configuration backups"""

import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class Backup:
    """Backup metadata"""
    id: str
    path: Path
    timestamp: datetime
    file_count: int
    size_bytes: int


class BackupManager:
    """Manage configuration backups"""

    def __init__(self, backup_dir: Path, max_backups: int = 10):
        """Initialize backup manager

        Args:
            backup_dir: Directory for backups
            max_backups: Maximum backups to keep
        """
        self.backup_dir = backup_dir
        self.max_backups = max_backups
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def list_backups(self) -> List[Backup]:
        """List all available backups

        Returns:
            List of backups, newest first
        """
        backups = []

        for backup_path in self.backup_dir.iterdir():
            if backup_path.is_dir() and backup_path.name.startswith("backup_"):
                backup = self.get_backup_info(backup_path.name)
                if backup:
                    backups.append(backup)

        # Sort by timestamp, newest first
        backups.sort(key=lambda b: b.timestamp, reverse=True)

        return backups

    def get_backup_info(self, backup_id: str) -> Optional[Backup]:
        """Get detailed backup information

        Args:
            backup_id: Backup identifier

        Returns:
            Backup object or None if not found
        """
        backup_path = self.backup_dir / backup_id

        if not backup_path.exists():
            return None

        # Parse timestamp from backup_id (format: backup_YYYYMMDD_HHMMSS)
        try:
            timestamp_str = backup_id.replace("backup_", "")
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
        except:
            timestamp = datetime.fromtimestamp(backup_path.stat().st_mtime)

        # Calculate size and file count
        file_count = 0
        size_bytes = 0
        for file in backup_path.rglob("*"):
            if file.is_file():
                file_count += 1
                size_bytes += file.stat().st_size

        return Backup(
            id=backup_id,
            path=backup_path,
            timestamp=timestamp,
            file_count=file_count,
            size_bytes=size_bytes
        )

    def restore_backup(self, backup_id: str, target_dir: Path) -> bool:
        """Restore configuration from backup

        Args:
            backup_id: Backup to restore
            target_dir: Directory to restore to

        Returns:
            True if successful
        """
        backup_path = self.backup_dir / backup_id

        if not backup_path.exists():
            return False

        # Remove current configs
        for file in target_dir.glob("*.yaml"):
            file.unlink()

        # Copy backup files
        shutil.copytree(backup_path, target_dir, dirs_exist_ok=True)

        return True

    def cleanup_old_backups(self) -> int:
        """Remove old backups exceeding max_backups limit

        Returns:
            Number of backups removed
        """
        backups = self.list_backups()

        if len(backups) <= self.max_backups:
            return 0

        # Remove oldest backups
        to_remove = backups[self.max_backups:]
        removed = 0

        for backup in to_remove:
            try:
                shutil.rmtree(backup.path)
                removed += 1
            except:
                pass  # Best effort

        return removed
```

#### Step 3: Integrate with adapter

Modify `opensurfcontrol/daemon/core/open5gs/adapter.py`:

```python
from daemon.services.backup_manager import BackupManager, Backup

class Open5GSAdapter(CoreAdapter):
    def __init__(self, ...):
        # ... existing init ...
        self.backup_mgr = BackupManager(backup_dir)

    def list_config_backups(self) -> List[Backup]:
        """List available configuration backups"""
        return self.backup_mgr.list_backups()

    def restore_config_backup(self, backup_id: str) -> Result:
        """Restore configuration from backup

        Args:
            backup_id: Backup identifier

        Returns:
            Result with success/failure
        """
        try:
            success = self.backup_mgr.restore_backup(backup_id, self.config_dir)

            if success:
                # Restart services after restore
                # (User should specify network type, or detect from config)
                return Result(
                    success=True,
                    message=f"Configuration restored from {backup_id}"
                )
            else:
                return Result(
                    success=False,
                    message="Backup not found",
                    error=f"No backup with ID {backup_id}"
                )

        except Exception as e:
            return Result(
                success=False,
                message="Failed to restore backup",
                error=str(e)
            )
```

#### Step 4: Test and commit

```bash
poetry run pytest tests/daemon/services/test_backup_manager.py -v
git add daemon/services/backup_manager.py tests/daemon/services/test_backup_manager.py daemon/core/open5gs/adapter.py
git commit -m "feat(daemon): add backup management capabilities

- List available configuration backups
- Get detailed backup information (size, files, timestamp)
- Restore from backup
- Automatic cleanup of old backups
- Integrate backup management with adapter"
```

---

### Task 20: Error Handling and Logging

**Goal:** Add comprehensive error handling and structured logging

**Context:** Current implementation has basic error handling. This task adds structured logging and better error messages for troubleshooting.

**Files:**
- Create: `opensurfcontrol/daemon/utils/logging.py`
- Modify: Various daemon files to add logging
- Create: `tests/daemon/utils/test_logging.py`

#### Step 1: Write logging utility tests

Create `tests/daemon/utils/test_logging.py`:

```python
import pytest
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from daemon.utils.logging import setup_logging, get_logger


def test_setup_logging_creates_file():
    """Test logging creates log file"""
    with TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"

        setup_logging(log_file=log_file, log_level=logging.INFO)

        logger = get_logger("test")
        logger.info("Test message")

        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content


def test_logging_includes_context():
    """Test log messages include useful context"""
    with TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"

        setup_logging(log_file=log_file)

        logger = get_logger("daemon.core")
        logger.info("Network deployed", extra={
            "network_type": "4G_LTE",
            "plmn": "315-010"
        })

        content = log_file.read_text()
        assert "daemon.core" in content
        assert "Network deployed" in content


def test_error_logging_includes_traceback():
    """Test errors include full traceback"""
    with TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"

        setup_logging(log_file=log_file)

        logger = get_logger("test")

        try:
            raise ValueError("Test error")
        except Exception as e:
            logger.error("Operation failed", exc_info=True)

        content = log_file.read_text()
        assert "ValueError: Test error" in content
        assert "Traceback" in content
```

#### Step 2: Implement logging utilities

Create `opensurfcontrol/daemon/utils/__init__.py`:

```python
"""Utility modules"""
```

Create `opensurfcontrol/daemon/utils/logging.py`:

```python
"""Structured logging configuration"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_file: Optional[Path] = None,
    log_level: int = logging.INFO,
    format_string: Optional[str] = None
):
    """Configure logging for daemon

    Args:
        log_file: Path to log file (None for stdout only)
        log_level: Logging level
        format_string: Custom format string
    """
    if format_string is None:
        format_string = (
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s "
            "(%(filename)s:%(lineno)d)"
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    formatter = logging.Formatter(format_string)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get logger for module

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger
    """
    return logging.getLogger(name)
```

#### Step 3: Add logging to key modules

Modify `opensurfcontrol/daemon/core/open5gs/adapter.py`:

```python
from daemon.utils.logging import get_logger

logger = get_logger(__name__)

class Open5GSAdapter(CoreAdapter):
    def apply_network_config(self, config: WaveridersConfig) -> Result:
        """Deploy network configuration"""
        logger.info(
            "Applying network configuration",
            extra={
                "network_type": config.network_type,
                "plmn": f"{config.network_identity.country_code}-{config.network_identity.network_code}"
            }
        )

        try:
            # ... existing implementation ...

            logger.info("Network configuration applied successfully")
            return Result(success=True, ...)

        except Exception as e:
            logger.error(
                "Failed to apply network configuration",
                exc_info=True,
                extra={"network_type": config.network_type}
            )
            return Result(success=False, ...)
```

Add similar logging to:
- `daemon/services/service_manager.py`
- `daemon/core/open5gs/monitor.py`
- `daemon/core/open5gs/subscriber_manager.py`

#### Step 4: Test and commit

```bash
poetry run pytest tests/daemon/utils/test_logging.py -v
git add daemon/utils/ tests/daemon/utils/ daemon/core/open5gs/adapter.py daemon/services/service_manager.py
git commit -m "feat(daemon): add structured logging framework

- Implement logging configuration with file and console output
- Add contextual logging with structured data
- Include tracebacks for error debugging
- Add logging to adapter, service manager, and monitor
- Support configurable log levels"
```

---

## Summary: Tasks 16-20 Complete

**What We Built:**
- ✅ **Task 16:** Orchestrated service restart with validation
- ✅ **Task 17:** Configuration validation before deployment
- ✅ **Task 18:** Monitoring API for dashboard consumption
- ✅ **Task 19:** Backup management (list, restore, cleanup)
- ✅ **Task 20:** Structured logging framework

**Current State:**
- **Tests:** 85+ passing
- **Tasks Completed:** 20 of 60+ (33%)
- **Phase Status:** System integration complete!

**Next Phase:** Tasks 21-30 will build the Core Management Daemon API server that the FastAPI backend will consume.

---

## Phase 3: Core Management Daemon API (Tasks 21-30)

### Task 21: Daemon API Server Setup

**Goal:** Create HTTP API server for daemon using FastAPI

**Context:** The daemon needs an internal API for the web backend to consume. This uses FastAPI on localhost or Unix socket.

**Files:**
- Create: `opensurfcontrol/daemon/api/__init__.py`
- Create: `opensurfcontrol/daemon/api/server.py`
- Create: `opensurfcontrol/daemon/api/models.py`
- Create: `tests/daemon/api/test_server.py`

#### Step 1: Write API server tests

Create `tests/daemon/api/test_server.py`:

```python
import pytest
from fastapi.testclient import TestClient
from daemon.api.server import create_app


@pytest.fixture
def client():
    """Create test client"""
    app = create_app()
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_api_version(client):
    """Test API returns version"""
    response = client.get("/version")

    assert response.status_code == 200
    assert "version" in response.json()


def test_api_requires_adapter():
    """Test API fails gracefully without adapter"""
    app = create_app(adapter=None)
    client = TestClient(app)

    response = client.get("/status/core")

    # Should return error when adapter not configured
    assert response.status_code == 503
```

#### Step 2: Implement daemon API server

Create `opensurfcontrol/daemon/api/__init__.py`:

```python
"""Internal API server for daemon"""
```

Create `opensurfcontrol/daemon/api/models.py`:

```python
"""Pydantic models for daemon API"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str


class VersionResponse(BaseModel):
    """Version information"""
    version: str
    api_version: str


class CoreStatusResponse(BaseModel):
    """Core health status"""
    overall: str
    components: Dict[str, str]


class RadioSiteResponse(BaseModel):
    """Radio site information"""
    name: str
    ip_address: str
    status: str
    type: str


class DeviceResponse(BaseModel):
    """Connected device"""
    imsi: str
    name: str
    ip_address: str
    status: str
    group: Optional[str]
    uplink_mbps: float
    downlink_mbps: float


class DashboardSummaryResponse(BaseModel):
    """Dashboard summary statistics"""
    core_status: str
    radios_connected: int
    devices_connected: int
    total_uplink_mbps: float
    total_downlink_mbps: float


class NetworkConfigRequest(BaseModel):
    """Network configuration deployment request"""
    config: Dict[str, Any]  # Waveriders config as dict


class ResultResponse(BaseModel):
    """Operation result"""
    success: bool
    message: str
    error: Optional[str] = None
```

Create `opensurfcontrol/daemon/api/server.py`:

```python
"""FastAPI server for daemon internal API"""

from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse

from daemon.api.models import (
    HealthResponse,
    VersionResponse,
    CoreStatusResponse,
    RadioSiteResponse,
    DeviceResponse,
    DashboardSummaryResponse,
    ResultResponse,
    NetworkConfigRequest
)
from daemon.core.abstract import CoreAdapter
from daemon.models.schema import WaveridersConfig
from daemon.utils.logging import get_logger

logger = get_logger(__name__)

# Global adapter instance (set on startup)
_adapter: Optional[CoreAdapter] = None


def create_app(adapter: Optional[CoreAdapter] = None) -> FastAPI:
    """Create FastAPI application

    Args:
        adapter: Core adapter instance

    Returns:
        Configured FastAPI app
    """
    global _adapter
    _adapter = adapter

    app = FastAPI(
        title="openSurfControl Daemon API",
        description="Internal API for mobile core management",
        version="0.1.0"
    )

    @app.get("/health", response_model=HealthResponse)
    async def health():
        """Health check endpoint"""
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat()
        )

    @app.get("/version", response_model=VersionResponse)
    async def version():
        """Get version information"""
        return VersionResponse(
            version="0.1.0",
            api_version="v1"
        )

    @app.get("/status/core", response_model=CoreStatusResponse)
    async def get_core_status():
        """Get core health status"""
        if _adapter is None:
            raise HTTPException(status_code=503, detail="Adapter not configured")

        status = _adapter.get_core_status()

        return CoreStatusResponse(
            overall=status.overall,
            components=status.components
        )

    @app.get("/status/radios", response_model=list[RadioSiteResponse])
    async def get_radios():
        """Get connected radio sites"""
        if _adapter is None:
            raise HTTPException(status_code=503, detail="Adapter not configured")

        radios = _adapter.get_connected_radios()

        return [
            RadioSiteResponse(
                name=r.name,
                ip_address=r.ip_address,
                status=r.status,
                type=r.type
            )
            for r in radios
        ]

    @app.get("/status/devices", response_model=list[DeviceResponse])
    async def get_devices():
        """Get connected devices"""
        if _adapter is None:
            raise HTTPException(status_code=503, detail="Adapter not configured")

        devices = _adapter.get_connected_devices()

        return [
            DeviceResponse(
                imsi=d.imsi,
                name=d.name,
                ip_address=d.ip_address,
                status=d.status,
                group=d.group,
                uplink_mbps=d.uplink_mbps,
                downlink_mbps=d.downlink_mbps
            )
            for d in devices
        ]

    @app.get("/dashboard/summary", response_model=DashboardSummaryResponse)
    async def get_dashboard_summary():
        """Get dashboard summary"""
        if _adapter is None:
            raise HTTPException(status_code=503, detail="Adapter not configured")

        summary = _adapter.get_dashboard_summary()

        return DashboardSummaryResponse(**summary)

    @app.post("/config/apply", response_model=ResultResponse)
    async def apply_config(request: NetworkConfigRequest):
        """Apply network configuration"""
        if _adapter is None:
            raise HTTPException(status_code=503, detail="Adapter not configured")

        # Parse config dict to WaveridersConfig
        config = WaveridersConfig(**request.config)

        result = _adapter.apply_network_config(config)

        return ResultResponse(
            success=result.success,
            message=result.message,
            error=result.error
        )

    return app
```

#### Step 3: Create daemon entry point

Create `opensurfcontrol/daemon/main.py`:

```python
"""Daemon main entry point"""

import argparse
import uvicorn
from pathlib import Path

from daemon.api.server import create_app
from daemon.core.factory import create_adapter
from daemon.utils.logging import setup_logging, get_logger


def main():
    """Main daemon entry point"""
    parser = argparse.ArgumentParser(description="openSurfControl Daemon")
    parser.add_argument("--host", default="127.0.0.1", help="API host")
    parser.add_argument("--port", type=int, default=5001, help="API port")
    parser.add_argument("--log-file", type=Path, help="Log file path")
    parser.add_argument("--core-type", choices=["open5gs", "attocore"], help="Force core type")

    args = parser.parse_args()

    # Setup logging
    setup_logging(log_file=args.log_file)
    logger = get_logger(__name__)

    logger.info("Starting openSurfControl daemon")

    # Create core adapter
    try:
        adapter = create_adapter(args.core_type)
        logger.info(f"Initialized adapter: {type(adapter).__name__}")
    except Exception as e:
        logger.error(f"Failed to initialize adapter: {e}")
        return 1

    # Create API server
    app = create_app(adapter=adapter)

    # Run server
    logger.info(f"Starting API server on {args.host}:{args.port}")
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_config=None  # Use our logging config
    )


if __name__ == "__main__":
    main()
```

#### Step 4: Test and commit

```bash
poetry run pytest tests/daemon/api/test_server.py -v

git add daemon/api/ daemon/main.py tests/daemon/api/
git commit -m "feat(daemon): add internal API server

- Implement FastAPI server for daemon
- Add health, version, and status endpoints
- Expose monitoring data via REST API
- Support network configuration deployment
- Add daemon main entry point"
```

---

**Note:** Due to response length constraints, I'm providing the framework and first few tasks in detail. The remaining tasks (22-60) would follow this same TDD pattern:

**Tasks 22-30** (Daemon API continued):
- Task 22: Device management endpoints (add/update/remove)
- Task 23: Backup management endpoints
- Task 24: QoS policy endpoints
- Task 25: Template management endpoints
- Task 26: WebSocket support for real-time updates
- Task 27: API authentication/authorization
- Task 28: API rate limiting
- Task 29: API documentation (OpenAPI/Swagger)
- Task 30: Daemon integration tests

**Tasks 31-40** (FastAPI Backend):
- Task 31: FastAPI project setup
- Task 32: Daemon client library
- Task 33: User authentication (JWT)
- Task 34: Configuration routes
- Task 35: Device management routes
- Task 36: Monitoring routes
- Task 37: Template routes
- Task 38: User management routes
- Task 39: WebSocket proxy
- Task 40: Backend integration tests

**Tasks 41-50** (React Frontend):
- Task 41: React project setup (Vite + TypeScript)
- Task 42: API client service
- Task 43: Authentication pages (login)
- Task 44: Dashboard page
- Task 45: Device management page
- Task 46: Group management UI
- Task 47: Configuration wizard (multi-step)
- Task 48: Monitoring dashboards
- Task 49: Settings page
- Task 50: Frontend E2E tests

**Tasks 51-60** (Templates & Integration):
- Task 51: Waveriders 4G template
- Task 52: Waveriders 5G template
- Task 53: Template validation
- Task 54: Template import/export
- Task 55: Quick start wizard
- Task 56: System integration tests
- Task 57: Performance testing
- Task 58: Documentation generation
- Task 59: VM packaging scripts
- Task 60: End-to-end acceptance tests

Would you like me to continue with the detailed implementation plans for specific task ranges?
