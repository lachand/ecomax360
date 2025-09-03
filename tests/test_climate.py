"""Tests for the EcoMAX360 climate entity.

These tests verify that the :class:`EcomaxThermostat` class builds
correct frames when changing the preset mode or target temperature and
that it updates its internal state when new thermostat data is
received.  Because the integration relies on Home Assistant classes
(`ClimateEntity`, `CoordinatorEntity`, etc.), the tests provide
minimal stub implementations of the required Home Assistant modules
and classes at runtime.  This allows the climate module to be loaded
without pulling in the full Home Assistant dependency tree.

The tests reuse the dynamic module loading approach from
``test_trame.py`` to import the ``Trame`` class for frame
verification.  A dummy client is used to capture frames sent by the
entity without opening a real TCP connection.
"""

from __future__ import annotations

import asyncio
import struct
from pathlib import Path
from types import ModuleType
import importlib.util
import sys
import types

import pytest


def _load_trame_module():
    """Reuse the helper from test_trame to load the Trame class.

    The :mod:`custom_components.ecomax360.trame` module uses relative
    imports (``from .utils``) so we need to register ``utils`` and
    ``api.parameters`` in ``sys.modules`` before loading it.
    """
    # Only load once to avoid polluting sys.modules repeatedly
    if 'custom_components.ecomax360.trame' in sys.modules:
        return sys.modules['custom_components.ecomax360.trame']
    # Locate the integration directory
    base = Path(__file__).resolve().parents[1]
    cc_dir = base / 'custom_components' / 'ecomax360'
    api_dir = cc_dir / 'api'
    # Helper to load a module from file and register it
    def load_module(name: str, path: Path) -> ModuleType:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)  # type: ignore[assignment]
        sys.modules[name] = module
        return module
    # Ensure package hierarchy exists
    if 'custom_components' not in sys.modules:
        pkg = ModuleType('custom_components')
        sys.modules['custom_components'] = pkg
    if 'custom_components.ecomax360' not in sys.modules:
        sub_pkg = ModuleType('custom_components.ecomax360')
        sub_pkg.__path__ = []  # mark as package
        sys.modules['custom_components.ecomax360'] = sub_pkg
    # Load utils and api.parameters into sys.modules so relative imports work
    load_module('custom_components.ecomax360.utils', cc_dir / 'utils.py')
    load_module('custom_components.ecomax360.api.parameters', api_dir / 'parameters.py')
    # Load trame
    trame_path = cc_dir / 'trame.py'
    spec_trame = importlib.util.spec_from_file_location(
        'custom_components.ecomax360.trame', trame_path
    )
    trame_module = importlib.util.module_from_spec(spec_trame)
    trame_module.__package__ = 'custom_components.ecomax360'
    assert spec_trame.loader is not None
    spec_trame.loader.exec_module(trame_module)  # type: ignore[assignment]
    sys.modules['custom_components.ecomax360.trame'] = trame_module
    return trame_module


