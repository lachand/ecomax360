import logging
import voluptuous as vol
import struct
import asyncio

import homeassistant.helpers.config_validation as cv
from homeassistant.components.climate import ClimateEntity, PLATFORM_SCHEMA, HVACAction, PRESET_AWAY, PRESET_COMFORT, PRESET_ECO
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode
)
from .api import EcoMAXAPI
from .parameters import THERMOSTAT, ECOMAX
from .trame import Trame

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({})

EM_TO_HA_MODES = {
    0: "SCHEDULE",
    1: PRESET_ECO,
    2: PRESET_COMFORT,
    3: PRESET_AWAY,
    4: "AIRING",
    5: "PARTY",
    6: "HOLIDAYS",
    7: "ANTIFREEZE"
}

PRESET_ICONS = {
    "SCHEDULE": "mdi:calendar-clock",
    PRESET_ECO: "mdi:leaf",
    PRESET_COMFORT: "mdi:home-thermometer",
    PRESET_AWAY: "mdi:airplane",
    "AIRING": "mdi:weather-windy",
    "PARTY": "mdi:glass-cocktail",
    "HOLIDAYS": "mdi:palm-tree",
    "ANTIFREEZE": "mdi:snowflake"
}

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Initialise la plateforme thermostat."""
    add_entities([CustomModeThermostat()])

async def async_setup_entry(hass, config_entry, async_add_entities):
    api = EcoMAXAPI()
    async_add_entities([EcomaxThermostat(api)])
    _LOGGER.error('Configuration climate.py')

class CustomModeThermostat(ClimateEntity):
    """Représentation d'un thermostat avec gestion de modes personnalisés."""

    def __init__(self):
        """Initialise le thermostat avec des valeurs par défaut."""
        self._name = "Thermostat personnalisé"
        self._target_temperature = 20
        self._current_temperature = 20
        self._preset_mode = "SCHEDULE"
        self.auto = 1
        self.heating = 0
        self._hvac_mode = HVACMode.AUTO
        self._attr_unique_id = "Ester_X40_temperature"
        self._attr_supported_features = (
            ClimateEntityFeature.PRESET_MODE | ClimateEntityFeature.TARGET_TEMPERATURE
        )
        self._attr_target_temperature_step = 0.1
        self.api = api

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
    def target_temperature_step(self):
        return self._attr_target_temperature_step

    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def hvac_modes(self):
        return [HVACMode.OFF, HVACMode.HEAT, HVACMode.AUTO]

    @property
    def preset_modes(self):
        return list(EM_TO_HA_MODES.values())

    @property
    def preset_mode(self):
        return self._preset_mode
    
    @property
    def preset_mode_icon(self):
        """Retourne l'icône associée au preset actuel."""
        return PRESET_ICONS.get(self._preset_mode, "mdi:thermometer")

    async def async_set_preset_mode(self, preset_mode):
        if preset_mode not in self.preset_modes:
            _LOGGER.error("Preset %s non supporté", preset_mode)
            return
        self._preset_mode = preset_mode

        mode_code = "011e01"
        code = next((key for key, value in EM_TO_HA_MODES.items() if value == preset_mode), "00")
        trame = Trame("6400", "0100", "29", "a9", mode_code, code).build()

        comm = Communication()
        await api.send_trame(trame, "a9")

        await self.async_update()
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._target_temperature = temperature

        code = "012001" if self._preset_mode in ["SCHEDULE", PRESET_ECO] and self.auto == 1 else "012101"
        trame = Trame("6400", "0100", "29", "a9", code, struct.pack('<f', temperature).hex()).build()

        comm = Communication()
        await api.send_trame(trame, "a9")

        await self.async_update()
        self.async_write_ha_state()

    async def async_update(self):
        comm = Communication()
        trame = Trame("64 00", "20 00", "40", "c0", "647800", "").build()
        thermostat_data = await api.request(trame, THERMOSTAT, "265535445525f78343", "c0") or {}
        
        if 5 < thermostat_data.get("ACTUELLE", 0) < 35:
            self._target_temperature = thermostat_data["ACTUELLE"]
        if 5 < thermostat_data.get("TEMPERATURE", 0) < 35:
            self._current_temperature = thermostat_data["TEMPERATURE"]
        
        self._preset_mode = EM_TO_HA_MODES.get(thermostat_data.get("MODE", 0), "SCHEDULE")
        self.auto = thermostat_data.get("AUTO", 1)
        self.heating = thermostat_data.get("HEATING", 0)
        self.async_write_ha_state()
