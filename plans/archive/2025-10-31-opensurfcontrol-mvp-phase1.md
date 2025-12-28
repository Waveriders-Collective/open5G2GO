# openSurfControl MVP Phase 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the MVP of openSurfControl - a web-based management platform for Open5GS that abstracts 3GPP complexity into plain-English, intent-based networking.

**Architecture:** 3-tier system with React frontend, FastAPI backend, and Python Core Management Daemon. The daemon translates Waveriders unified schema into Open5GS-specific configs (YAML files, MongoDB, systemd services). Plain English terminology throughout (Core, Radio Sites, Devices instead of MME, eNodeB, UE).

**Tech Stack:** Python 3.11+, FastAPI, React/TypeScript, MongoDB, PyYAML, Pydantic, systemd

**Timeline:** 8-12 weeks (60+ tasks)

---

## Implementation Progress

**Status as of 2025-10-31:**
- **Tasks Completed:** 9 of 60+ (15%)
- **Commits:** 9 following conventional commit format
- **Tests:** 26 passing, 0 failing
- **Test Coverage:** Schema models (9), CoreAdapter (6), Open5GS config (5), MongoDB subscriber management (6)
- **Lines of Code:** ~1,800 lines of production code + tests
- **Development Environment:** Python 3.10 venv with Poetry

**Completed Tasks:**
- ✅ Task 1: Project Structure Setup
- ✅ Task 2: Waveriders Schema Models (NetworkIdentity)
- ✅ Task 3: IP Addressing Schema
- ✅ Task 4: Complete Waveriders Configuration Schema
- ✅ Task 5: CoreAdapter Abstract Interface
- ✅ Task 6: Open5GS Config Generation - MME and SMF
- ✅ Task 7: Open5GS Config Generation - Remaining Components (SGW-U, UPF, AMF)
- ✅ Task 8: MongoDB Subscriber Model and Connection
- ✅ Task 9: Subscriber CRUD Operations

**Git Commits:**
```
40c0199 feat(daemon): add subscriber CRUD operations
495177f feat(daemon): add MongoDB subscriber model and manager
fadd3bf feat(daemon): add Open5GS config generation for all components
142caa3 feat(daemon): add Open5GS config generator for MME and SMF
fef4432 feat(daemon): add CoreAdapter abstract interface
8f10b5a feat(daemon): complete Waveriders schema models
98c9e7e feat(daemon): add IPAddressing model
452ccba feat(daemon): add NetworkIdentity model
76806ac chore: initialize project structure
```

**Next Phase:** Tasks 10-15 (Open5GS monitoring, device detection, complete Open5GSAdapter implementation)

---

## Prerequisites

Before starting implementation:

1. Development environment:
   - Ubuntu 22.04 VM or LXC container
   - Python 3.11+
   - Node.js 18+
   - MongoDB 6.0+
   - Open5GS 2.7.6+ installed and operational

2. Git repository structure:
   ```
   opensurfcontrol/
   ├── daemon/           # Core Management Daemon
   ├── api/             # FastAPI Backend
   ├── frontend/        # React Frontend
   ├── tests/           # All tests
   └── docs/            # Documentation
   ```

3. Reference documentation:
   - Open5GS installation: https://open5gs.org/open5gs/docs/guide/01-quickstart/
   - Existing deployment docs: `/home/jr/development/projects/536/applications/open5gs.md`

---

## Phase 1: Foundation (Tasks 1-15)

### Task 1: Project Structure Setup

**Goal:** Initialize repository with proper structure and development tooling

**Files:**
- Create: `opensurfcontrol/README.md`
- Create: `opensurfcontrol/.gitignore`
- Create: `opensurfcontrol/pyproject.toml`
- Create: `opensurfcontrol/daemon/README.md`
- Create: `opensurfcontrol/api/README.md`
- Create: `opensurfcontrol/frontend/README.md`

**Step 1: Initialize git repository**

```bash
mkdir -p opensurfcontrol
cd opensurfcontrol
git init
git checkout -b main
```

**Step 2: Create root README**

Create `opensurfcontrol/README.md`:

```markdown
# openSurfControl

Web-based management platform for private 4G/5G cellular networks.

## Components

- **daemon/** - Core Management Daemon (Python)
- **api/** - FastAPI Backend
- **frontend/** - React Frontend

## Quick Start

See individual component READMEs for setup instructions.

## Documentation

Design document: `docs/plans/2025-10-31-opensurfcontrol-design.md`
```

**Step 3: Create .gitignore**

Create `opensurfcontrol/.gitignore`:

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
*.egg-info/
dist/
build/

# Node
node_modules/
npm-debug.log
yarn-error.log
.next/
out/
build/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# Environment
.env
.env.local

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/

# Logs
*.log
```

**Step 4: Create Python project config**

Create `opensurfcontrol/pyproject.toml`:

```toml
[tool.poetry]
name = "opensurfcontrol"
version = "0.1.0"
description = "Web-based management for private cellular networks"
authors = ["Waveriders Collective <info@waveriders.io>"]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"
pymongo = "^4.6.0"
pyyaml = "^6.0.1"
python-multipart = "^0.0.6"
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
httpx = "^0.25.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.3"
pytest-asyncio = "^0.21.1"
pytest-cov = "^4.1.0"
black = "^23.11.0"
ruff = "^0.1.6"
mypy = "^1.7.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

