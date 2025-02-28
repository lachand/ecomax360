import logging
import struct
from homeassistant.components.climate import ClimateEntity, HVACAction, PRESET_AWAY, PRESET_COMFORT, PRESET_ECO
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.components.climate.const import ClimateEntityFeature, HVACMode
from .api import EcoMAXAPI
from .parameters import THERMOSTAT

_LOGGER = logging.getLogger(__name__)

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

async def async_setup_entry(hass, config_entry, async_add_entities):
    api = EcoMAXAPI()
    async_add_entities([EcomaxThermostat(api)])
    _LOGGER.error('Configuration climate.py')

class EcomaxThermostat(ClimateEntity):
    def __init__(self, api):
        self.api = api
        self._name = "Thermostat ecoMAX360"
        self._target_temperature = 20
        self._current_temperature = 20
        self._preset_mode = "SCHEDULE"
        self._hvac_mode = HVACMode.AUTO
        self.auto = 1
        self.heating = 0
        self._attr_unique_id = "ecomax360_thermostat"
        self.update()
        _LOGGER.error('Configuration climate.py terminee')

    @property
    def hvac_action(self):
        return HVACAction.HEATING if self.heating == 1 else HVACAction.IDLE

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def target_temperature(self):
        return self._target_temperature

    def set_preset_mode(self, preset_mode):
        if preset_mode not in EM_TO_HA_MODES.values():
            _LOGGER.error("Preset %s non supporté", preset_mode)
            return
        self._preset_mode = preset_mode
        trame = "6400 0100 29 a9 011e01 " + {"SCHEDULE": "03", PRESET_COMFORT: "01", PRESET_ECO: "02", "ANTIFREEZE": "07"}.get(preset_mode, "00")
        self.api.send_trame(trame)
        self.update()

    def update(self):
        trame = "64 00 20 00 40 c0 647800"
        _LOGGER.error(trame)
        data = self.api.request(trame, THERMOSTAT, "265535445525f78343", "c0") or {}
        _LOGGER.error(data)
         data:
            self._target_temperature = data.get("ACTUELLE", 20)
            self._current_temperature = data.get("TEMPERATURE", 20)
            self._preset_mode = EM_TO_HA_MODES.get(data.get("MODE", 0), "SCHEDULE")
            self.auto = data.get("AUTO", 1)
            self.heating = data.get("HEATING", 0)
