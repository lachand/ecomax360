from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .api import EcoMAXAPI

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> bool:
    """Configurer la plateforme climate pour une entrée donnée."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    host = entry.options.get("host", entry.data.get("host"))
    port = int(entry.options.get("port", entry.data.get("port", 8899)))
    api = EcoMAXAPI(host, port)

    thermostat = EcomaxThermostat(coordinator, api)
    async_add_entities([thermostat], True)

    return True   # <- indispensable !


class EcomaxThermostat(ClimateEntity):
    """Thermostat EcoMAX (lecture via coordinator)."""

    _attr_name = "EcoMAX Thermostat"
    _attr_unique_id = f"{DOMAIN}_thermostat"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.AUTO, HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = 0

    def __init__(self, coordinator, api: EcoMAXAPI) -> None:
        self._coordinator = coordinator
        self._api = api

    @property
    def available(self) -> bool:
        return self._coordinator.last_update_success

    @property
    def current_temperature(self) -> float | None:
        data = self._coordinator.data or {}
        for key in ("DEPART_RADIATEUR", "ECS", "TEMPERATURE_EXTERIEUR"):
            val = data.get(key)
            if isinstance(val, (int, float)):
                return float(val)
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        return HVACMode.AUTO

    async def async_update(self) -> None:
        await self._coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return dict(self._coordinator.data or {})
