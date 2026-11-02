"""SIM keys must not leave the API."""

import asyncio
from unittest.mock import MagicMock

from web_backend.services.open5gs_service import Open5GSService

# Public 3GPP Milenage test set 1; not real subscriber credentials.
TEST_K = "465b5ce8b199b49faa5f0a2ee238a6bc"
TEST_OPC = "cd63cb71954a9f4e48a5994e37a02baf"


def test_subscriber_detail_omits_sim_keys():
    mongo = MagicMock()
    mongo.get_subscriber.return_value = {
        "imsi": "315010000000011",
        "security": {"k": TEST_K, "opc": TEST_OPC, "op": None, "amf": "8000", "sqn": 97},
        "slice": [],
    }
    result = asyncio.run(Open5GSService(client=mongo).get_subscriber("315010000000011"))

    assert result["success"] is True
    assert result["data"]["security"] == {"amf": "8000", "sqn": 97}
    assert TEST_K not in repr(result)
    assert TEST_OPC not in repr(result)
    # The stored document itself is left untouched
    assert mongo.get_subscriber.return_value["security"]["k"] == TEST_K
