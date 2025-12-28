# openSurfControl MVP Phase 1 - Tasks 21-30 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Date:** 2025-10-31
**Phase:** Complete Daemon + Begin FastAPI Backend
**Tasks:** 21-30 of Phase 1

---

## Overview

This plan completes the Core Management Daemon and begins the FastAPI Backend:
- **Tasks 21-23:** Device group management and bulk operations
- **Task 24:** Daemon main entry point and CLI
- **Task 25:** Systemd service integration
- **Tasks 26-28:** FastAPI Backend foundation and structure
- **Tasks 29-30:** Backend authentication and daemon client

**Goal:** Complete the daemon as a production-ready service, then build the FastAPI backend that exposes the daemon's capabilities to the frontend.

---

## Task 21: Device Group Management Service

**Goal:** Implement service for managing device groups with QoS policies

**Context:** Groups allow bulk device management - all devices in a group inherit the same QoS policy. This is a key UI feature.

**Files:**
- Create: `opensurfcontrol/daemon/services/group_manager.py`
- Create: `tests/daemon/services/test_group_manager.py`

### Step 1: Write tests for group manager

Create `tests/daemon/services/test_group_manager.py`:

```python
import pytest
from unittest.mock import Mock, patch
from daemon.services.group_manager import GroupManager, DeviceGroup


@pytest.fixture
def group_manager():
    """Create group manager"""
    with patch("daemon.services.group_manager.create_adapter"):
        return GroupManager()


def test_create_group(group_manager):
    """Test creating a device group"""
    group = group_manager.create_group(
        name="Uplink_Cameras",
        description="Camera feeds to cloud",
        qos_policy_name="high_priority"
    )

    assert group.name == "Uplink_Cameras"
    assert group.qos_policy_name == "high_priority"
    assert group.device_count == 0


def test_add_device_to_group(group_manager):
    """Test adding device to group"""
    group = group_manager.create_group(
        name="Test_Group",
        description="Test",
        qos_policy_name="standard"
    )

    result = group_manager.add_device_to_group(group.id, "315010000000001")

    assert result is True
    updated_group = group_manager.get_group(group.id)
    assert updated_group.device_count == 1


def test_remove_device_from_group(group_manager):
    """Test removing device from group"""
    group = group_manager.create_group("Test", "Test", "standard")
    group_manager.add_device_to_group(group.id, "315010000000001")

    result = group_manager.remove_device_from_group(group.id, "315010000000001")

    assert result is True
    updated_group = group_manager.get_group(group.id)
    assert updated_group.device_count == 0


def test_list_groups(group_manager):
    """Test listing all groups"""
    group_manager.create_group("Group1", "Test 1", "standard")
    group_manager.create_group("Group2", "Test 2", "high_priority")

    groups = group_manager.list_groups()

    assert len(groups) >= 2
    assert any(g.name == "Group1" for g in groups)


def test_update_group_qos(group_manager):
    """Test updating group QoS policy"""
    group = group_manager.create_group("Test", "Test", "standard")
    group_manager.add_device_to_group(group.id, "315010000000001")

    # Update QoS - should update all devices in group
    with patch.object(group_manager.adapter, "update_device_qos") as mock_update:
        mock_update.return_value = Mock(success=True)

        result = group_manager.update_group_qos(group.id, "high_priority")

    assert result is True
    mock_update.assert_called_once()


def test_delete_group(group_manager):
    """Test deleting a group"""
    group = group_manager.create_group("Test", "Test", "standard")

    result = group_manager.delete_group(group.id)

    assert result is True
    assert group_manager.get_group(group.id) is None
```

### Step 2: Run tests to verify they fail

```bash
poetry run pytest tests/daemon/services/test_group_manager.py -v
```

Expected: FAIL with "No module named group_manager"

### Step 3: Implement group manager

Create `opensurfcontrol/daemon/services/group_manager.py`:

