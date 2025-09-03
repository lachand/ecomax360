from __future__ import annotations

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
from .parameters import THERMOSTAT  # structure de parsing côté thermostat
from .trame import Trame
from .communication import Communication  # async, prend (host, port)

_LOGGER = logging.getLogger(__name__)


# Mappages modes EcoMAX <-> Home Assistant.
# Adapte si besoin pour coller exactement à tes valeurs.
EM_TO_HA_MODES = {
    0: "Calendrier",   # Auto Jour (ton libellé d’origine)
    1: PRESET_ECO,     # Nuit
    2: PRESET_COMFORT, # Jour
    3: "Exterieur",
    4: "Aeration",
    5: "Fete",
    6: "Vacances",
    7: PRESET_AWAY,    # Hors-gel
}

HA_TO_EM_MODES = {
    "Calendrier": "00",
    PRESET_ECO: "02",
    PRESET_COMFORT: "01",
    "Exterieur": "03",
    "Aeration": "04",
    "Fete": "05",
    "Vacances": "06",
    PRESET_AWAY: "07",
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> bool:
    """Configurer la plateforme climate pour une entrée donnée."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    host = entry.options.get("host", entry.data.get("host"))
    port = int(entry.options.get("port", entry.data.get("port", 8899)))

    thermostat = EcomaxThermostat(coordinator, host, port)
    async_add_entities([thermostat], True)
    return True


class EcomaxThermostat(ClimateEntity):
    """Thermostat EcoMAX: lecture via coordinator + requêtes ciblées THERMOSTAT pour les actions."""

    _attr_name = "Thermostat personnalisé"
    _attr_unique_id = f"{DOMAIN}_thermostat"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.AUTO, HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE

    # Liste de presets exposée à l’UI
    @property
    def preset_modes(self) -> list[str]:
        return list(HA_TO_EM_MODES.keys())

    def __init__(self, coordinator, host: str, port: int) -> None:
        self._coordinator = coordinator
        self._host = host
        self._port = port

        # états internes
        self._preset_mode: str = "Calendrier"
        self._current_temperature: float | None = None
        self._target_temperature: float | None = None
        self.auto: int = 1
        self.heating: int = 0

    # ------------------------- propriétés UI -------------------------

    @property
    def available(self) -> bool:
        return self._coordinator.last_update_success

    @property
    def current_temperature(self) -> float | None:
        return self._current_temperature

    @property
    def target_temperature(self) -> float | None:
        return self._target_temperature

    @property
    def hvac_mode(self) -> HVACMode:
        # Basique : AUTO par défaut ; tu peux le mapper à partir de THERMOSTAT si dispo
        return HVACMode.AUTO

    @property
    def preset_mode(self) -> str | None:
        return self._preset_mode

    # ------------------------- actions -------------------------

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Envoie le preset (mode) à la chaudière."""
        if preset_mode not in self.preset_modes:
            _LOGGER.error("Preset %s non supporté", preset_mode)
            return

        # Code “fonction” du mode (confirmé dans ton code d’origine)
        mode_code = "011e01"
        # Conversion du libellé HA vers code EcoMAX (2 hexdigits)
        code = HA_TO_EM_MODES[preset_mode]

        trame = Trame("6400", "0100", "29", "a9", mode_code, code).build()

        comm = Communication(self._host, self._port)
        await comm.connect()
        try:
            # Envoi + attente ACK 'a9'
            await comm.send(trame, "a9")
        finally:
            await comm.close()

        self._preset_mode = preset_mode
        # Rafraîchir les infos thermostat après action
        await self.async_update()
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs) -> None:
        """Envoie la consigne de température."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        # Choix du code en fonction du preset/auto (reprend ta logique)
        code = "012001" if (self._preset_mode in ["Calendrier"] and self.auto == 1) or (self._preset_mode in [PRESET_COMFORT]) else "012101"
        value_hex = struct.pack("<f", float(temperature)).hex()
        trame = Trame("6400", "0100", "29", "a9", code, value_hex).build()

        comm = Communication(self._host, self._port)
        await comm.connect()
        try:
            await comm.send(trame, "a9")
        finally:
            await comm.close()

        self._target_temperature = float(temperature)
        await self.async_update()
        self.async_write_ha_state()

    # ------------------------- refresh ciblé thermostat -------------------------

    async def async_update(self) -> None:
        """Met à jour les informations du thermostat via la requête THERMOSTAT."""
        # Trame d’origine de ton code pour lecture THERMOSTAT
        trame = Trame("64 00", "20 00", "40", "c0", "647800", "").build()

        comm = Communication(self._host, self._port)
        await comm.connect()
        try:
            thermostat_data = await comm.request(
                trame,
                THERMOSTAT,
                "265535445525f78343",  # dataToSearch attendu
                "c0",                  # ack_flag
            )
        finally:
            await comm.close()

        if thermostat_data is None:
            _LOGGER.warning("Données thermostat indisponibles, conservation des valeurs précédentes")
            return

        _LOGGER.debug("Données du thermostat reçues: %s", thermostat_data)

        self._current_temperature = thermostat_data.get("TEMPERATURE", self._current_temperature)
        self._target_temperature = thermostat_data.get("ACTUELLE", self._target_temperature)

        mode = thermostat_data.get("MODE", 0)
        self._preset_mode = EM_TO_HA_MODES.get(mode, "Calendrier")

        self.auto = thermostat_data.get("AUTO", self.auto)
        self.heating = thermostat_data.get("HEATING", self.heating)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose les données brutes utiles pour debug."""
        return {
            "preset_map_mode_to_ha": EM_TO_HA_MODES.get(self._preset_mode, self._preset_mode),
            "auto": self.auto,
            "heating": self.heating,
        }
