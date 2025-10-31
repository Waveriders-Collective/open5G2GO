import yaml
from daemon.core.open5gs.config_generator import Open5GSConfigGenerator
from daemon.models.schema import (
    WaveridersConfig,
    NetworkIdentity,
    IPAddressing,
    RadioParameters,
    NetworkSlice
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
