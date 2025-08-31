
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

USER_SCHEMA = vol.Schema({
    vol.Required("host"): str,
    vol.Required("port", default=8899): int,
})

OPTIONS_SCHEMA = vol.Schema({
    vol.Required("host"): str,
    vol.Required("port", default=8899): int,
    vol.Required("scan_interval", default=60): int,  # seconds
})

class Ecomax360ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="EcoMax360", data=user_input)
        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA)

    @staticmethod
    def async_get_options_flow(config_entry):
        return Ecomax360OptionsFlow(config_entry)

class Ecomax360OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Pre-fill with current option or a sensible default
        current = {
            "host": self._entry.options.get("host", self._entry.data.get("host")),
            "port": self._entry.options.get("port", self._entry.data.get("port", 8899)),
            "scan_interval": self._entry.options.get("scan_interval", 60)
        }
        schema = vol.Schema({
            vol.Required("host", default=current["host"]): str,
            vol.Required("port", default=int(current["port"])): int,
            vol.Required("scan_interval", default=current["scan_interval"]): int,
        })
        return self.async_show_form(step_id="init", data_schema=schema)
