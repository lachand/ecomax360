from __future__ import annotations

import logging
from typing import Any

from .const import DOMAIN
from .api import EcoMAXAPI
import struct
import asyncio

from homeassistant.components.climate import ClimateEntity, PLATFORM_SCHEMA, HVACAction, PRESET_AWAY, PRESET_COMFORT, PRESET_ECO
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
import homeassistant.helpers.config_validation as cv
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({})

EM_TO_HA_MODES = {
    0: "Calendrier",
    1: PRESET_ECO,
    2: PRESET_COMFORT,
    3: PRESET_AWAY,
    4: "Aération",
    5: "Fête",
    6: "Vacances",
    7: "Hors-gel"
}

HA_TO_EM_MODES = {
    "Calendrier" : "00",
    PRESET_ECO : "01",
    PRESET_COMFORT : "02",
    PRESET_AWAY : "03",
    "Aération" : "04",
    "Fête" : "05",
    "Vacances" : "06",
    "Hors-gel" : "07",
}

PRESET_ICONS = {
    "Calendrier": "mdi:calendar",
    PRESET_ECO: "mdi:leaf",
    PRESET_COMFORT: "mdi:sofa",
    PRESET_AWAY: "mdi:airplane",
    "Aération": "mdi:weather-windy",
    "Fête": "mdi:glass-cocktail",
    "Vacances": "mdi:palm-tree",
    "Hors-gel": "mdi:snowflake"
}

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

    _attr_name = "Thermostat chaudière"
    _attr_unique_id = f"{DOMAIN}_thermostat"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = 0
    self._preset_mode = "Calendrier"
    self.auto = 0
    self.heating = 0
    self._hvac_mode = "auto"

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
    def hvac_action(self):
        return HVACAction.HEATING if self.heating == 1 else HVACAction.IDLE
    
    @property
    def name(self):
        return self._name

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def hvac_modes(self):
        return [HVACMode.OFF, HVACMode.HEAT, HVACMode.AUTO]

    @property
    def preset_modes(self):
        return list(PRESET_ICONS.keys())

    @property
    def preset_mode(self):
        return ["Calendrier",PRESET_ECO,PRESET_COMFORT,PRESET_AWAY,"Aération","Fête","Vacances","Hors-gel"]

    @property
    def extra_state_attributes(self):
        """Ajoute un attribut pour stocker l'icône associée au preset_mode."""
        return {"preset_icon": PRESET_ICONS.get(self._preset_mode, "mdi:thermometer")}

    @property
    def target_temperature_step(self) -> float:
        """Retourne le pas de modification de la température cible."""
        return 0.1  # définit un pas de 0.1 degré

    @property
    def supported_features(self):
        """Retourne les fonctionnalités supportées par le thermostat."""
        return (ClimateEntityFeature.PRESET_MODE | ClimateEntityFeature.TARGET_TEMPERATURE)