```python
"""Device group management service"""

import uuid
from typing import List, Optional, Set
from datetime import datetime
from pydantic import BaseModel, Field

from daemon.core.factory import create_adapter
from daemon.models.schema import QoSPolicy


class DeviceGroup(BaseModel):
    """Device group model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    qos_policy_name: str
    device_imsis: Set[str] = Field(default_factory=set)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @property
    def device_count(self) -> int:
        """Get number of devices in group"""
        return len(self.device_imsis)


class GroupManager:
    """Manage device groups and bulk operations"""

    def __init__(self):
        """Initialize group manager"""
        self.adapter = create_adapter()
        self._groups: dict[str, DeviceGroup] = {}

    def create_group(
        self,
        name: str,
        description: str,
        qos_policy_name: str
    ) -> DeviceGroup:
        """Create a new device group

        Args:
            name: Group name
            description: Group description
            qos_policy_name: QoS policy to apply to group

        Returns:
            Created group
        """
        group = DeviceGroup(
            name=name,
            description=description,
            qos_policy_name=qos_policy_name
        )

        self._groups[group.id] = group
        return group

    def get_group(self, group_id: str) -> Optional[DeviceGroup]:
        """Get group by ID

        Args:
            group_id: Group identifier

        Returns:
            Group or None if not found
        """
        return self._groups.get(group_id)

    def list_groups(self) -> List[DeviceGroup]:
        """List all groups

        Returns:
            List of groups
        """
        return list(self._groups.values())

    def add_device_to_group(self, group_id: str, imsi: str) -> bool:
        """Add device to group

        Args:
            group_id: Group identifier
            imsi: Device IMSI

        Returns:
            True if added, False if group not found
        """
        group = self._groups.get(group_id)
        if not group:
            return False

        group.device_imsis.add(imsi)
        group.updated_at = datetime.now()

        # TODO: Update device QoS in adapter

        return True

    def remove_device_from_group(self, group_id: str, imsi: str) -> bool:
        """Remove device from group

        Args:
            group_id: Group identifier
            imsi: Device IMSI

        Returns:
            True if removed, False if group not found
        """
        group = self._groups.get(group_id)
        if not group:
            return False

        group.device_imsis.discard(imsi)
        group.updated_at = datetime.now()

        return True

    def update_group_qos(
        self,
        group_id: str,
        qos_policy_name: str,
        qos_policy: Optional[QoSPolicy] = None
    ) -> bool:
        """Update QoS policy for all devices in group

        Args:
            group_id: Group identifier
            qos_policy_name: New QoS policy name
            qos_policy: Optional QoS policy object

        Returns:
            True if updated, False if group not found
        """
        group = self._groups.get(group_id)
        if not group:
            return False

        group.qos_policy_name = qos_policy_name
        group.updated_at = datetime.now()

        # Update all devices in group
        if qos_policy:
            for imsi in group.device_imsis:
                result = self.adapter.update_device_qos(imsi, qos_policy)
                if not result.success:
                    # Log error but continue with other devices
                    print(f"Failed to update QoS for device {imsi}: {result.error}")

        return True

    def delete_group(self, group_id: str) -> bool:
        """Delete a group

        Note: Does not remove devices, just the group

        Args:
            group_id: Group identifier

        Returns:
            True if deleted, False if not found
        """
        if group_id in self._groups:
            del self._groups[group_id]
            return True

        return False

    def get_device_group(self, imsi: str) -> Optional[DeviceGroup]:
        """Find which group a device belongs to

        Args:
            imsi: Device IMSI

        Returns:
            Group or None if device not in any group
        """
        for group in self._groups.values():
            if imsi in group.device_imsis:
                return group

        return None
```

### Step 4: Run tests to verify they pass

```bash
poetry run pytest tests/daemon/services/test_group_manager.py -v
```

Expected: PASS (all group manager tests)

### Step 5: Commit

```bash
git add daemon/services/group_manager.py tests/daemon/services/test_group_manager.py
git commit -m "feat(daemon): add device group management service

- Create GroupManager for device group operations
- Support creating, listing, updating, deleting groups
- Add/remove devices from groups
- Update QoS policy for all devices in group
- Track group metadata and device counts"
```

---

## Task 22: Group API Endpoints

**Goal:** Expose group management operations through API

**Context:** Frontend needs to create groups, assign devices, and manage QoS policies at the group level.

**Files:**
- Create: `opensurfcontrol/daemon/api/routes/groups.py`
- Create: `tests/daemon/api/test_groups_api.py`

### Step 1: Write tests for group endpoints