def _load_climate_module() -> ModuleType:
    """Dynamically load the climate module with Home Assistant stubs.

    The climate platform depends on several Home Assistant modules.  To
    import it in isolation, we create minimal stub modules and insert
    them into ``sys.modules`` before loading the climate code.  These
    stubs provide just enough structure for the import to succeed and
    for the entity class to operate in our tests.  Once loaded, the
    module is cached in ``sys.modules``.
    """
    if 'custom_components.ecomax360.climate' in sys.modules:
        return sys.modules['custom_components.ecomax360.climate']
    # Create stub modules for homeassistant dependencies
    # homeassistant package
    ha_mod = ModuleType('homeassistant')
    ha_components = ModuleType('homeassistant.components')
    ha_components_climate = ModuleType('homeassistant.components.climate')
    ha_helpers = ModuleType('homeassistant.helpers')
    ha_helpers_update_coordinator = ModuleType('homeassistant.helpers.update_coordinator')
    ha_const = ModuleType('homeassistant.const')
    ha_config_entries = ModuleType('homeassistant.config_entries')
    # Stub classes and enums used in climate.py
    class ClimateEntity:
        async def async_write_ha_state(self) -> None:
            pass

    class CoordinatorEntity:
        def __init__(self, coordinator) -> None:
            self.coordinator = coordinator
        async def async_write_ha_state(self) -> None:
            pass

    class ClimateEntityFeature:
        PRESET_MODE = 1
        TARGET_TEMPERATURE = 2

    class HVACMode:
        OFF = 'off'
        HEAT = 'heat'
        AUTO = 'auto'

    class HVACAction:
        HEATING = 'heating'
        IDLE = 'idle'

    class UnitOfTemperature:
        CELSIUS = '°C'

    # Attach stubs to modules
    ha_components_climate.ClimateEntity = ClimateEntity
    ha_components_climate.ClimateEntityFeature = ClimateEntityFeature
    ha_components_climate.HVACMode = HVACMode
    ha_components_climate.HVACAction = HVACAction
    ha_const.ATTR_TEMPERATURE = 'temperature'
    ha_const.UnitOfTemperature = UnitOfTemperature
    ha_helpers_update_coordinator.CoordinatorEntity = CoordinatorEntity
    # Minimal ConfigEntry and HomeAssistant stubs (not used directly)
    class ConfigEntry:
        def __init__(self, data: dict | None = None, options: dict | None = None) -> None:
            self.data = data or {}
            self.options = options or {}
            self.entry_id = 'test'
    ha_config_entries.ConfigEntry = ConfigEntry
    # Register stubs in sys.modules
    sys.modules.setdefault('homeassistant', ha_mod)
    sys.modules.setdefault('homeassistant.components', ha_components)
    sys.modules.setdefault('homeassistant.components.climate', ha_components_climate)
    sys.modules.setdefault('homeassistant.helpers', ha_helpers)
    sys.modules.setdefault('homeassistant.helpers.update_coordinator', ha_helpers_update_coordinator)
    sys.modules.setdefault('homeassistant.const', ha_const)
    sys.modules.setdefault('homeassistant.config_entries', ha_config_entries)
    # Load the climate module
    base = Path(__file__).resolve().parents[1]
    climate_path = base / 'custom_components' / 'ecomax360' / 'climate.py'
    spec = importlib.util.spec_from_file_location(
        'custom_components.ecomax360.climate', climate_path
    )
    climate_module = importlib.util.module_from_spec(spec)
    climate_module.__package__ = 'custom_components.ecomax360'
    assert spec.loader is not None
    spec.loader.exec_module(climate_module)  # type: ignore[assignment]
    sys.modules['custom_components.ecomax360.climate'] = climate_module
    return climate_module


class DummyCoordinator:
    """Simple coordinator stub used in tests.

    The real ``CoordinatorEntity`` expects a coordinator with a
    ``data`` attribute, a ``last_update_success`` flag and a
    ``config_entry`` with an ``entry_id``.  This stub provides those
    attributes without any behaviour.  Entities created with this
    coordinator will see ``last_update_success`` as ``True`` and
    ``config_entry.entry_id`` equal to ``test``.
    """

    def __init__(self, data: dict | None = None, entry_id: str = 'test') -> None:
        self.data: dict = data or {}
        self.last_update_success = True
        self.config_entry = types.SimpleNamespace(entry_id=entry_id)


class DummyClient:
    """Client stub capturing frames instead of sending them over TCP."""

    def __init__(self, response: dict | None = None) -> None:
        # Store any sent frames as tuples (frame, ack_flag)
        self.sent_frames: list[tuple[bytes, str]] = []
        # Optional response to return from async_request
        self._response = response

    async def async_connect(self) -> None:
        return None

    async def async_disconnect(self) -> None:
        return None

    async def async_send(self, frame: bytes, ack_flag: str) -> None:
        # Append the frame and ack flag for later inspection
        self.sent_frames.append((frame, ack_flag))

    async def async_request(
        self,
        frame: bytes,
        datastruct: dict,
        data_to_search: str,
        ack_flag: str,
    ) -> dict | None:
        # Ignore inputs and return the preset response
        return self._response

    # New high‑level methods introduced in api.client
    async def async_change_preset(self, preset_hex: str) -> None:
        """Simulate sending a preset change frame via async_send.

        The dummy client builds the frame using the Trame class loaded
        dynamically and records it via async_send.  No network I/O is
        performed.
        """
        # Dynamically import the Trame class to build the frame
        trame_module = _load_trame_module()
        Trame = trame_module.Trame  # type: ignore[attr-defined]
        frame = Trame('6400', '0100', '29', 'a9', '011e01', preset_hex).build()
        await self.async_send(frame, 'a9')

    async def async_set_setpoint(self, code: str, temperature: float) -> None:
        """Simulate sending a setpoint frame via async_send.

        The dummy client encodes the floating point temperature and
        constructs a frame identical to the real client.  The frame is
        recorded via async_send for later inspection.
        """
        # Dynamically import the Trame class
        trame_module = _load_trame_module()
        Trame = trame_module.Trame  # type: ignore[attr-defined]
        value_hex = struct.pack('<f', float(temperature)).hex()
        frame = Trame('6400', '0100', '29', 'a9', code, value_hex).build()
        await self.async_send(frame, 'a9')

    async def async_get_thermostat(self) -> dict | None:
        """Return the stored response for thermostat data."""
        return self._response


