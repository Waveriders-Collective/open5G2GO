"""Generate Open5GS configuration files from Waveriders schema"""

import yaml
from typing import Any, Dict

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
        mme_config: Dict[str, Any] = {
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

        smf_config: Dict[str, Any] = {
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

    def generate_sgwu_config(self, config: WaveridersConfig) -> str:
        """Generate SGW-U configuration for 4G user plane

        Critical: PFCP on localhost, GTP-U on network interface

        Args:
            config: Waveriders configuration

        Returns:
            YAML configuration string
        """
        sgwu_config: Dict[str, Any] = {
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

        upf_config: Dict[str, Any] = {
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

        amf_config: Dict[str, Any] = {
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