**Step 5: Create component READMEs**

Create `opensurfcontrol/daemon/README.md`:

```markdown
# Core Management Daemon

Translates Waveriders unified schema to core-specific implementations.

## Installation

```bash
poetry install
```

## Running

```bash
poetry run opensurfcontrol-daemon
```

## Testing

```bash
poetry run pytest tests/daemon/
```
```

Create similar READMEs for `api/` and `frontend/`.

**Step 6: Commit initial structure**

```bash
git add .
git commit -m "chore: initialize project structure

- Add Python/Node gitignore
- Configure Poetry with dependencies
- Set up component directories
- Add documentation structure"
```

---

### Task 2: Waveriders Schema Models (Pydantic)

**Goal:** Define the unified Waveriders configuration schema as Pydantic models

**Files:**
- Create: `opensurfcontrol/daemon/models/__init__.py`
- Create: `opensurfcontrol/daemon/models/schema.py`
- Create: `tests/daemon/models/test_schema.py`

**Step 1: Write failing test for network identity**

Create `tests/daemon/models/test_schema.py`:

```python
import pytest
from pydantic import ValidationError
from daemon.models.schema import NetworkIdentity


def test_network_identity_valid():
    """Test valid network identity creation"""
    identity = NetworkIdentity(
        country_code="315",
        network_code="010",
        area_code=1,
        network_name="Test Network"
    )
    assert identity.country_code == "315"
    assert identity.network_code == "010"
    assert identity.area_code == 1


def test_network_identity_invalid_mcc():
    """Test that invalid country code is rejected"""
    with pytest.raises(ValidationError):
        NetworkIdentity(
            country_code="99",  # Too short
            network_code="010",
            area_code=1,
            network_name="Test"
        )
```

**Step 2: Run test to verify it fails**

```bash
cd opensurfcontrol
poetry install
poetry run pytest tests/daemon/models/test_schema.py -v
```

Expected: FAIL with "No module named 'daemon'"

**Step 3: Write NetworkIdentity model**

Create `opensurfcontrol/daemon/models/__init__.py`:

```python
"""Waveriders unified schema models"""
```

Create `opensurfcontrol/daemon/models/schema.py`:

```python
"""Pydantic models for Waveriders unified configuration schema"""

from typing import Literal
from pydantic import BaseModel, Field, field_validator


class NetworkIdentity(BaseModel):
    """Network identity configuration (PLMN, TAC, name)"""

    country_code: str = Field(
        ...,
        description="Mobile Country Code (MCC) - 3 digits",
        examples=["315"]
    )
    network_code: str = Field(
        ...,
        description="Mobile Network Code (MNC) - 2-3 digits",
        examples=["010"]
    )
    area_code: int = Field(
        ...,
        description="Tracking Area Code (TAC)",
        ge=1,
        le=65535
    )
    network_name: str = Field(
        ...,
        description="Human-readable network name",
        min_length=1,
        max_length=64
    )

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        """Validate MCC is 3 digits"""
        if not v.isdigit() or len(v) != 3:
            raise ValueError("Country code must be 3 digits")
        return v

    @field_validator("network_code")
    @classmethod
    def validate_network_code(cls, v: str) -> str:
        """Validate MNC is 2-3 digits"""
        if not v.isdigit() or len(v) not in [2, 3]:
            raise ValueError("Network code must be 2-3 digits")
        return v
```

**Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/daemon/models/test_schema.py -v
```

Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add daemon/models/ tests/daemon/models/
git commit -m "feat(daemon): add NetworkIdentity model

- Define Waveriders network identity schema
- Validate MCC (3 digits) and MNC (2-3 digits)
- Test valid and invalid inputs"
```

---

### Task 3: IP Addressing Schema

**Goal:** Define IP addressing configuration model

**Files:**
- Modify: `opensurfcontrol/daemon/models/schema.py`
- Modify: `tests/daemon/models/test_schema.py`

**Step 1: Write failing test for IP addressing**

Add to `tests/daemon/models/test_schema.py`:

```python
from daemon.models.schema import IPAddressing


def test_ip_addressing_valid():
    """Test valid IP addressing configuration"""
    addressing = IPAddressing(
        architecture="direct_routing",
        core_address="10.48.0.5",
        device_pool="10.48.99.0/24",
        device_gateway="10.48.99.1",
        dns_servers=["8.8.8.8", "8.8.4.4"]
    )
    assert addressing.core_address == "10.48.0.5"
    assert addressing.device_pool == "10.48.99.0/24"


def test_ip_addressing_validates_cidr():
    """Test that invalid CIDR notation is rejected"""
    with pytest.raises(ValidationError):
        IPAddressing(
            architecture="direct_routing",
            core_address="10.48.0.5",
            device_pool="10.48.99.0",  # Missing /prefix
            device_gateway="10.48.99.1",
            dns_servers=["8.8.8.8"]
        )
```

**Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/daemon/models/test_schema.py::test_ip_addressing_valid -v
```

Expected: FAIL with "cannot import name 'IPAddressing'"

**Step 3: Implement IPAddressing model**

Add to `opensurfcontrol/daemon/models/schema.py`:

```python
import ipaddress
from typing import List


class IPAddressing(BaseModel):
    """IP addressing configuration"""

    architecture: Literal["direct_routing"] = Field(
        default="direct_routing",
        description="Waveriders standard: devices directly routable on LAN"
    )
    core_address: str = Field(
        ...,
        description="IP address of core control plane (MME/AMF)",
        examples=["10.48.0.5"]
    )
    device_pool: str = Field(
        ...,
        description="CIDR subnet for device IP assignments",
        examples=["10.48.99.0/24"]
    )
    device_gateway: str = Field(
        ...,
        description="Gateway IP for devices (ogstun interface)",
        examples=["10.48.99.1"]
    )
    dns_servers: List[str] = Field(
        default=["8.8.8.8", "8.8.4.4"],
        description="DNS servers for device internet access"
    )

    @field_validator("core_address", "device_gateway")
    @classmethod
    def validate_ip_address(cls, v: str) -> str:
        """Validate IP address format"""
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"Invalid IP address: {v}")
        return v

    @field_validator("device_pool")
    @classmethod
    def validate_cidr(cls, v: str) -> str:
        """Validate CIDR notation"""
        try:
            ipaddress.ip_network(v, strict=False)
        except ValueError:
            raise ValueError(f"Invalid CIDR notation: {v}")
        return v

    @field_validator("dns_servers")
    @classmethod
    def validate_dns_servers(cls, v: List[str]) -> List[str]:
        """Validate DNS server IPs"""
        for dns in v:
            try:
                ipaddress.ip_address(dns)
            except ValueError:
                raise ValueError(f"Invalid DNS server IP: {dns}")
        return v
```

**Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/daemon/models/test_schema.py::test_ip_addressing_valid -v
poetry run pytest tests/daemon/models/test_schema.py::test_ip_addressing_validates_cidr -v
```

Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add daemon/models/schema.py tests/daemon/models/test_schema.py
git commit -m "feat(daemon): add IPAddressing model

- Define IP addressing schema with validation
- Validate IP addresses and CIDR notation
- Default to Waveriders direct_routing architecture"
```

---

### Task 4: Complete Waveriders Configuration Schema

**Goal:** Complete remaining schema models (radio params, QoS, full config)

**Files:**
- Modify: `opensurfcontrol/daemon/models/schema.py`
- Modify: `tests/daemon/models/test_schema.py`

**Step 1: Write tests for remaining models**

Add to `tests/daemon/models/test_schema.py`:

```python
from daemon.models.schema import (
    RadioParameters,
    QoSPolicy,
    DeviceConfig,
    DeviceGroup,
    WaveridersConfig
)


def test_radio_parameters_4g():
    """Test 4G radio parameters"""
    radio = RadioParameters(
        network_name="internet",
        frequency_band="CBRS_Band48"
    )
    assert radio.network_name == "internet"
    assert radio.network_slice is None  # Only for 5G


def test_radio_parameters_5g():
    """Test 5G radio parameters with network slice"""
    radio = RadioParameters(
        network_name="internet",
        frequency_band="3.5GHz_CBRS",
        network_slice={
            "service_type": 1,
            "slice_id": "000001"
        }
    )
    assert radio.network_slice is not None
    assert radio.network_slice["service_type"] == 1


def test_qos_policy():
    """Test QoS policy definition"""
    policy = QoSPolicy(
        name="high_priority",
        description="Time-sensitive production traffic",
        priority_level=1,
        guaranteed_bandwidth=True,
        uplink_mbps=50,
        downlink_mbps=10
    )
    assert policy.priority_level == 1
    assert policy.guaranteed_bandwidth is True


def test_device_group():
    """Test device group configuration"""
    group = DeviceGroup(
        name="Uplink_Cameras",
        description="Camera feeds",
        qos_policy="high_priority",
        devices=[]
    )
    assert group.name == "Uplink_Cameras"


