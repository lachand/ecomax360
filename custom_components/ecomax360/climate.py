"""Intégration minimaliste d'un thermostat pour Home Assistant avec gestion de modes personnalisés."""

import logging
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.climate import ClimateEntity, PLATFORM_SCHEMA
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.components.climate.const import ClimateEntityFeature
from .communication import Communication
from .parameters import THERMOSTAT, ECOMAX
from .trame import Trame

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({})

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Initialise la plateforme thermostat."""
    add_entities([CustomModeThermostat()])

class CustomModeThermostat(ClimateEntity):
    """Représentation d'un thermostat avec gestion de modes personnalisés."""

    def __init__(self):
        """Initialise le thermostat avec des valeurs par défaut."""
        self._name = "Thermostat personnalisé"
        self._current_temperature = 20.0
        self._target_temperature = 22.0
        self._hvac_mode = "auto"  # Mode par défaut

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
        return ["Auto Jour","Nuit","Jour","Exterieur","Aération","Fête","Vacances","Hors-gel"]

    @property
    def supported_features(self):
        """Renvoie les fonctionnalités supportées par ce thermostat."""
        return ClimateEntityFeature.TARGET_TEMPERATURE

    def set_temperature(self, **kwargs):
        """Définit la nouvelle température cible."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._target_temperature = temperature
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
        self._target_temperature = thermostat_data["ACTUELLE"]
        self._current_temperature = thermostat_data["TEMPERATURE"]
        pass
