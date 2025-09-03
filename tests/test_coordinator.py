"""Tests for the EcoMAX360 data coordinator.

These tests verify that the :class:`~custom_components.ecomax360.coordinator.EcoMaxDataUpdateCoordinator`
properly invokes the underlying client to fetch new data and returns
the decoded values.  A dummy client is used to supply precomputed
frames, allowing the test to run without network access.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from custom_components.ecomax360.coordinator import EcoMaxDataUpdateCoordinator


class DummyClient:
    """Stub of EcoMaxClient returning predetermined data."""

    def __init__(self, data: dict[str, float | int]) -> None:
        self.data = data
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.listen_calls = 0

    async def async_connect(self) -> None:
        self.connect_calls += 1

    async def async_disconnect(self) -> None:
        self.disconnect_calls += 1

    async def listen_frame(self, param: str) -> dict[str, float | int] | None:
        assert param == 'GET_DATAS'
        self.listen_calls += 1
        return self.data


@pytest.mark.asyncio
async def test_coordinator_returns_data() -> None:
    """Ensure that the coordinator fetches data via the client and returns it."""
    dummy_data = {
        'DEPART_RADIATEUR': 55.0,
        'ECS': 50.0,
        'BALLON_TAMPON': 30.0,
    }
    client = DummyClient(dummy_data)
    # A bare SimpleNamespace suffices for the hass argument since
    # EcoMaxDataUpdateCoordinator does not reference hass in _async_update_data.
    hass = SimpleNamespace()
    coordinator = EcoMaxDataUpdateCoordinator(hass, client, scan_interval=10)
    result = await coordinator._async_update_data()
    # The coordinator should return the same data dictionary
    assert result == dummy_data
    # Verify client methods were called
    assert client.connect_calls == 1
    assert client.disconnect_calls == 1
    assert client.listen_calls == 1
