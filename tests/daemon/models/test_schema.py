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