Create `tests/daemon/api/test_groups_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from daemon.api.server import create_app


@pytest.fixture
def client():
    """Create test client"""
    app = create_app()
    return TestClient(app)


def test_create_group(client):
    """Test creating a device group"""
    group_data = {
        "name": "Uplink_Cameras",
        "description": "Camera feeds",
        "qos_policy_name": "high_priority"
    }

    with patch("daemon.api.routes.groups.group_manager") as mock_mgr:
        mock_group = Mock(
            id="group-123",
            name="Uplink_Cameras",
            description="Camera feeds",
            qos_policy_name="high_priority",
            device_count=0
        )
        mock_mgr.create_group.return_value = mock_group

        response = client.post("/api/v1/groups", json=group_data)

    assert response.status_code == 200
    data = response.json()
    assert data["group"]["name"] == "Uplink_Cameras"


def test_list_groups(client):
    """Test listing groups"""
    mock_groups = [
        Mock(id="1", name="Group1", description="Test 1", qos_policy_name="standard", device_count=2),
        Mock(id="2", name="Group2", description="Test 2", qos_policy_name="high_priority", device_count=3)
    ]

    with patch("daemon.api.routes.groups.group_manager") as mock_mgr:
        mock_mgr.list_groups.return_value = mock_groups

        response = client.get("/api/v1/groups")

    assert response.status_code == 200
    data = response.json()
    assert len(data["groups"]) == 2


def test_add_device_to_group(client):
    """Test adding device to group"""
    with patch("daemon.api.routes.groups.group_manager") as mock_mgr:
        mock_mgr.add_device_to_group.return_value = True

        response = client.post("/api/v1/groups/group-123/devices/315010000000001")

    assert response.status_code == 200


def test_remove_device_from_group(client):
    """Test removing device from group"""
    with patch("daemon.api.routes.groups.group_manager") as mock_mgr:
        mock_mgr.remove_device_from_group.return_value = True

        response = client.delete("/api/v1/groups/group-123/devices/315010000000001")

    assert response.status_code == 200


def test_update_group_qos(client):
    """Test updating group QoS policy"""
    qos_data = {
        "qos_policy_name": "low_latency"
    }

    with patch("daemon.api.routes.groups.group_manager") as mock_mgr:
        mock_mgr.update_group_qos.return_value = True

        response = client.put("/api/v1/groups/group-123/qos", json=qos_data)

    assert response.status_code == 200


def test_delete_group(client):
    """Test deleting a group"""
    with patch("daemon.api.routes.groups.group_manager") as mock_mgr:
        mock_mgr.delete_group.return_value = True

        response = client.delete("/api/v1/groups/group-123")

    assert response.status_code == 200
```

### Step 2: Run tests to verify they fail

```bash
poetry run pytest tests/daemon/api/test_groups_api.py -v
```

