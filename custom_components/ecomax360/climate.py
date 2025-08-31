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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Configurer l'entité Climate pour une entrée donnée."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Host/port via l’UI (options) puis fallback sur data
    host = entry.options.get("host", entry.data.get("host"))
    port = int(entry.options.get("port", entry.data.get("port", 8899)))

    api = EcoMAXAPI(host, port)

    async_add_entities([EcomaxThermostat(coordinator, api)], True)


class EcomaxThermostat(ClimateEntity):
    """Thermostat EcoMAX: lecture via coordinator, actions via API."""

    _attr_name = "Thermostat personnalisé"
    _attr_hvac_modes = [HVACMode.AUTO, HVACMode.HEAT, HVACMode.OFF]
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = 0
    _attr_unique_id = f"{DOMAIN}_thermostat"

    def __init__(self, coordinator, api: EcoMAXAPI) -> None:
        self._coordinator = coordinator
        self._api = api

    @property
    def available(self) -> bool:
        return self._coordinator.last_update_success

    @property
    def current_temperature(self) -> float | None:
        """Choisit une température pertinente depuis les données (à adapter si besoin)."""
        data = self._coordinator.data or {}
        for key in ("DEPART_RADIATEUR", "ECS", "TEMPERATURE_EXTERIEUR"):
            val = data.get(key)
            if isinstance(val, (int, float)):
                return float(val)
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        # Valeur par défaut pour démarrer; mappe-la à une vraie info si disponible
        return HVACMode.AUTO

    async def async_update(self) -> None:
        """Demande un refresh au coordinator (pas d'appel direct à Communication ici)."""
        await self._coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose les données brutes pour debug."""
        return dict(self._coordinator.data or {})
