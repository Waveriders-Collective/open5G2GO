import pytest
from pydantic import ValidationError
from daemon.models.schema import NetworkIdentity, IPAddressing


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
