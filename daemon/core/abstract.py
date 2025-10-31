"""Abstract base class for mobile core adapters"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from daemon.models.schema import DeviceConfig, QoSPolicy, WaveridersConfig


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
