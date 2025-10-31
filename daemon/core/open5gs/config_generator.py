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
