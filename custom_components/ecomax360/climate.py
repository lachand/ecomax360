import logging
import struct
from typing import Any
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    ClimateEntityFeature,
    PRESET_ECO,
    PRESET_COMFORT,
    PRESET_AWAY,
)
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .api import EcoMAXAPI
from .mappings import EM_TO_HA_MODES, HA_TO_EM_MODES, em_to_ha

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Configurer la plateforme climate à partir d'un config entry."""
    # Récupère host/port depuis options (prioritaires) sinon data
    host: Optional[str] = entry.options.get("host") or entry.data.get("host")
    port: Optional[int] = entry.options.get("port") or entry.data.get("port")

    if not host or not port:
        _LOGGER.error(
            "Configuration incomplète (host/port). Vérifiez l'entrée %s", entry.entry_id
        )
        return

    # Essaie de récupérer le coordinator si l'init l'a stocké
    coordinator: Any = None
    domain_data = hass.data.get(DOMAIN, {})
    entry_blob = domain_data.get(entry.entry_id)
    if isinstance(entry_blob, dict) and "coordinator" in entry_blob:
        coordinator = entry_blob["coordinator"]
    elif entry_blob is not None:
        coordinator = entry_blob

    entity = EcomaxThermostat(coordinator, host, int(port))
    #async_add_entities([entity], True)
    async_add_entities([entity], False)


class EcomaxThermostat(ClimateEntity):
    """Entité thermostat EcoMAX."""

    _attr_has_entity_name = True
    _attr_name = "Thermostat Personnalisé"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_preset_modes = ["Calendrier", PRESET_COMFORT, PRESET_ECO, PRESET_AWAY]

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
        # HA accepte une string libre si HVACAction n'est pas importé
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
        # Logique historique : calendrier+auto ou confort => 012001, sinon 012101
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
        #await self.async_update_ha_state()

