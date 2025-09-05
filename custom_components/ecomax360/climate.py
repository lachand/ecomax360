import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate.const import (
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_ECO,
    ATTR_TEMPERATURE,
)
from homeassistant.const import UnitOfTemperature

from .api import EcoMAXAPI
from .mappings import EM_TO_HA_MODES, HA_TO_EM_MODES, em_to_ha

_LOGGER = logging.getLogger(__name__)


class EcomaxThermostat(ClimateEntity):
    """Entité thermostat EcoMAX."""

    _attr_has_entity_name = True
    _attr_name = "Thermostat Personnalisé"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_preset_modes = list(HA_TO_EM_MODES.keys())

    def __init__(self, coordinator, host: str, port: int) -> None:
        self._coordinator = coordinator
        self._host = host
        self._port = port
        self._api = EcoMAXAPI(host, port)

        self._attr_unique_id = f"thermostat_{host}_{port}"
        self._current_temperature = 20.0
        self._target_temperature = 21.0
        self._preset_mode = "Calendrier"
        self.auto = 1
        self.heating = 0

    @property
    def hvac_mode(self):
        return HVACMode.HEAT

    @property
    def hvac_action(self):
        return "heating" if self.heating else "idle"

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def preset_mode(self):
        return self._preset_mode

    async def async_set_preset_mode(self, preset_mode):
        if preset_mode not in self.preset_modes:
            _LOGGER.error("Preset %s non supporté", preset_mode)
            return
        self._preset_mode = preset_mode
        await self._api.async_change_preset(HA_TO_EM_MODES[preset_mode])
        await self.async_update()
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._target_temperature = temperature
        code = (
            "012001"
            if (self._preset_mode in ["Calendrier"] and self.auto == 1)
            or (self._preset_mode in [PRESET_COMFORT])
            else "012101"
        )
        await self._api.async_set_setpoint(code, temperature)
        await self.async_update()
        self.async_write_ha_state()

    async def async_update(self):
        data = await self._api.async_get_thermostat()
        if not data:
            return
        self._current_temperature = data.get("TEMPERATURE", self._current_temperature)
        self._target_temperature = data.get("ACTUELLE", self._target_temperature)
        self._preset_mode = em_to_ha(data.get("MODE", 0))
        self.auto = data.get("AUTO", 1)
        self.heating = data.get("HEATING", 0)
        await self.async_update_ha_state()
