import pytest
from unittest.mock import Mock, MagicMock, patch
from daemon.core.open5gs.subscriber_manager import SubscriberManager, Open5GSSubscriber
from daemon.models.schema import DeviceConfig, QoSPolicy


def test_open5gs_subscriber_from_device_config():
    """Test converting DeviceConfig to Open5GS subscriber format"""
    device = DeviceConfig(
        imsi="315010000000001",
        name="CAM-01",
        k="465B5CE8B199B49FAA5F0A2EE238A6BC",
        opc="E8ED289DEBA952E4283B54E88E6183CA"
    )

    qos = QoSPolicy(
        name="high_priority",
        description="High priority",
        priority_level=1,
        guaranteed_bandwidth=True,
        uplink_mbps=50,
        downlink_mbps=10
    )

    subscriber = Open5GSSubscriber.from_device_config(
        device=device,
        qos_policy=qos,
        plmn="315010"
    )

    assert subscriber.imsi == "315010000000001"
    assert subscriber.k == "465B5CE8B199B49FAA5F0A2EE238A6BC"
    assert subscriber.opc == "E8ED289DEBA952E4283B54E88E6183CA"
    assert subscriber.slice_qos["qos_index"] == 1  # Maps to priority_level


def test_subscriber_manager_init():
    """Test SubscriberManager initialization"""
    manager = SubscriberManager(
        mongodb_uri="mongodb://localhost:27017",
        database_name="open5gs"
    )
    assert manager.database_name == "open5gs"


@patch('daemon.core.open5gs.subscriber_manager.MongoClient')
def test_subscriber_manager_add_subscriber(mock_mongo_client):
    """Test adding a subscriber to MongoDB"""
    # Mock MongoDB
    mock_collection = Mock()
    mock_db = Mock()
    mock_db.subscribers = mock_collection
    mock_client = MagicMock()
    mock_client.__getitem__.return_value = mock_db
    mock_mongo_client.return_value = mock_client

    manager = SubscriberManager(
        mongodb_uri="mongodb://localhost:27017",
        database_name="open5gs"
    )

    device = DeviceConfig(
        imsi="315010000000001",
        name="CAM-01",
        k="465B5CE8B199B49FAA5F0A2EE238A6BC",
        opc="E8ED289DEBA952E4283B54E88E6183CA"
    )

    qos = QoSPolicy(
        name="high_priority",
        description="High priority",
        priority_level=1,
        guaranteed_bandwidth=True,
        uplink_mbps=50,
        downlink_mbps=10
    )

    result = manager.add_subscriber(device, qos, plmn="315010")

    assert result.success is True
    mock_collection.insert_one.assert_called_once()