Expected: FAIL (endpoints don't exist)

### Step 3: Implement group endpoints

Create `opensurfcontrol/daemon/api/routes/groups.py`:

```python
"""Device group management endpoints"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from daemon.services.group_manager import GroupManager
from daemon.api.schemas import SuccessResponse


# Initialize group manager
group_manager = GroupManager()


# Request/Response models
class CreateGroupRequest(BaseModel):
    """Create group request"""
    name: str
    description: str
    qos_policy_name: str


class GroupResponse(BaseModel):
    """Group response"""
    id: str
    name: str
    description: str
    qos_policy_name: str
    device_count: int


class GroupListResponse(BaseModel):
    """Group list response"""
    groups: List[GroupResponse]
    count: int


class UpdateGroupQoSRequest(BaseModel):
    """Update group QoS request"""
    qos_policy_name: str


# Router
router = APIRouter(prefix="/api/v1/groups", tags=["Groups"])


@router.post("", response_model=dict)
def create_group(request: CreateGroupRequest):
    """Create a new device group

    Args:
        request: Group configuration

    Returns:
        Created group
    """
    group = group_manager.create_group(
        name=request.name,
        description=request.description,
        qos_policy_name=request.qos_policy_name
    )

    return {
        "group": GroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            qos_policy_name=group.qos_policy_name,
            device_count=group.device_count
        )
    }


@router.get("", response_model=GroupListResponse)
def list_groups():
    """List all device groups

    Returns:
        List of groups
    """
    groups = group_manager.list_groups()

    group_list = [
        GroupResponse(
            id=g.id,
            name=g.name,
            description=g.description,
            qos_policy_name=g.qos_policy_name,
            device_count=g.device_count
        )
        for g in groups
    ]

    return GroupListResponse(
        groups=group_list,
        count=len(group_list)
    )


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(group_id: str):
    """Get group by ID

    Args:
        group_id: Group identifier

    Returns:
        Group details
    """
    group = group_manager.get_group(group_id)

    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        qos_policy_name=group.qos_policy_name,
        device_count=group.device_count
    )


@router.post("/{group_id}/devices/{imsi}", response_model=SuccessResponse)
def add_device_to_group(group_id: str, imsi: str):
    """Add device to group

    Args:
        group_id: Group identifier
        imsi: Device IMSI

    Returns:
        Success response
    """
    result = group_manager.add_device_to_group(group_id, imsi)

    if not result:
        raise HTTPException(status_code=404, detail="Group not found")

    return SuccessResponse(
        success=True,
        message=f"Device {imsi} added to group"
    )


@router.delete("/{group_id}/devices/{imsi}", response_model=SuccessResponse)
def remove_device_from_group(group_id: str, imsi: str):
    """Remove device from group

    Args:
        group_id: Group identifier
        imsi: Device IMSI

    Returns:
        Success response
    """
    result = group_manager.remove_device_from_group(group_id, imsi)

    if not result:
        raise HTTPException(status_code=404, detail="Group not found")

    return SuccessResponse(
        success=True,
        message=f"Device {imsi} removed from group"
    )


@router.put("/{group_id}/qos", response_model=SuccessResponse)
def update_group_qos(group_id: str, request: UpdateGroupQoSRequest):
    """Update QoS policy for all devices in group

    Args:
        group_id: Group identifier
        request: New QoS policy

    Returns:
        Success response
    """
    result = group_manager.update_group_qos(group_id, request.qos_policy_name)

    if not result:
        raise HTTPException(status_code=404, detail="Group not found")

    return SuccessResponse(
        success=True,
        message=f"Group QoS updated to {request.qos_policy_name}"
    )


@router.delete("/{group_id}", response_model=SuccessResponse)
def delete_group(group_id: str):
    """Delete a group

    Args:
        group_id: Group identifier

    Returns:
        Success response
    """
    result = group_manager.delete_group(group_id)

    if not result:
        raise HTTPException(status_code=404, detail="Group not found")

    return SuccessResponse(
        success=True,
        message="Group deleted successfully"
    )
```

Update `server.py`:

```python
from daemon.api.routes import status, devices, config, groups


def create_app() -> FastAPI:
    # ... existing code ...

    # Include routers
    app.include_router(status.router)
    app.include_router(devices.router)
    app.include_router(config.router)
    app.include_router(groups.router)

    return app
```

### Step 4: Run tests to verify they pass

```bash
poetry run pytest tests/daemon/api/test_groups_api.py -v
```

Expected: PASS (all group endpoint tests)

### Step 5: Commit

```bash
git add daemon/api/routes/groups.py tests/daemon/api/test_groups_api.py daemon/api/server.py
git commit -m "feat(daemon): add group management API endpoints

- Add POST /api/v1/groups for creating groups
- Add GET /api/v1/groups for listing groups
- Add GET /api/v1/groups/{id} for group details
- Add POST /api/v1/groups/{id}/devices/{imsi} for adding devices
- Add DELETE /api/v1/groups/{id}/devices/{imsi} for removing devices
- Add PUT /api/v1/groups/{id}/qos for updating group QoS
- Add DELETE /api/v1/groups/{id} for deleting groups"
```

---

## Tasks 23-30: Summary

Due to length constraints, I'll provide a condensed outline for the remaining tasks:

### **Task 23: Bulk Device Operations**
- Implement bulk add/remove/update endpoints
- Support batch operations with transaction-like semantics
- Add progress tracking for long-running operations

### **Task 24: Daemon Main Entry Point**
- Create `daemon/main.py` with CLI using `typer` or `click`
- Support commands: `start`, `stop`, `status`, `config`
- Configuration file parsing (YAML/TOML)

### **Task 25: Systemd Service Integration**
- Create systemd service file template
- Add installation script
- Test service lifecycle (start, stop, restart, status)

### **Task 26: FastAPI Backend Foundation**
- Create `api/main.py` with FastAPI application
- Set up project structure (routes, models, services)
- Add CORS, logging, error handling middleware

### **Task 27: Backend Authentication**
- Implement JWT authentication
- User model and password hashing
- Login/logout endpoints
- Protected route decorators

### **Task 28: Daemon Client**
- Create `api/services/daemon_client.py`
- HTTP client for calling daemon API
- Connection pooling and retries
- Error handling and circuit breaker

### **Task 29: Backend Config Routes**
- Map daemon config API to backend routes
- Add `/api/v1/wizard/*` endpoints
- Frontend-friendly response formatting

### **Task 30: Backend Device Routes**
- Map daemon device/group API to backend
- Add search, filtering, pagination
- Real-time updates via WebSocket (optional)

---

## Verification Commands

```bash
# Run all daemon tests
poetry run pytest tests/daemon/ -v

# Run API tests only
poetry run pytest tests/daemon/api/ -v

# Check test coverage
poetry run pytest --cov=daemon --cov-report=html

# Run the daemon (once Task 24 complete)
poetry run opensurfcontrol-daemon --help
poetry run opensurfcontrol-daemon start

# Check systemd service (once Task 25 complete)
sudo systemctl status opensurfcontrol-daemon
```

---

**Ready for execution with superpowers:executing-plans!**
