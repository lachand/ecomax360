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

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Initialise la plateforme thermostat."""
    add_entities([EcomaxThermostat()])

async def async_setup_entry(hass, config_entry, async_add_entities):
    host = entry.options.get("host", entry.data.get("host"))
    port = int(entry.options.get("port", entry.data.get("port", 8899)))

    api = EcoMAXAPI(host, port)
    async_add_entities([EcomaxThermostat(api)])
    _LOGGER.error('Configuration climate.py')

class EcomaxThermostat(ClimateEntity):
    """Représentation d'un thermostat avec gestion de modes personnalisés."""

    def __init__(self, api):
        """Initialise le thermostat avec des valeurs par défaut."""
        self._name = "Thermostat personnalisé"
        self._target_temperature = 20
        self._current_temperature = 20
        self._preset_mode = "Calendrier"
        self.auto = 0
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

    async def async_set_preset_mode(self, preset_mode):
        if preset_mode not in self.preset_modes:
            _LOGGER.error("Preset %s non supporté", preset_mode)
            return
        self._preset_mode = preset_mode

        mode_code = "011e01"
        _LOGGER.error("Preset %s", preset_mode)
        #code = next((key for key, value in EM_TO_HA_MODES.items() if value == preset_mode), "00")
        code = HA_TO_EM_MODES[preset_mode]
        _LOGGER.error("Preset %s", code)
        trame = Trame("6400", "0100", "29", "a9", mode_code, code).build()

        comm = Communication()
        await comm.connect()
        await comm.send(trame, "a9")
        await comm.close()

        await self.async_update()
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._target_temperature = temperature
        _LOGGER.info("preset: %s", self._preset_mode)
        _LOGGER.info("auto : %s", self.auto)
        code = "012001" if (self._preset_mode in ["Calendrier"] and self.auto == 1) or (self._preset_mode in [PRESET_COMFORT]) else "012101"
        trame = Trame("6400", "0100", "29", "a9", code, struct.pack('<f', temperature).hex()).build()

        comm = Communication()
        await comm.connect()
        await comm.send(trame, "a9")
        await comm.close()

        await self.async_update()
        self.async_write_ha_state()
        
    async def async_update(self):
        """Met à jour les informations du thermostat."""
        comm = Communication()
        await comm.connect()
        trame = Trame("64 00", "20 00", "40", "c0", "647800", "").build()
        thermostat_data = await comm.request(trame, THERMOSTAT, "265535445525f78343", "c0") or {"MODE": 0, "TEMPERATURE": self._current_temperature, "ACTUELLE": self._target_temperature, "AUTO": self.auto, "HEATING": self.heating}
        await comm.close()

        _LOGGER.info("Données du thermostat reçues: %s", thermostat_data)

        self._current_temperature = thermostat_data.get("TEMPERATURE", self._current_temperature)
        self._target_temperature = thermostat_data.get("ACTUELLE", self._target_temperature)

        mode = thermostat_data.get("MODE", 0)
        self._preset_mode = EM_TO_HA_MODES.get(mode, "Calendrier")

        self.auto = thermostat_data.get("AUTO", 1)
        self.heating = thermostat_data.get("HEATING", 0)

        await self.async_update_ha_state()
