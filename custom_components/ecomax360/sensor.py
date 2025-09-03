"""Sensor platform for the EcoMAX360 integration.

This module defines a generic sensor entity that represents a single
measurement reported by the EcoMAX controller.  The sensor values are
retrieved from the central data coordinator, which polls the device
periodically.  Each sensor exposes a name, state, unit of measurement and
icon appropriate to the underlying parameter.  All sensors are created
dynamically based on the definitions in :data:`ECOMAX`.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import STATE_UNKNOWN, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .api.parameters import ECOMAX

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up EcoMAX360 sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    # Ensure we have initial data
    await coordinator.async_config_entry_first_refresh()
    sensors: list[EcomaxSensor] = []
    for key in ECOMAX.keys():
        name = f"EcoMAX {key}".replace("_", " ")
        sensors.append(EcomaxSensor(coordinator, key, name))
    if not sensors:
        _LOGGER.warning("No sensors created for EcoMAX360")
        return
    async_add_entities(sensors, True)


class EcomaxSensor(CoordinatorEntity, SensorEntity):
    """Representation of a single EcoMAX sensor entity."""

    # Mapping of keys to display units.  The default unit is Celsius for
    # temperature readings; additional mappings can be added here.
    UNIT_MAPPING: dict[str, str] = {
        "TEMPERATURE": UnitOfTemperature.CELSIUS,
        "ACTUELLE": UnitOfTemperature.CELSIUS,
        "DEPART_RADIATEUR": UnitOfTemperature.CELSIUS,
        "ECS": UnitOfTemperature.CELSIUS,
        "BALLON_TAMPON": UnitOfTemperature.CELSIUS,
        "TEMPERATURE_EXTERIEUR": UnitOfTemperature.CELSIUS,
    }

    # Icon mapping for specific sensors.  Icons are taken from Material
    # Design Icons (mdi) to visually differentiate the different readings.
    ICONS: dict[str, str] = {
        "TEMPERATURE": "mdi:thermometer",
        "JOUR": "mdi:weather-sunny",
        "NUIT": "mdi:weather-night",
        "ACTUELLE": "mdi:thermometer-check",
        "SOURCE_PRINCIPALE": "mdi:fire",
        "DEPART_RADIATEUR": "mdi:radiator",
        "ECS": "mdi:water-pump",
        "BALLON_TAMPON": "mdi:water",
        "TEMPERATURE_EXTERIEUR": "mdi:weather-partly-cloudy",
    }

    def __init__(self, coordinator, key: str, name: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        # Unique ID combines the entry id and parameter key
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{key}"
        # Unit of measurement and device class based on mapping
        unit = self.UNIT_MAPPING.get(key.upper())
        if unit is not None:
            self._attr_native_unit_of_measurement = unit
            # Temperature measurements can set a device class
            if unit == UnitOfTemperature.CELSIUS:
                self._attr_device_class = "temperature"
                self._attr_state_class = "measurement"
        # Default icon fallback
        self._icon = self.ICONS.get(key.upper(), "mdi:help-circle")

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        data = self.coordinator.data or {}
        value = data.get(self._key)
        if value is None:
            return STATE_UNKNOWN
        # Attempt to convert to a float with two decimals; if conversion
        # fails return the value directly (may already be a number)
        try:
            return round(float(value), 2)
        except (ValueError, TypeError):
            return value

    @property
    def icon(self) -> str:
        """Return the icon for the sensor."""
        return self._icon