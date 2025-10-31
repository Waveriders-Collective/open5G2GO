"""MongoDB subscriber management for Open5GS"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from daemon.models.schema import DeviceConfig, QoSPolicy
from daemon.core.abstract import Result


class Open5GSSubscriber(BaseModel):
    """Open5GS subscriber document structure"""

    imsi: str
    k: str
    opc: str
    slice_qos: Dict[str, Any] = Field(default_factory=dict)
    ambr: Dict[str, Any] = Field(default_factory=dict)
    subscribed_rau_tau_timer: int = 12
    network_access_mode: int = 0
    subscriber_status: int = 0
    access_restriction_data: int = 32
    security: Dict[str, Any] = Field(
        default_factory=lambda: {
            "k": "",
            "amf": "8000",
            "op": None,
            "opc": ""
        }
    )
    schema_version: int = 1

    @classmethod
    def from_device_config(
        cls,
        device: DeviceConfig,
        qos_policy: QoSPolicy,
        plmn: str
    ) -> "Open5GSSubscriber":
        """Convert DeviceConfig to Open5GS subscriber format

        Args:
            device: Device configuration
            qos_policy: QoS policy to apply
            plmn: PLMN identifier (MCC+MNC)

        Returns:
            Open5GSSubscriber instance
        """
        # Map QoS priority to Open5GS QoS Index
        # Priority 1 (highest) -> QCI 1 (conversational voice)
        # Priority 5 (standard) -> QCI 5 (video streaming)
        # Priority 9 (lowest) -> QCI 9 (background data)
        qos_index = qos_policy.priority_level

        # Convert Mbps to Kbps for Open5GS
        uplink_kbps = qos_policy.uplink_mbps * 1000
        downlink_kbps = qos_policy.downlink_mbps * 1000

        return cls(
            imsi=device.imsi,
            k=device.k,
            opc=device.opc,
            slice_qos={
                "qos_index": qos_index,
                "session": [
                    {
                        "name": "internet",
                        "type": 3,  # IPv4
                        "qos": {
                            "index": qos_index,
                            "arp": {
                                "priority_level": qos_policy.priority_level,
                                "pre_emption_capability": 1,
                                "pre_emption_vulnerability": 1
                            }
                        },
                        "ambr": {
                            "uplink": {"value": uplink_kbps, "unit": 1},  # Kbps
                            "downlink": {"value": downlink_kbps, "unit": 1}
                        }
                    }
                ]
            },
            ambr={
                "uplink": {"value": uplink_kbps, "unit": 1},
                "downlink": {"value": downlink_kbps, "unit": 1}
            },
            security={
                "k": device.k,
                "amf": "8000",
                "op": None,
                "opc": device.opc
            }
        )


class SubscriberManager:
    """Manage Open5GS subscribers in MongoDB"""

    def __init__(self, mongodb_uri: str, database_name: str = "open5gs"):
        """Initialize subscriber manager

        Args:
            mongodb_uri: MongoDB connection URI
            database_name: Database name (default: open5gs)
        """
        self.mongodb_uri = mongodb_uri
        self.database_name = database_name
        self._client: Optional[MongoClient] = None

    @property
    def client(self) -> MongoClient:
        """Get MongoDB client (lazy initialization)"""
        if self._client is None:
            self._client = MongoClient(self.mongodb_uri)
        return self._client

    @property
    def db(self):
        """Get database handle"""
        return self.client[self.database_name]

    @property
    def subscribers(self):
        """Get subscribers collection"""
        return self.db.subscribers

    def add_subscriber(
        self,
        device: DeviceConfig,
        qos_policy: QoSPolicy,
        plmn: str
    ) -> Result:
        """Add subscriber to MongoDB

        Args:
            device: Device configuration
            qos_policy: QoS policy to apply
            plmn: PLMN identifier (MCC+MNC)

        Returns:
            Result with success/failure status
        """
        try:
            # Convert to Open5GS format
            subscriber = Open5GSSubscriber.from_device_config(
                device=device,
                qos_policy=qos_policy,
                plmn=plmn
            )

            # Insert into MongoDB
            result = self.subscribers.insert_one(subscriber.model_dump())

            return Result(
                success=True,
                message=f"Subscriber {device.imsi} added successfully",
                data={"subscriber_id": str(result.inserted_id)}
            )

        except PyMongoError as e:
            return Result(
                success=False,
                message="Failed to add subscriber",
                error=str(e)
            )

    def close(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            self._client = None
