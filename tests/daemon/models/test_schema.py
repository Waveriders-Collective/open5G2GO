# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Waveriders Collective Inc.

import pytest
from pydantic import ValidationError
from daemon.models.schema import (
    NetworkIdentity,
    IPAddressing,
    RadioParameters,
    QoSPolicy,
    DeviceConfig,
    DeviceGroup,
    WaveridersConfig
)


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
    assert radio.network_slice.service_type == 1


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
