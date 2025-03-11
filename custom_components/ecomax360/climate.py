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
from .communication import Communication
from .parameters import THERMOSTAT, ECOMAX
from .trame import Trame
from .api import EcoMAXAPI

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

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Initialise la plateforme thermostat."""
    add_entities([EcomaxThermostat()])

async def async_setup_entry(hass, config_entry, async_add_entities):
    api = EcoMAXAPI()
    async_add_entities([EcomaxThermostat(api)])
    _LOGGER.error('Configuration climate.py')

class EcomaxThermostat(ClimateEntity):
    """Représentation d'un thermostat avec gestion de modes personnalisés."""

    def __init__(self, api):
        """Initialise le thermostat avec des valeurs par défaut."""
        self._name = "Thermostat personnalisé"
        self._target_temperature = 20
        self._current_temperature = 20
        self._preset_mode = 0
        self.auto = 1
        self.heating = 0
        self._hvac_mode = "auto"
        self._attr_unique_id = "Ester_X40_temperature"

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
        return ["SCHEDULE", PRESET_ECO, PRESET_COMFORT, PRESET_AWAY, "AIRING", "PARTY", "HOLIDAYS", "ANTIFREEZE"]

    @property
    def preset_mode(self):
        return self._preset_mode

    async def set_preset_mode(self, preset_mode):
        if preset_mode not in self.preset_modes:
            _LOGGER.error("Preset %s non supporté", preset_mode)
            return
        self._preset_mode = preset_mode

        mode_code = "011e01"
        code = {"SCHEDULE": "03", PRESET_COMFORT: "01", PRESET_ECO: "02", "ANTIFREEZE": "07"}.get(self._preset_mode, "00")
        trame = Trame("6400", "0100", "29", "a9", mode_code, code).build()

        comm = Communication()
        await comm.connect()
        await comm.send(trame, "a9")
        await comm.close()

        await self.async_update_ha_state()
        await self.async_update()

    async def set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._target_temperature = temperature

        code = "012001" if self._preset_mode in [0, 1] and self.auto == 1 else "012101"
        trame = Trame("6400", "0100", "29", "a9", code, struct.pack('<f', temperature).hex()).build()

        comm = Communication()
        await comm.connect()
        await comm.send(trame, "a9")
        await comm.close()

        await self.async_update_ha_state()
        await self.async_update()

    async def async_update(self):
        comm = Communication()
        await comm.connect()
        trame = Trame("64 00", "20 00", "40", "c0", "647800", "").build()
        thermostat_data = await comm.request(trame, THERMOSTAT, "265535445525f78343", "c0") or {}
        await comm.close()
        
        if 5 < thermostat_data.get("ACTUELLE", 0) < 35:
            self._target_temperature = thermostat_data["ACTUELLE"]
        if 5 < thermostat_data.get("TEMPERATURE", 0) < 35:
            self._current_temperature = thermostat_data["TEMPERATURE"]
        
        self._preset_mode = EM_TO_HA_MODES.get(thermostat_data.get("MODE", 0), "SCHEDULE")
        self.auto = thermostat_data.get("AUTO", 1)
        self.heating = thermostat_data.get("HEATING", 0)
        await self.async_update_ha_state()
