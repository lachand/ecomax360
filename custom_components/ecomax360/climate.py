"""Intégration minimaliste d'un thermostat pour Home Assistant avec gestion de modes personnalisés."""

import logging
import voluptuous as vol
import struct

import homeassistant.helpers.config_validation as cv
from homeassistant.components.climate import ClimateEntity, PLATFORM_SCHEMA, HVACAction, PRESET_AWAY,PRESET_COMFORT,PRESET_ECO
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature, ATTR_MODE
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode
)
from .communication import Communication
from .parameters import THERMOSTAT, ECOMAX
from .trame import Trame
from typing import Final

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({})

PRESET_SCHEDULE: Final = "schedule"
PRESET_AIRING: Final = "airing"
PRESET_PARTY: Final = "party"
PRESET_HOLIDAYS: Final = "holidays"
PRESET_ANTIFREEZE: Final = "antifreeze"
PRESET_UNKNOWN: Final = "unknown"

EM_TO_HA_MODE: Final[dict[int, str]] = {
    0: PRESET_SCHEDULE,
    1: PRESET_ECO,
    2: PRESET_COMFORT,
    3: PRESET_AWAY,
    4: PRESET_AIRING,
    5: PRESET_PARTY,
    6: PRESET_HOLIDAYS,
    7: PRESET_ANTIFREEZE,
}
HA_TO_EM_MODE: Final = {v: k for k, v in EM_TO_HA_MODE.items()}

HA_PRESET_TO_EM_TEMP: Final[dict[str, str]] = {
    PRESET_ECO: "night_target_temp",
    PRESET_COMFORT: "day_target_temp",
    PRESET_AWAY: "night_target_temp",
    PRESET_PARTY: "party_target_temp",
    PRESET_HOLIDAYS: "holidays_target_temp",
    PRESET_ANTIFREEZE: "antifreeze_target_temp",
}

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Initialise la plateforme thermostat."""
    add_entities([CustomModeThermostat()])

class CustomModeThermostat(ClimateEntity):
    """Représentation d'un thermostat avec gestion de modes personnalisés."""

    def __init__(self):
        """Initialise le thermostat avec des valeurs par défaut."""
        self._name = "Thermostat personnalisé"
        comm = Communication()
        comm.connect()
        trame = Trame("64 00", "20 00", "40", "c0", "647800","").build()
        thermostat_data = comm.request(trame,THERMOSTAT, "265535445525f78343","c0") or {}
        comm.close()
        _LOGGER.error(thermostat_data)
        self._target_temperature = 20#thermostat_data["ACTUELLE"]
        self._current_temperature = 20#thermostat_data["TEMPERATURE"]
        self._preset_mode = 0#thermostat_data['MODE']
        self.auto = 1#thermostat_data['AUTO']
        self.heating = 0#thermostat_data["HEATING"]
        self._hvac_mode = "auto"  # Mode par défaut
        
    @property
    def hvac_action(self):
        """
        Retourne l'action actuelle du thermostat.
        Ici, on considère que si le mode est chauffage et que la température actuelle
        est inférieure à la consigne, le chauffage est actif.
        """
        if self.heating == 1:
            return HVACAction.HEATING
        else :
            return HVACAction.IDLE
               
    @property
    def name(self):
        """Renvoie le nom du thermostat."""
        return self._name

    @property
    def temperature_unit(self):
        """Renvoie l'unité de température utilisée."""
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self):
        """Renvoie la température actuelle."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Renvoie la température cible."""
        return self._target_temperature

    @property
    def hvac_mode(self):
        """Renvoie le mode de fonctionnement actuel."""
        return self._hvac_mode

    @property
    def hvac_modes(self):
        """Renvoie la liste des modes supportés par le thermostat."""
        return [
            HVACMode.OFF,
            HVACMode.HEAT,
            HVACMode.AUTO
        ]

    @property
    def preset_modes(self):
        """
        Liste des presets personnalisés.
        Ce sont vos anciens 'modes' : jour, nuit, hors gel, aération, party, vacances...
        """
        return list(HA_TO_EM_MODE)

    @property
    def preset_mode(self):
        """Renvoie le preset actuel."""
        return self._preset_mode

    def set_preset_mode(self, preset_mode):
        """
        Définit le preset à appliquer.
        Appelé via le service climate.set_preset_mode.
        """
        if preset_mode not in self.preset_modes:
            _LOGGER.error("Preset %s non supporté", preset_mode)
            return
        self._preset_mode = preset_mode
        self.schedule_update_ha_state()

    @property
    def supported_features(self):
        """Renvoie les fonctionnalités supportées par ce thermostat."""
        return (
        ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TARGET_TEMPERATURE
    )
    
    @property
    def target_temperature_step(self) -> float:
        """Retourne le pas de modification de la température cible."""
        return 0.1  # définit un pas de 0.5 degré

    def set_temperature(self, **kwargs):
        """Définit la nouvelle température cible."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._target_temperature = temperature

        _LOGGER.error(self._preset_mode)
        _LOGGER.error(self.auto)
        
        if self._preset_mode == 1 or self._preset_mode == 0 and self.auto == 1 :
            code = "012001"
        elif self._preset_mode == 2 or self._preset_mode == 0 and self.auto == 0 :
            code = "012101"
        else :
            code = "012001"

        trame = Trame("6400","0100","29","a9",code, struct.pack('<f', temperature).hex()).build()

        comm = Communication()
        comm.connect()
        comm.send(trame,"a9")
        comm.close()
        
        self.schedule_update_ha_state()

    def set_hvac_mode(self, hvac_mode):
        """Change le mode de fonctionnement du thermostat."""
        if hvac_mode not in self.hvac_modes:
            _LOGGER.error("Mode %s non supporté", hvac_mode)
            return
        self._hvac_mode = hvac_mode
        self.schedule_update_ha_state()

    def update(self):
        """Méthode de mise à jour (à personnaliser pour récupérer des données réelles)."""
        comm = Communication()
        comm.connect()
        trame = Trame("64 00", "20 00", "40", "c0", "647800","").build()
        thermostat_data = comm.request(trame,THERMOSTAT, "265535445525f78343","c0") or {}
        comm.close()
        
        if(thermostat_data["ACTUELLE"] >= 5 and thermostat_data["ACTUELLE"] <= 50):
            self._target_temperature = thermostat_data["ACTUELLE"]
        if(thermostat_data["TEMPERATURE"] >= 5 and thermostat_data["TEMPERATURE"] <= 50):
            self._current_temperature = thermostat_data["TEMPERATURE"]
            
        self._preset_mode = EM_TO_HA_MODE[thermostat_data['MODE']]
        
        _LOGGER.error("Mode  EM actuel %s", thermostat_data['MODE'])
        _LOGGER.error("Mode  actuel %s", self._preset_mode)
        self.auto = thermostat_data['AUTO']
        self.heating = thermostat_data["HEATING"]
        _LOGGER.error(thermostat_data)
        pass
