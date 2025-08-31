from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Configurer les capteurs pour une entrée donnée."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Première récupération des données
    await coordinator.async_config_entry_first_refresh()

    # Crée un capteur par clé présente dans coordinator.data
    data = coordinator.data or {}
    sensors: list[EcomaxSensor] = []
    for key in data.keys():
        sensors.append(EcomaxSensor(coordinator, key, f"EcoMax {key}"))

    if not sensors:
        _LOGGER.warning("Aucune donnée initiale, création d’un capteur 'EcoMax Data'")
        sensors.append(EcomaxSensor(coordinator, "DEPART_RADIATEUR", "EcoMax Data"))

    async_add_entities(sensors, True)


class EcomaxSensor(CoordinatorEntity, SensorEntity):
    """Capteur individuel lié au coordinator."""

    def __init__(self, coordinator, key: str, name: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_sensor_{key}"

        # Unités simples pour quelques clés courantes
        if any(k in key.upper() for k in ("TEMP", "RADIATEUR", "ECS", "BALLON", "EXTER")):
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data or {}
        return data.get(self._key)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success
