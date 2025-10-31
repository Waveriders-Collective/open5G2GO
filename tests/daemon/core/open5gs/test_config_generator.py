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
