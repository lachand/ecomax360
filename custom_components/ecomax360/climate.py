"""Climate platform for EcoMAX360 controllers.

This module implements a thermostat entity that exposes the heating
functions of the EcoMAX controller.  The thermostat supports changing
the preset mode (e.g. Eco, Comfort, Away) and adjusting the target
temperature.  It retrieves its current state by sending a request frame
to the controller and decoding the response according to the
:data:`THERMOSTAT` data structure.

Only a single thermostat entity is created per config entry.  It
interacts with the :class:`EcoMaxClient` directly for sending commands
and uses the data coordinator solely for exposing the general broadcast
data; thermostatic state is fetched on demand to avoid interfering with
the regular polling cycle.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .api.client import EcoMaxClient

_LOGGER = logging.getLogger(__name__)


# Mapping from EcoMAX numeric mode codes to Home Assistant preset names
EM_TO_HA_MODES: Dict[int, str] = {
    0: "Calendrier",
    1: "eco",
    2: "comfort",
    3: "away",
    4: "Aeration",
    5: "Fete",
    6: "Vacances",
    7: "HorsGel",
}

# Reverse mapping from Home Assistant preset names to EcoMAX codes.  The
# keys here should match those returned by :attr:`preset_modes` on the
# thermostat entity.  Unknown presets are ignored.
HA_TO_EM_MODES: Dict[str, str] = {
    "Calendrier": "00",
    "eco": "01",
    "comfort": "02",
    "away": "03",
    "Aeration": "04",
    "Fete": "05",
    "Vacances": "06",
    "HorsGel": "07",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up the EcoMAX360 thermostat from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    client: EcoMaxClient = data["client"]
    thermostat = EcomaxThermostat(coordinator, client, entry.entry_id)
    async_add_entities([thermostat], True)


class EcomaxThermostat(CoordinatorEntity, ClimateEntity):
    """A climate entity wrapping an EcoMAX thermostat."""

    _attr_name = "Thermostat personnalisé"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.PRESET_MODE | ClimateEntityFeature.TARGET_TEMPERATURE
    # Expose the list of available HVAC modes
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.AUTO]

    def __init__(self, coordinator, client: EcoMaxClient, entry_id: str) -> None:
        super().__init__(coordinator)
        self._client = client
        self._entry_id = entry_id
        # Internal state values
        self._current_temperature: Optional[float] = None
        self._target_temperature: Optional[float] = None
        self._preset_mode: str = "Calendrier"
        # Auto and heating flags as reported by the controller
        self.auto: int = 1
        self.heating: int = 0
        self._hvac_mode = HVACMode.AUTO
        self._attr_unique_id = f"{entry_id}_thermostat"

    # ------------------------------------------------------------------
    # Home Assistant properties
    # ------------------------------------------------------------------
    @property
    def hvac_action(self) -> HVACAction:
        """Return the current operation (heating/idle)."""
        return HVACAction.HEATING if self.heating == 1 else HVACAction.IDLE

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        return self._hvac_mode

    @property
    def preset_modes(self) -> List[str]:
        """Return a list of available preset modes."""
        return list(HA_TO_EM_MODES.keys())

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the currently active preset mode."""
        return self._preset_mode

    @property
    def current_temperature(self) -> Optional[float]:
        """Return the current temperature as reported by the controller."""
        return self._current_temperature

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the setpoint temperature."""
        return self._target_temperature

    @property
    def min_temp(self) -> float:
        """Return the minimum supported target temperature."""
        return 5.0

    @property
    def max_temp(self) -> float:
        """Return the maximum supported target temperature."""
        return 35.0

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Change the preset mode of the thermostat.

        The mapping of preset names to EcoMAX codes is defined in
        :data:`HA_TO_EM_MODES`.  This method delegates the frame
        construction and transmission to :class:`EcoMaxClient`, which
        handles opening and closing the TCP connection.  After the
        command is sent, the entity refreshes its state.
        """
        if preset_mode not in HA_TO_EM_MODES:
            _LOGGER.error("Preset mode %s is not supported", preset_mode)
            return
        preset_hex = HA_TO_EM_MODES[preset_mode]
        # Delegate to the client for sending the appropriate frame
        await self._client.async_change_preset(preset_hex)
        # Update local state and refresh values
        self._preset_mode = preset_mode
        await self.async_update()
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a new target temperature on the controller."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        # Determine the code to use based on current auto and preset flags.
        # Use 012001 if preset is Calendrier and auto==1, or if preset is comfort;
        # otherwise use 012101.
        if (self._preset_mode == "Calendrier" and self.auto == 1) or (
            self._preset_mode == "comfort"
        ):
            code = "012001"
        else:
            code = "012101"
        # Send via the high‑level client method
        await self._client.async_set_setpoint(code, float(temperature))
        self._target_temperature = float(temperature)
        await self.async_update()
        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Updating state
    # ------------------------------------------------------------------
    async def async_update(self) -> None:
        """Fetch the latest thermostat state from the controller."""
        # Delegate the request to the client.  It will handle opening and
        # closing the connection.
        result = await self._client.async_get_thermostat()
        if not result:
            _LOGGER.debug("No thermostat data received from controller")
            return
        # Update local attributes
        self._current_temperature = result.get("TEMPERATURE", self._current_temperature)
        self._target_temperature = result.get("ACTUELLE", self._target_temperature)
        mode_code = result.get("MODE", 0)
        # Map numeric mode to preset name if possible
        self._preset_mode = EM_TO_HA_MODES.get(mode_code, self._preset_mode)
        self.auto = result.get("AUTO", self.auto)
        self.heating = result.get("HEATING", self.heating)
        # Always keep hvac_mode in AUTO for now; EcoMAX thermostat does
        # not expose distinct off/heat modes directly via this protocol.
        self._hvac_mode = HVACMode.AUTO