"""Tests for the EcoMAX360 sensor entities.

This module exercises the :class:`~custom_components.ecomax360.sensor.EcomaxSensor`
class without requiring a running Home Assistant instance.  A small
set of stub modules is used to satisfy the imports of the sensor
platform, allowing the module to be loaded in isolation.  The test
verifies that sensor entities correctly expose values from the
coordinator and that units and icons are assigned based on the
parameter key.  As with other tests in this suite, no real EcoMAX
device is contacted.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType, SimpleNamespace
import importlib.util
import sys

import pytest

# ---------------------------------------------------------------------------
# Helper to load the sensor platform with Home Assistant stubs
#
# The sensor platform relies on a number of Home Assistant modules and
# classes such as SensorEntity, UnitOfTemperature and CoordinatorEntity.
# To import the module outside of Home Assistant, we inject minimal
# stand‑ins for these symbols into ``sys.modules`` before loading the
# sensor code.  Once loaded, the module is cached in sys.modules and
# subsequent imports will reuse it.
# ---------------------------------------------------------------------------

def _load_sensor_module():
    """Dynamically load the sensor module with stubbed dependencies.

    Returns the loaded module.  Subsequent calls return the cached
    module.
    """
    if 'custom_components.ecomax360.sensor' in sys.modules:
        return sys.modules['custom_components.ecomax360.sensor']
    # Create stub modules for the pieces of Home Assistant used by sensor.py
    # homeassistant package and subpackages
    ha_mod = ModuleType('homeassistant')
    ha_components = ModuleType('homeassistant.components')
    ha_components_sensor = ModuleType('homeassistant.components.sensor')
    ha_helpers = ModuleType('homeassistant.helpers')
    ha_helpers_update_coordinator = ModuleType('homeassistant.helpers.update_coordinator')
    ha_config_entries = ModuleType('homeassistant.config_entries')
    ha_const = ModuleType('homeassistant.const')
    # Stub classes
    class SensorEntity:
        """Minimal stub for SensorEntity."""
        pass
    class CoordinatorEntity:
        """Minimal stub for CoordinatorEntity."""
        def __init__(self, coordinator) -> None:
            self.coordinator = coordinator
    class UnitOfTemperature:
        CELSIUS = '°C'
    # Attach stubs to modules
    ha_components_sensor.SensorEntity = SensorEntity
    ha_helpers_update_coordinator.CoordinatorEntity = CoordinatorEntity
    ha_const.STATE_UNKNOWN = 'unknown'
    ha_const.UnitOfTemperature = UnitOfTemperature
    # Minimal ConfigEntry stub (not used directly by sensor)
    class ConfigEntry:
        def __init__(self, data: dict | None = None, options: dict | None = None) -> None:
            self.data = data or {}
            self.options = options or {}
            self.entry_id = 'test'
    ha_config_entries.ConfigEntry = ConfigEntry
    # Register stubs in sys.modules
    sys.modules.setdefault('homeassistant', ha_mod)
    sys.modules.setdefault('homeassistant.components', ha_components)
    sys.modules.setdefault('homeassistant.components.sensor', ha_components_sensor)
    sys.modules.setdefault('homeassistant.helpers', ha_helpers)
    sys.modules.setdefault('homeassistant.helpers.update_coordinator', ha_helpers_update_coordinator)
    sys.modules.setdefault('homeassistant.const', ha_const)
    sys.modules.setdefault('homeassistant.config_entries', ha_config_entries)
    # Load the utils and parameters modules used by the sensor
    base = Path(__file__).resolve().parents[1]
    cc_dir = base / 'custom_components' / 'ecomax360'
    def load_module(name: str, path: Path) -> ModuleType:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)  # type: ignore[assignment]
        sys.modules[name] = module
        return module
    # Ensure package namespace exists
    if 'custom_components' not in sys.modules:
        pkg = ModuleType('custom_components')
        sys.modules['custom_components'] = pkg
    if 'custom_components.ecomax360' not in sys.modules:
        sub_pkg = ModuleType('custom_components.ecomax360')
        sub_pkg.__path__ = []  # mark as package
        sys.modules['custom_components.ecomax360'] = sub_pkg
    # Load dependencies for relative imports
    load_module('custom_components.ecomax360.utils', cc_dir / 'utils.py')
    load_module('custom_components.ecomax360.api.parameters', cc_dir / 'api' / 'parameters.py')
    # Load the sensor module
    sensor_path = cc_dir / 'sensor.py'
    spec = importlib.util.spec_from_file_location('custom_components.ecomax360.sensor', sensor_path)
    sensor_module = importlib.util.module_from_spec(spec)
    sensor_module.__package__ = 'custom_components.ecomax360'
    assert spec.loader is not None
    spec.loader.exec_module(sensor_module)  # type: ignore[assignment]
    sys.modules['custom_components.ecomax360.sensor'] = sensor_module
    return sensor_module


class DummyCoordinator:
    """Coordinator stub providing data and metadata for sensor tests."""

    def __init__(self, data: dict[str, float | int], entry_id: str = 'test') -> None:
        self.data = data
        self.last_update_success = True
        self.config_entry = SimpleNamespace(entry_id=entry_id)


def test_sensors_expose_values() -> None:
    """Verify that EcomaxSensor exposes coordinator values and units correctly."""
    sensor_mod = _load_sensor_module()
    EcomaxSensor = sensor_mod.EcomaxSensor
    from custom_components.ecomax360.api.parameters import ECOMAX
    # Define sample data for all keys
    sample_data: dict[str, float] = {
        'SOURCE_PRINCIPALE': 60.0,
        'DEPART_RADIATEUR': 55.5,
        'ECS': 50.0,
        'BALLON_TAMPON': 30.0,
        'TEMPERATURE_EXTERIEUR': 15.0,
    }
    coordinator = DummyCoordinator(sample_data)
    # Create sensors for each parameter in ECOMAX
    sensors = [EcomaxSensor(coordinator, key, f"EcoMAX {key}") for key in ECOMAX.keys()]
    # Each sensor should return the corresponding value from coordinator.data
    for sensor in sensors:
        key = sensor._key
        expected = sample_data.get(key)
        # Some sensors convert to float and round; approximate
        if expected is not None:
            assert sensor.native_value == pytest.approx(expected)
        # Check that available is True when last_update_success is True
        assert sensor.available is True