def test_waveriders_config_4g():
    """Test complete 4G network configuration"""
    config = WaveridersConfig(
        network_type="4G_LTE",
        network_identity=NetworkIdentity(
            country_code="315",
            network_code="010",
            area_code=1,
            network_name="Test Network"
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
        service_quality="standard",
        template_source="waveriders_4g_standard"
    )
    assert config.network_type == "4G_LTE"
    assert config.network_identity.country_code == "315"
```

**Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/daemon/models/test_schema.py -k "radio or qos or group or waveriders_config" -v
```

Expected: FAIL with import errors

**Step 3: Implement remaining models**

Add to `opensurfcontrol/daemon/models/schema.py`:

```python
from typing import Optional, Dict, Any


class NetworkSlice(BaseModel):
    """5G network slice configuration"""

    service_type: int = Field(
        ...,
        description="Slice/Service Type (SST) - 1=eMBB, 2=URLLC, 3=MIoT",
        ge=1,
        le=3
    )
    slice_id: str = Field(
        ...,
        description="Slice Differentiator (SD) - 6 hex digits",
        pattern=r"^[0-9A-Fa-f]{6}$"
    )


class RadioParameters(BaseModel):
    """Radio access network configuration"""

    network_name: str = Field(
        default="internet",
        description="Network name (APN for 4G, DNN for 5G)",
        examples=["internet", "production"]
    )
    frequency_band: str = Field(
        ...,
        description="Operating frequency band",
        examples=["CBRS_Band48", "3.5GHz_CBRS", "custom"]
    )
    network_slice: Optional[NetworkSlice] = Field(
        default=None,
        description="5G network slice configuration (5G only)"
    )


class QoSPolicy(BaseModel):
    """Quality of Service policy definition"""

    name: str = Field(
        ...,
        description="Policy name",
        examples=["high_priority", "standard", "low_latency"]
    )
    description: str = Field(
        ...,
        description="Human-readable description"
    )
    priority_level: int = Field(
        ...,
        description="Priority level (1=highest, 10=lowest)",
        ge=1,
        le=10
    )
    guaranteed_bandwidth: bool = Field(
        default=False,
        description="Whether bandwidth is guaranteed"
    )
    uplink_mbps: int = Field(
        ...,
        description="Uplink bandwidth limit in Mbps",
        ge=1
    )
    downlink_mbps: int = Field(
        ...,
        description="Downlink bandwidth limit in Mbps",
        ge=1
    )


class DeviceConfig(BaseModel):
    """Individual device configuration"""

    imsi: str = Field(
        ...,
        description="International Mobile Subscriber Identity",
        pattern=r"^\d{15}$"
    )
    name: str = Field(
        ...,
        description="Human-readable device name",
        examples=["CAM-01", "TABLET-1"]
    )
    k: str = Field(
        ...,
        description="Authentication key (32 hex chars)",
        pattern=r"^[0-9A-Fa-f]{32}$"
    )
    opc: str = Field(
        ...,
        description="Operator variant key (32 hex chars)",
        pattern=r"^[0-9A-Fa-f]{32}$"
    )
    ip: Optional[str] = Field(
        default=None,
        description="Assigned IP address (populated at runtime)"
    )


class DeviceGroup(BaseModel):
    """Group of devices with common QoS policy"""

    name: str = Field(
        ...,
        description="Group name",
        examples=["Uplink_Cameras", "Crew_Devices"]
    )
    description: str = Field(
        default="",
        description="Group description"
    )
    qos_policy: str = Field(
        ...,
        description="QoS policy name to apply"
    )
    devices: List[DeviceConfig] = Field(
        default_factory=list,
        description="Devices in this group"
    )


class WaveridersConfig(BaseModel):
    """Complete Waveriders network configuration"""

    network_type: Literal["4G_LTE", "5G_Standalone"] = Field(
        ...,
        description="Network generation"
    )
    network_identity: NetworkIdentity
    ip_addressing: IPAddressing
    radio_parameters: RadioParameters
    service_quality: Literal["standard", "high_priority", "low_latency", "custom"] = Field(
        default="standard"
    )
    template_source: str = Field(
        ...,
        description="Configuration template source",
        examples=["waveriders_4g_standard", "waveriders_5g_standard", "custom"]
    )
    qos_policies: Dict[str, QoSPolicy] = Field(
        default_factory=dict,
        description="Available QoS policies"
    )
    device_groups: List[DeviceGroup] = Field(
        default_factory=list,
        description="Device groups"
    )

    @field_validator("radio_parameters")
    @classmethod
    def validate_5g_slice(cls, v: RadioParameters, info) -> RadioParameters:
        """Validate 5G networks have network slice configured"""
        if info.data.get("network_type") == "5G_Standalone":
            if v.network_slice is None:
                raise ValueError("5G networks require network_slice configuration")
        return v
```

**Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/daemon/models/test_schema.py -v
```

Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add daemon/models/schema.py tests/daemon/models/test_schema.py
git commit -m "feat(daemon): complete Waveriders schema models

- Add RadioParameters with 5G network slice support
- Add QoSPolicy for bandwidth/priority configuration
- Add DeviceConfig and DeviceGroup models
- Add WaveridersConfig as top-level schema
- Validate 5G requires network slice configuration"
```

---

### Task 5: CoreAdapter Abstract Interface

**Goal:** Define the abstract base class that all mobile core implementations must follow

**Files:**
- Create: `opensurfcontrol/daemon/core/__init__.py`
- Create: `opensurfcontrol/daemon/core/abstract.py`
- Create: `tests/daemon/core/test_abstract.py`

**Step 1: Write test for abstract interface**

Create `tests/daemon/core/test_abstract.py`:

```python
import pytest
from daemon.core.abstract import CoreAdapter, CoreStatus, RadioSite, Device, Result


def test_core_adapter_cannot_instantiate():
    """Test that CoreAdapter abstract class cannot be instantiated"""
    with pytest.raises(TypeError):
        CoreAdapter()


def test_result_success():
    """Test Result success case"""
    result = Result(success=True, message="Operation successful")
    assert result.success is True
    assert result.message == "Operation successful"


def test_result_failure():
    """Test Result failure case"""
    result = Result(success=False, message="Operation failed", error="Connection timeout")
    assert result.success is False
    assert result.error == "Connection timeout"


def test_core_status():
    """Test CoreStatus model"""
    status = CoreStatus(
        overall="healthy",
        components={
            "control_plane": "healthy",
            "user_plane": "healthy",
            "authentication": "healthy"
        }
    )
    assert status.overall == "healthy"
    assert len(status.components) == 3


def test_radio_site():
    """Test RadioSite model"""
    site = RadioSite(
        name="Camera-Site-1",
        ip_address="10.48.0.100",
        status="connected",
        type="4G_eNodeB"
    )
    assert site.name == "Camera-Site-1"
    assert site.type == "4G_eNodeB"


def test_device():
    """Test Device model"""
    device = Device(
        imsi="315010000000001",
        name="CAM-01",
        ip_address="10.48.99.10",
        status="connected",
        group="Uplink_Cameras",
        uplink_mbps=45.2,
        downlink_mbps=2.1
    )
    assert device.imsi == "315010000000001"
    assert device.uplink_mbps == 45.2
```

**Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/daemon/core/test_abstract.py -v
```

Expected: FAIL with "No module named 'daemon.core'"

**Step 3: Implement CoreAdapter abstract interface**

Create `opensurfcontrol/daemon/core/__init__.py`:

```python
"""Core adapter interfaces for mobile core management"""
```

Create `opensurfcontrol/daemon/core/abstract.py`:

```python
"""Abstract base class for mobile core adapters"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

from daemon.models.schema import WaveridersConfig, DeviceConfig, QoSPolicy


class Result(BaseModel):
    """Operation result"""

    success: bool
    message: str = ""
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class CoreStatus(BaseModel):
    """Core health status"""

    overall: Literal["healthy", "degraded", "down"]
    components: Dict[str, str] = Field(
        default_factory=dict,
        description="Component-level status (e.g., control_plane: healthy)"
    )
    details: Optional[str] = None


class RadioSite(BaseModel):
    """Connected radio site (eNodeB/gNB)"""

    name: str
    ip_address: str
    status: Literal["connected", "disconnected", "error"]
    type: Literal["4G_eNodeB", "5G_gNB"]
    connection_time: Optional[str] = None


class Device(BaseModel):
    """Connected device (UE)"""

    imsi: str
    name: str
    ip_address: str
    status: Literal["connected", "disconnected", "idle"]
    group: Optional[str] = None
    uplink_mbps: float = 0.0
    downlink_mbps: float = 0.0
    connection_time: Optional[str] = None


class CoreAdapter(ABC):
    """Abstract interface for mobile core management

    All mobile core implementations (Open5GS, Attocore, etc.) must
    implement this interface to work with openSurfControl.
    """

    @abstractmethod
    def apply_network_config(self, config: WaveridersConfig) -> Result:
        """Deploy network configuration to mobile core

        Args:
            config: Waveriders unified configuration

        Returns:
            Result with success/failure status
        """
        pass

    @abstractmethod
    def get_core_status(self) -> CoreStatus:
        """Get overall core health status

        Returns:
            CoreStatus with overall and component-level health
        """
        pass

    @abstractmethod
    def get_connected_radios(self) -> List[RadioSite]:
        """Get list of connected radio sites (eNodeB/gNB)

        Returns:
            List of RadioSite objects
        """
        pass

    @abstractmethod
    def get_connected_devices(self) -> List[Device]:
        """Get list of connected devices with throughput stats

        Returns:
            List of Device objects with current throughput
        """
        pass

    @abstractmethod
    def add_device(self, device: DeviceConfig, qos_policy: QoSPolicy) -> Result:
        """Provision new device with QoS policy

        Args:
            device: Device configuration (IMSI, K, OPc, etc.)
            qos_policy: QoS policy to apply

        Returns:
            Result with success/failure status
        """
        pass

    @abstractmethod
    def update_device_qos(self, imsi: str, qos_policy: QoSPolicy) -> Result:
        """Update device QoS policy (e.g., group move)

        Args:
            imsi: Device IMSI
            qos_policy: New QoS policy to apply

        Returns:
            Result with success/failure status
        """
        pass

    @abstractmethod
    def remove_device(self, imsi: str) -> Result:
        """Deprovision device from core

        Args:
            imsi: Device IMSI to remove

        Returns:
            Result with success/failure status
        """
        pass
```

**Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/daemon/core/test_abstract.py -v
```

Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add daemon/core/ tests/daemon/core/
git commit -m "feat(daemon): add CoreAdapter abstract interface

- Define abstract interface for all mobile cores
- Add Result, CoreStatus, RadioSite, Device models
- Require implementations for config, monitoring, device mgmt
- Test that interface cannot be directly instantiated"
```

---

## Phase 2: Open5GS Adapter (Tasks 6-20)

### Task 6: Open5GS Config Generation - MME (4G)

**Goal:** Generate Open5GS MME configuration from Waveriders schema

**Files:**
- Create: `opensurfcontrol/daemon/core/open5gs/__init__.py`
- Create: `opensurfcontrol/daemon/core/open5gs/config_generator.py`
- Create: `tests/daemon/core/open5gs/test_config_generator.py`

**Step 1: Write test for MME config generation**

Create `tests/daemon/core/open5gs/test_config_generator.py`:

```python
import yaml
from daemon.core.open5gs.config_generator import Open5GSConfigGenerator
from daemon.models.schema import (
    WaveridersConfig,
    NetworkIdentity,
    IPAddressing,
    RadioParameters
)


def test_generate_mme_config():
    """Test MME config generation from Waveriders schema"""
    config = WaveridersConfig(
        network_type="4G_LTE",
        network_identity=NetworkIdentity(
            country_code="315",
            network_code="010",
            area_code=1,
            network_name="Test Network"
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

    generator = Open5GSConfigGenerator()
    mme_config = generator.generate_mme_config(config)

    # Parse generated YAML
    parsed = yaml.safe_load(mme_config)

    # Verify PLMN configuration
    assert parsed["mme"]["gummei"]["plmn_id"]["mcc"] == "315"
    assert parsed["mme"]["gummei"]["plmn_id"]["mnc"] == "010"
    assert parsed["mme"]["tai"]["plmn_id"]["mcc"] == "315"
    assert parsed["mme"]["tai"]["plmn_id"]["mnc"] == "010"
    assert parsed["mme"]["tai"]["tac"] == 1

    # Verify S1AP binding
    s1ap = parsed["mme"]["s1ap"][0]
    assert s1ap["addr"] == "10.48.0.5"

    # Verify GTP-C binding
    gtpc = parsed["mme"]["gtpc"][0]
    assert gtpc["addr"] == "10.48.0.5"
```

**Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/daemon/core/open5gs/test_config_generator.py::test_generate_mme_config -v
```

Expected: FAIL with "No module named 'daemon.core.open5gs'"

**Step 3: Implement MME config generator**

Create `opensurfcontrol/daemon/core/open5gs/__init__.py`:

```python
"""Open5GS core adapter implementation"""
```

Create `opensurfcontrol/daemon/core/open5gs/config_generator.py`:

```python
"""Generate Open5GS configuration files from Waveriders schema"""

import yaml
from typing import Dict, Any

from daemon.models.schema import WaveridersConfig


class Open5GSConfigGenerator:
    """Generate Open5GS YAML configuration files"""

    def generate_mme_config(self, config: WaveridersConfig) -> str:
        """Generate MME configuration for 4G EPC

        Args:
            config: Waveriders configuration

        Returns:
            YAML configuration string
        """
        mme_config = {
            "logger": {
                "file": "/var/log/open5gs/mme.log"
            },
            "mme": {
                "freeDiameter": "/etc/freeDiameter/mme.conf",
                "s1ap": [
                    {
                        "addr": config.ip_addressing.core_address,
                        "port": 36412
                    }
                ],
                "gtpc": [
                    {
                        "addr": config.ip_addressing.core_address,
                        "port": 2123
                    }
                ],
                "gummei": {
                    "plmn_id": {
                        "mcc": config.network_identity.country_code,
                        "mnc": config.network_identity.network_code
                    },
                    "mme_gid": 2,
                    "mme_code": 1
                },
                "tai": {
                    "plmn_id": {
                        "mcc": config.network_identity.country_code,
                        "mnc": config.network_identity.network_code
                    },
                    "tac": config.network_identity.area_code
                },
                "security": {
                    "integrity_order": ["EIA2", "EIA1", "EIA0"],
                    "ciphering_order": ["EEA0", "EEA1", "EEA2"]
                },
                "network_name": {
                    "full": config.network_identity.network_name
                }
            }
        }

        return yaml.dump(mme_config, default_flow_style=False, sort_keys=False)

    def generate_smf_config(self, config: WaveridersConfig) -> str:
        """Generate SMF configuration (shared 4G PGW / 5G SMF)

        Args:
            config: Waveriders configuration

        Returns:
            YAML configuration string
        """
        # Extract subnet and gateway from device_pool
        # Format: "10.48.99.0/24"
        subnet = config.ip_addressing.device_pool
        gateway = config.ip_addressing.device_gateway

        smf_config = {
            "logger": {
                "file": "/var/log/open5gs/smf.log"
            },
            "smf": {
                "sbi": [
                    {
                        "addr": "127.0.0.4",
                        "port": 7777
                    }
                ],
                "pfcp": [
                    {
                        "addr": "127.0.0.4",
                        "port": 8805
                    }
                ],
                "gtpc": [
                    {
                        "addr": "127.0.0.4",
                        "port": 2123
                    }
                ],
                "subnet": [
                    {
                        "addr": subnet,
                        "dnn": config.radio_parameters.network_name
                    }
                ],
                "dns": config.ip_addressing.dns_servers,
                "mtu": 1400
            }
        }

        return yaml.dump(smf_config, default_flow_style=False, sort_keys=False)
```

**Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/daemon/core/open5gs/test_config_generator.py::test_generate_mme_config -v
```

Expected: PASS

**Step 5: Add test and implementation for SMF config**

Add to `tests/daemon/core/open5gs/test_config_generator.py`:

```python
def test_generate_smf_config():
    """Test SMF config generation"""
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

    generator = Open5GSConfigGenerator()
    smf_config = generator.generate_smf_config(config)

    parsed = yaml.safe_load(smf_config)

    # Verify subnet configuration
    subnet = parsed["smf"]["subnet"][0]
    assert subnet["addr"] == "10.48.99.0/24"
    assert subnet["dnn"] == "internet"

    # Verify DNS
    assert "8.8.8.8" in parsed["smf"]["dns"]
```

Run test:

```bash
poetry run pytest tests/daemon/core/open5gs/test_config_generator.py::test_generate_smf_config -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add daemon/core/open5gs/ tests/daemon/core/open5gs/
git commit -m "feat(daemon): add Open5GS config generator for MME and SMF

- Generate MME config with PLMN, TAC, S1AP bindings
- Generate SMF config with device pool, DNN, DNS
- Extract network identity from Waveriders schema
- Test YAML generation and parsing"
```

---

### Task 7: Open5GS Config Generation - Remaining Components

**Goal:** Generate configs for SGW-U, UPF, AMF (5G), and other Open5GS components

**Files:**
- Modify: `opensurfcontrol/daemon/core/open5gs/config_generator.py`
- Modify: `tests/daemon/core/open5gs/test_config_generator.py`

**Step 1: Write tests for remaining configs**

Add to `tests/daemon/core/open5gs/test_config_generator.py`:

```python
def test_generate_sgwu_config():
    """Test SGW-U config generation for 4G user plane"""
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

    generator = Open5GSConfigGenerator()
    sgwu_config = generator.generate_sgwu_config(config)

    parsed = yaml.safe_load(sgwu_config)

    # PFCP must be on localhost for SGW-C communication
    assert parsed["sgwu"]["pfcp"][0]["addr"] == "127.0.0.6"

    # GTP-U must be on network interface for eNodeB
    assert parsed["sgwu"]["gtpu"][0]["addr"] == "10.48.0.5"


def test_generate_upf_config():
    """Test UPF config generation"""
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

    generator = Open5GSConfigGenerator()
    upf_config = generator.generate_upf_config(config)

    parsed = yaml.safe_load(upf_config)

    # Verify subnet configuration
    subnet = parsed["upf"]["subnet"][0]
    assert subnet["addr"] == "10.48.99.0/24"
    assert subnet["dnn"] == "internet"

    # Verify gateway (ogstun interface IP)
    assert subnet["gateway"] == "10.48.99.1"


def test_generate_amf_config_5g():
    """Test AMF config generation for 5G SA"""
    from daemon.models.schema import NetworkSlice

    config = WaveridersConfig(
        network_type="5G_Standalone",
        network_identity=NetworkIdentity(
            country_code="999",
            network_code="773",
            area_code=1,
            network_name="Test 5G"
        ),
        ip_addressing=IPAddressing(
            core_address="10.48.0.5",
            device_pool="10.48.99.0/24",
            device_gateway="10.48.99.1"
        ),
        radio_parameters=RadioParameters(
            network_name="internet",
            frequency_band="3.5GHz_CBRS",
            network_slice=NetworkSlice(
                service_type=1,
                slice_id="000001"
            )
        ),
        template_source="test"
    )

    generator = Open5GSConfigGenerator()
    amf_config = generator.generate_amf_config(config)

    parsed = yaml.safe_load(amf_config)

    # Verify PLMN
    assert parsed["amf"]["guami"][0]["plmn_id"]["mcc"] == "999"
    assert parsed["amf"]["guami"][0]["plmn_id"]["mnc"] == "773"

    # Verify TAC
    assert parsed["amf"]["tai"][0]["tac"] == 1

    # Verify S-NSSAI (network slice)
    snssai = parsed["amf"]["plmn_support"][0]["s_nssai"][0]
    assert snssai["sst"] == 1
    assert snssai["sd"] == "000001"

    # Verify NGAP binding
    assert parsed["amf"]["ngap"][0]["addr"] == "10.48.0.5"
    assert parsed["amf"]["ngap"][0]["port"] == 38412
```

**Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/daemon/core/open5gs/test_config_generator.py -k "sgwu or upf or amf" -v
```

Expected: FAIL with method not found errors

**Step 3: Implement remaining config generators**

Add to `opensurfcontrol/daemon/core/open5gs/config_generator.py`:

```python
    def generate_sgwu_config(self, config: WaveridersConfig) -> str:
        """Generate SGW-U configuration for 4G user plane

        Critical: PFCP on localhost, GTP-U on network interface

        Args:
            config: Waveriders configuration

        Returns:
            YAML configuration string
        """
        sgwu_config = {
            "logger": {
                "file": "/var/log/open5gs/sgwu.log"
            },
            "sgwu": {
                "pfcp": [
                    {
                        "addr": "127.0.0.6",  # Localhost for SGW-C communication
                        "port": 8805
                    }
                ],
                "gtpu": [
                    {
                        "addr": config.ip_addressing.core_address,  # Network IP for eNodeB
                        "port": 2152
                    }
                ]
            }
        }

        return yaml.dump(sgwu_config, default_flow_style=False, sort_keys=False)

    def generate_upf_config(self, config: WaveridersConfig) -> str:
        """Generate UPF configuration (shared 4G/5G user plane)

        Args:
            config: Waveriders configuration

        Returns:
            YAML configuration string
        """
        # Determine GTP-U address based on network type
        # For 5G, use separate interface (10.48.0.6) to avoid port conflict with SGW-U
        if config.network_type == "5G_Standalone":
            gtpu_addr = "10.48.0.6"  # Separate interface for 5G
        else:
            gtpu_addr = "127.0.0.7"  # Localhost for 4G (SGW-U handles external GTP-U)

        upf_config = {
            "logger": {
                "file": "/var/log/open5gs/upf.log"
            },
            "upf": {
                "pfcp": [
                    {
                        "addr": "127.0.0.7",
                        "port": 8805
                    }
                ],
                "gtpu": [
                    {
                        "addr": gtpu_addr,
                        "port": 2152
                    }
                ],
                "subnet": [
                    {
                        "addr": config.ip_addressing.device_pool,
                        "gateway": config.ip_addressing.device_gateway,
                        "dnn": config.radio_parameters.network_name
                    }
                ]
            }
        }

        return yaml.dump(upf_config, default_flow_style=False, sort_keys=False)

    def generate_amf_config(self, config: WaveridersConfig) -> str:
        """Generate AMF configuration for 5G SA

        Args:
            config: Waveriders configuration

        Returns:
            YAML configuration string
        """
        if config.network_type != "5G_Standalone":
            raise ValueError("AMF config only for 5G networks")

        if config.radio_parameters.network_slice is None:
            raise ValueError("5G networks require network_slice configuration")

        amf_config = {
            "logger": {
                "file": "/var/log/open5gs/amf.log"
            },
            "amf": {
                "sbi": [
                    {
                        "addr": "127.0.0.5",
                        "port": 7777
                    }
                ],
                "ngap": [
                    {
                        "addr": config.ip_addressing.core_address,
                        "port": 38412
                    }
                ],
                "guami": [
                    {
                        "plmn_id": {
                            "mcc": config.network_identity.country_code,
                            "mnc": config.network_identity.network_code
                        },
                        "amf_id": {
                            "region": 2,
                            "set": 1
                        }
                    }
                ],
                "tai": [
                    {
                        "plmn_id": {
                            "mcc": config.network_identity.country_code,
                            "mnc": config.network_identity.network_code
                        },
                        "tac": config.network_identity.area_code
                    }
                ],
                "plmn_support": [
                    {
                        "plmn_id": {
                            "mcc": config.network_identity.country_code,
                            "mnc": config.network_identity.network_code
                        },
                        "s_nssai": [
                            {
                                "sst": config.radio_parameters.network_slice.service_type,
                                "sd": config.radio_parameters.network_slice.slice_id
                            }
                        ]
                    }
                ],
                "security": {
                    "integrity_order": ["NIA2", "NIA1", "NIA0"],
                    "ciphering_order": ["NEA0", "NEA1", "NEA2"]
                },
                "network_name": {
                    "full": config.network_identity.network_name
                }
            }
        }

        return yaml.dump(amf_config, default_flow_style=False, sort_keys=False)
```

**Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/daemon/core/open5gs/test_config_generator.py -v
```

Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add daemon/core/open5gs/config_generator.py tests/daemon/core/open5gs/test_config_generator.py
git commit -m "feat(daemon): add Open5GS config generation for all components

- Add SGW-U config with localhost PFCP, network GTP-U
- Add UPF config with device pool, gateway, DNN
- Add AMF config for 5G with PLMN, TAC, S-NSSAI
- Handle 4G vs 5G GTP-U interface separation
- Test all config generation paths"
```

---

**[Note: This implementation plan continues with 50+ more tasks covering:]**

- **Tasks 8-10:** Open5GS subscriber management (MongoDB operations)
- **Tasks 11-13:** Open5GS monitoring (log parsing, device detection)
- **Tasks 14-16:** Complete Open5GSAdapter implementation
- **Tasks 17-20:** System integration (config apply, service restarts, validation)
- **Tasks 21-30:** Core Management Daemon (API server, service management)
- **Tasks 31-40:** FastAPI Backend (routes, authentication, daemon client)
- **Tasks 41-50:** React Frontend (pages, components, API integration)
- **Tasks 51-55:** Configuration templates and wizards
- **Tasks 56-60:** End-to-end integration testing
- **Tasks 61-65:** VM packaging and deployment automation

**Each task follows the same TDD pattern:**
1. Write failing test
2. Run test to verify failure
3. Write minimal implementation
4. Run test to verify pass
5. Commit with descriptive message

**Due to response length limits, I've provided the first 7 tasks in detail. The remaining tasks follow identical structure and granularity. Would you like me to continue with specific sections, or shall we proceed to execution?**

---

## Execution Strategy

**Total Effort:** 8-12 weeks for 60+ bite-sized tasks

**Dependencies:**
- Working Open5GS installation for testing
- Ubuntu 22.04 development environment
- Access to test radios (optional for MVP - can mock)

**Risk Mitigation:**
- Early integration testing (Task 56+) catches issues before frontend
- Config validation prevents breaking production Open5GS
- Backup/rollback built into config apply workflow

**Success Criteria:**
- All tests pass
- Deploy 4G network via wizard in < 5 minutes
- Add/remove devices through UI
- Zero 3GPP terminology visible to users
