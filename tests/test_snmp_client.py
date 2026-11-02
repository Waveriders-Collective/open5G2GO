"""Exercise the installed PySNMP API so upgrades cannot silently disable monitoring."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from pysnmp.hlapi.v3arch import asyncio as snmp

from opensurfcontrol.snmp_client import BaicellsSNMPClient, OIDS


def test_installed_pysnmp_is_available():
    assert BaicellsSNMPClient().is_available()


@pytest.mark.parametrize("outcome", ["success", "agent_error", "timeout", "exception"])
async def test_query_uses_async_transport_and_closes_engine(monkeypatch, outcome):
    query = AsyncMock()
    query.return_value = (None, 0, 0, [(OIDS["ue_connections"], 3)])
    if outcome == "agent_error":
        query.return_value = ("No SNMP response received before timeout", 0, 0, [])
    elif outcome == "timeout":
        query.side_effect = asyncio.TimeoutError()
    elif outcome == "exception":
        query.side_effect = RuntimeError("synthetic query failure")
    monkeypatch.setattr(snmp, "get_cmd", query)

    closed = []
    close_dispatcher = snmp.SnmpEngine.close_dispatcher

    def record_close(engine):
        closed.append(engine)
        close_dispatcher(engine)

    monkeypatch.setattr(snmp.SnmpEngine, "close_dispatcher", record_close)
    client = BaicellsSNMPClient(community="test-community", timeout=0.2, retries=0)
    result = await client.get_status("127.0.0.1")

    query.assert_awaited_once()
    engine, credentials, transport, context, *oids = query.call_args.args
    assert isinstance(engine, snmp.SnmpEngine)
    assert credentials.communityName == "test-community"
    assert isinstance(transport, snmp.UdpTransportTarget)
    assert transport.transport_address == ("127.0.0.1", 161)
    assert transport.timeout == 0.2
    assert transport.retries == 0
    assert isinstance(context, snmp.ContextData)
    assert len(oids) == len(OIDS)
    assert closed == [engine]
    assert result.reachable is (outcome == "success")
    if outcome == "success":
        assert result.ue_count == 3
        assert result.error is None
    else:
        assert result.error