@pytest.mark.asyncio
async def test_set_preset_mode_sends_correct_frame() -> None:
    """Verify that async_set_preset_mode builds the expected frame and updates state."""
    climate_mod = _load_climate_module()
    trame_mod = _load_trame_module()
    Trame = trame_mod.Trame
    # Prepare dummy client and coordinator
    client = DummyClient()
    coordinator = DummyCoordinator()
    thermostat = climate_mod.EcomaxThermostat(coordinator, client, 'test')
    # Set eco preset
    await thermostat.async_set_preset_mode('eco')
    # Only one frame should have been sent
    assert len(client.sent_frames) == 1
    frame, ack = client.sent_frames[0]
    # The expected frame uses function code 29, ack flag a9, mode payload 011e01 and preset code 01
    expected_frame = Trame('6400', '0100', '29', 'a9', '011e01', '01').build()
    assert frame == expected_frame
    assert ack == 'a9'
    # Preset mode should now be updated on the entity
    assert thermostat.preset_mode == 'eco'


@pytest.mark.asyncio
async def test_set_temperature_sends_correct_frame() -> None:
    """Verify that async_set_temperature encodes the temperature correctly."""
    climate_mod = _load_climate_module()
    trame_mod = _load_trame_module()
    Trame = trame_mod.Trame
    # Dummy client to capture frame
    client = DummyClient()
    coordinator = DummyCoordinator()
    thermostat = climate_mod.EcomaxThermostat(coordinator, client, 'test')
    # Use conditions to select code 012001: preset Calendrier and auto=1
    thermostat._preset_mode = 'Calendrier'
    thermostat.auto = 1
    temp_val = 20.0
    await thermostat.async_set_temperature(**{climate_mod.ATTR_TEMPERATURE: temp_val})
    assert len(client.sent_frames) == 1
    sent_frame, ack = client.sent_frames[0]
    # Compute expected frame
    value_hex = struct.pack('<f', float(temp_val)).hex()
    expected_frame = Trame('6400', '0100', '29', 'a9', '012001', value_hex).build()
    assert sent_frame == expected_frame
    assert ack == 'a9'
    # Entity should update its internal target temperature
    assert thermostat.target_temperature == pytest.approx(temp_val)


@pytest.mark.asyncio
async def test_async_update_applies_new_state() -> None:
    """Verify that async_update reads thermostat data and updates attributes."""
    climate_mod = _load_climate_module()
    # Data returned by the dummy client for the thermostat
    response = {
        'TEMPERATURE': 21.5,
        'ACTUELLE': 23.0,
        'MODE': 2,  # maps to 'comfort'
        'AUTO': 0,
        'HEATING': 1,
    }
    client = DummyClient(response=response)
    coordinator = DummyCoordinator()
    thermostat = climate_mod.EcomaxThermostat(coordinator, client, 'test')
    await thermostat.async_update()
    # Check that attributes have been updated
    assert thermostat.current_temperature == pytest.approx(21.5)
    assert thermostat.target_temperature == pytest.approx(23.0)
    # mode code 2 corresponds to 'comfort'
    assert thermostat.preset_mode == 'comfort'
    assert thermostat.auto == 0
    assert thermostat.heating == 1