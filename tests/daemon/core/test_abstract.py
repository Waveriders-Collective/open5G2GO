# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Waveriders Collective Inc.

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
